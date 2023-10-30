import json
import base64
import os
from io import BytesIO
import time
import threading
import os
import mimetypes
from urllib.parse import urljoin

from django.core.handlers.wsgi import WSGIRequest
from django.http.response import JsonResponse, FileResponse, HttpResponseNotFound, HttpResponseNotAllowed
from django.conf import settings
from django.db.models import F
from django.urls import reverse as url_reverse
from django.utils import timezone
from django.shortcuts import render

from firebase.auth_firebase import send_topic_push
from .models import Plant, PlantDetection, Recomendation, Disease, Recomendation, Notification, Plant, DetectionHistory
from django.core import serializers

from rest_framework import viewsets
from .serializers import PlantSerializer, PlantDetectionSerializer, RecomendationSerializer, DiseaseSerializer, \
    NotificationSerializer, DetectionHistorySerializer
from rest_framework import status, generics
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from PIL import Image
import numpy as np
import cv2

from .utils import make_response

print('Loading object detection model...')
model = YOLO('best.pt')
print('Object Detection Model Loaded!')


print('Loading semantic segmentation model...')
segmentation_model = YOLO('segmentation_best.pt')
print('Semantic Segmentation Model Loaded!')


'''Klasifikasi'''


def get_plant_image(request, plant_id):
    # Ambil objek tanaman berdasarkan ID
    plant = get_object_or_404(Plant, id=plant_id)

    # Pastikan hanya pengguna yang sudah login yang dapat mengakses gambar
    if request.user.is_authenticated:
        # Mengatur header respons untuk memastikan gambar dapat diakses
        response = HttpResponse(plant.plant_img.read(), content_type='image/jpeg')
        return response
    else:
        # Pengguna yang tidak login tidak diijinkan mengakses gambar
        return HttpResponse(status=403)


@api_view(['POST'])
def create_plant(request):
    serializer = PlantSerializer(data=request.data)
    if serializer.is_valid():
        # Create a new name based on database values
        plant_name = serializer.validated_data.get('plant_name')
        condition = serializer.validated_data.get('condition')
        disease = serializer.validated_data.get('disease')

        new_name = f"{plant_name}/{condition}/{disease}"

        response_data = {
            'plant_name': new_name,
            'condition': condition,
            'disease': disease,
        }

        serializer.save()
        return make_response(data=serializer.data, status_code=200)
    return make_response(data=serializer.errors, status_code=400, message="error")


@api_view(['PUT'])
def update_plant(request, plant_id):
    plant = get_object_or_404(Plant, id=plant_id)
    serializer = PlantSerializer(plant, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return make_response(data=serializer.data, status_code=200)
    return make_response(data=serializer.errors, status_code=400)


@api_view(['DELETE'])
def delete_plant(request, plant_id):
    plant = get_object_or_404(Plant, id=plant_id)
    plant.delete()
    return make_response(message="Deleted", status_code=200)


'''deteksi'''
class PlantDetectionList(generics.ListCreateAPIView):
    queryset = PlantDetection.objects.all()
    serializer_class = PlantDetectionSerializer


class PlantDetectionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PlantDetection.objects.all()
    serializer_class = PlantDetectionSerializer


def download_media_file(request: WSGIRequest):
    if request.method == 'GET':
        file_path = os.path.join(settings.MEDIA_ROOT, request.GET['filepath'])
        if os.path.exists(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            response = FileResponse(open(file_path, 'rb'), content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}'
            return response
        return make_response(message=f'No file named {file_path}', status_code=400)
    return make_response(message='Invalid method', status_code=400)


def draw_bounding_boxes(image, boxes, labels):
    for box in boxes:
        if len(box) >= 4:
            x1, y1, x2, y2 = box[:4]
            label = labels[int(box[4]) if len(box) > 4 else 0] 

            color = (0, 255, 0)
            thickness = 2

            cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
            cv2.putText(image, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)

    return image

def detect_plant_disease(request):
    if request.method == 'POST':
        try:
            if 'image' in request.FILES:
                uploaded_image = request.FILES['image'].read()
                image = np.asarray(cv2.imdecode(np.frombuffer(uploaded_image, np.uint8), -1))
            else:
                try:
                    json_body = json.loads(request.body)
                    image_data = json_body.get('image')
                    if image_data:
                        image = np.asarray(cv2.imdecode(np.frombuffer(base64.b64decode(image_data), np.uint8), -1))
                    else:
                        return make_response(status_code=400, message='No image data provided in request')
                except json.JSONDecodeError:
                    return make_response(status_code=400, message='Invalid JSON data in request body')

            print("predict")

            # Now you can proceed with your detection logic using the 'image' variable
            predict_result = model.predict(image)
            data_disease = []
            file_name = ""
            condition = ""

            for r in predict_result:
                boxes = r.boxes

                image_with_boxes = draw_bounding_boxes(image.copy(), boxes, model.names)

                file_name = f'{time.time()}_{threading.get_native_id()}.png'
                file_path = os.path.join(settings.MEDIA_ROOT, file_name)
                cv2.imwrite(file_path, image_with_boxes)

                for box in boxes:
                    c = box.cls
                    condition = model.names[int(c)]
                    print("Condition " + condition)
                    
                    plant_detection = PlantDetection(
                        user_id=1, 
                        plant_img=file_name,
                        plant_name="strawberry",  
                        condition=condition,
                    )
                    plant_detection.save()
                    
                    existing_history = DetectionHistory.objects.filter(plant_img=file_name).first()

                    if not existing_history:
                        plant_history = DetectionHistory(
                            source='detection',
                            plant_img=file_name,
                            plant_name='strawberry',
                            condition=condition
                        )
                        plant_history.save() 

                    try:
                        disease = Disease.objects.get(disease_type=condition)

                        try:
                            recomendation = Recomendation.objects.get(disease_id=disease)

                            # Create a dictionary representing the Recomendation object
                            recomendation_dict = {
                                'disease_type': disease.disease_type,
                                'symptoms': recomendation.symptoms,
                                'recomendation': recomendation.recomendation,
                                'organic_control': recomendation.organic_control,
                                'chemical_control_1': recomendation.chemical_control_1,
                                'chemical_control_2': recomendation.chemical_control_2,
                                'chemical_control_3': recomendation.chemical_control_3,
                                'chemical_control_4': recomendation.chemical_control_4,
                                'chemical_control_5': recomendation.chemical_control_5,
                                'chemical_control_1_dosage': recomendation.chemical_control_1_dosage,
                                'chemical_control_2_dosage': recomendation.chemical_control_2_dosage,
                                'chemical_control_3_dosage': recomendation.chemical_control_3_dosage,
                                'chemical_control_4_dosage': recomendation.chemical_control_4_dosage,
                                'chemical_control_5_dosage': recomendation.chemical_control_5_dosage,
                                'additional_info': recomendation.additional_info,
                            }

                            print(recomendation_dict)

                            image_uri = urljoin(f'http://{request.get_host()}', 'media/') + file_name

                            data = {
                                'created_at': timezone.now(),
                                'condition': condition,
                                'image_uri': image_uri,
                                'recomendation': recomendation_dict
                            }

                            send_topic_push(
                                'Penyakit Terdeteksi',
                                f'Ada penyakit pada tanaman anda dengan jenis {condition}. Silahkan cek aplikasi untuk informasi lebih lanjut.',
                                image_uri
                            )

                            data_disease.append(data)
                        except Recomendation.DoesNotExist:
                            pass

                    except Disease.DoesNotExist:
                        pass

            if len(data_disease) > 0:
                message = "Penyakit tanaman berhasil dideteksi"
            else:
                message = "Tidak ada penyakit yang terdeteksi"
                
            # Response yang menggabungkan hasil detection dan hasil dari fungsi detect_plant_disease1
            response = {
                'created_at': timezone.now(),
                'leafs_disease': data_disease,
                'message' : message
            }
            return make_response(data=response, status_code=200, message='ok')

        except Exception as e:
            print(e.__class__)
            return make_response(status_code=400, message=str(e))
    else:
        return make_response(status_code=405, message='Method not allowed')

def plants_segmentation(request):
    if request.method == 'POST':
        try:
            if 'image' in request.FILES:
                uploaded_image = request.FILES['image'].read()
                image = np.asarray(cv2.imdecode(np.frombuffer(uploaded_image, np.uint8), -1))
            else:
                try:
                    json_body = json.loads(request.body)
                    image_data = json_body.get('image')
                    if image_data:
                        image = np.asarray(cv2.imdecode(np.frombuffer(base64.b64decode(image_data), np.uint8), -1))
                    else:
                        return make_response(status_code=400, message='No image data provided in request')
                except json.JSONDecodeError:
                    return make_response(status_code=400, message='Invalid JSON data in request body')

            print("predict")

            predict_result = segmentation_model.predict(image)
            data_disease = []
            file_name = ""
            condition = ""

            for r in predict_result:
                boxes = r.boxes

                image_with_boxes = draw_bounding_boxes(image.copy(), boxes, segmentation_model.names)

                file_name = f'{time.time()}_{threading.get_native_id()}.png'
                file_path = os.path.join(settings.MEDIA_ROOT, file_name)
                cv2.imwrite(file_path, image_with_boxes)

                for box in boxes:
                    c = box.cls
                    condition = segmentation_model.names[int(c)]
                    print("Condition " + condition)
                    
                    plant_detection = Plant(
                        user_id=1, 
                        plant_img=file_name,
                        plant_name="strawberry",  
                        condition=condition,
                    )
                    plant_detection.save()
                    
                    existing_history = DetectionHistory.objects.filter(plant_img=file_name).first()

                    if not existing_history:
                        plant_history = DetectionHistory(
                            source='segmentation',
                            plant_img=file_name,
                            plant_name='strawberry',
                            condition=condition
                        )
                        plant_history.save() 

                    try:
                        disease = Disease.objects.get(disease_type=condition)

                        try:
                            recomendation = Recomendation.objects.get(disease_id=disease)

                            # Create a dictionary representing the Recomendation object
                            recomendation_dict = {
                                'disease_type': disease.disease_type,
                                'symptoms': recomendation.symptoms,
                                'recomendation': recomendation.recomendation,
                                'organic_control': recomendation.organic_control,
                                'chemical_control_1': recomendation.chemical_control_1,
                                'chemical_control_2': recomendation.chemical_control_2,
                                'chemical_control_3': recomendation.chemical_control_3,
                                'chemical_control_4': recomendation.chemical_control_4,
                                'chemical_control_5': recomendation.chemical_control_5,
                                'chemical_control_1_dosage': recomendation.chemical_control_1_dosage,
                                'chemical_control_2_dosage': recomendation.chemical_control_2_dosage,
                                'chemical_control_3_dosage': recomendation.chemical_control_3_dosage,
                                'chemical_control_4_dosage': recomendation.chemical_control_4_dosage,
                                'chemical_control_5_dosage': recomendation.chemical_control_5_dosage,
                                'additional_info': recomendation.additional_info,
                            }

                            print(recomendation_dict)

                            image_uri = urljoin(f'http://{request.get_host()}', 'media/') + file_name

                            data = {
                                'created_at': timezone.now(),
                                'condition': condition,
                                'image_uri': image_uri,
                                'recomendation': recomendation_dict
                            }

                            send_topic_push(
                                'Penyakit Terdeteksi',
                                f'Ada penyakit pada tanaman anda dengan jenis {condition}. Silahkan cek aplikasi untuk informasi lebih lanjut.',
                                image_uri
                            )

                            data_disease.append(data)
                        except Recomendation.DoesNotExist:
                            pass

                    except Disease.DoesNotExist:
                        pass

            if len(data_disease) > 0:
                message = "Penyakit tanaman berhasil dideteksi"
            else:
                message = "Tidak ada penyakit yang terdeteksi"
                
            # Response yang menggabungkan hasil detection dan hasil dari fungsi detect_plant_disease1
            response = {
                'created_at': timezone.now(),
                'leafs_disease': data_disease,
                'message' : message
            }
            return make_response(data=response, status_code=200, message='ok')

        except Exception as e:
            print(e.__class__)
            return make_response(status_code=400, message=str(e))
    else:
        return make_response(status_code=405, message='Method not allowed')

  
def detection_history(request):
    # Mengambil semua data DetectionHistory dari database
    history_entries = DetectionHistory.objects.all()

    # Meng-serialize data menggunakan serializer
    serializer = DetectionHistorySerializer(history_entries, many=True)

    # Menambahkan URL gambar media ke setiap entri
    data = serializer.data
    for entry in data:
        entry['image_url'] = settings.MEDIA_URL + entry['plant_img']

    return make_response(data=data, status_code=200)




class DiseaseList(generics.ListCreateAPIView):
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer


class RecomendationList(generics.ListCreateAPIView):
    queryset = Recomendation.objects.all()
    serializer_class = RecomendationSerializer


@api_view(['POST'])
def notification(request):
    serializer = NotificationSerializer(data=request.data)
    if serializer.is_valid():
        title = serializer.validated_data.get('title')
        description = serializer.validated_data.get('description')

        response_data = {
            'title': title,
            'description': description,
        }

        serializer.save()
        return make_response(response_data, "Notifikasi berhasil dikirim", 201)
    return make_response(serializer.errors, "Notifikasi gagal dikirim", 400)


@api_view(['GET', 'POST'])
def notificationHistory(request):
    if request.method == 'GET':
        # Mendapatkan semua notifikasi dari database
        notifications = Notification.objects.all()
        serializer = NotificationSerializer(notifications, many=True)
        return make_response(serializer.data, "Notification History", 200)

    elif request.method == 'POST':
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data.get('title')
            description = serializer.validated_data.get('description')

            response_data = {
                'title': title,
                'description': description,
            }

            serializer.save()
            return make_response(response_data, "Notification History", 200)
        return make_response(None, "Notification History", 400, serializer.errors)

def dashboard(request: WSGIRequest):
    month_count = {num:0 for num in range(1, 13)}
    groupped_detections = [[]]
    for detection in DetectionHistory.objects.all():
        if len(groupped_detections[-1])==4:
            groupped_detections.append([])
        groupped_detections[-1].append({'plant_img': urljoin(f'http://{request.get_host()}', 'media/') + detection.plant_img, 'condition': detection.condition})
        month_detected = detection.updated_at.date().month
        if not (month_detected in month_count):
            month_count[month_detected] = 1
        else:
            month_count[month_detected] += 1

    return render(request, 'dashboard.html', {'line_data': list(month_count.values()), 'penyakit_list': groupped_detections})