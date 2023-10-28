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

from firebase.auth_firebase import send_topic_push
from .models import Plant, PlantDetection, Recomendation, Disease, Recomendation, Notification, Plant, DetectionHistory
from django.core import serializers

from rest_framework import viewsets
from .serializers import PlantSerializer, PlantDetectionSerializer, RecomendationSerializer, DiseaseSerializer, \
    NotificationSerializer
from rest_framework import status, generics
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from PIL import Image
import numpy as np
import cv2

from .utils import make_response

print('Loading model...')
model = YOLO('best.pt')
segmentation_model = YOLO('segmentation_best.pt')
print('Model Loaded!')


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
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
def update_plant(request, plant_id):
    plant = get_object_or_404(Plant, id=plant_id)
    serializer = PlantSerializer(plant, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_plant(request, plant_id):
    plant = get_object_or_404(Plant, id=plant_id)
    plant.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


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
        return HttpResponseNotFound(f'No file named {file_path}')
    return HttpResponseNotAllowed('Invalid method')


def draw_bounding_boxes(image, boxes, labels):
    for box in boxes:
        if len(box) >= 4:
            x1, y1, x2, y2 = box[:4]  # Ambil koordinat kotak pembatas
            label = labels[int(box[4]) if len(box) > 4 else 0]  # Ambil label objek jika tersedia

            color = (0, 255, 0)  # Warna hijau
            thickness = 2

            # Gambar kotak pembatas pada gambar
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
                        return JsonResponse({'data': {}, 'status': False, 'message': 'No image data provided in request', 'error_data': 'No image data provided in request.'}, status=400)
                except json.JSONDecodeError:
                    return JsonResponse({'data': {}, 'status': False, 'message': 'Invalid JSON data in request body', 'error_data': 'Invalid JSON data in request body.'}, status=400)

            print("predict")

            # Now you can proceed with your detection logic using the 'image' variable
            predict_result = model.predict(image)
            data_disease = []
            file_name = ""
            condition = ""

            for r in predict_result:
                boxes = r.boxes

                # Menggambar bounding box pada gambar asli
                image_with_boxes = draw_bounding_boxes(image.copy(), boxes, model.names)

                # Simpan gambar yang telah dimodifikasi ke dalam media dan ambil path file
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
                        plant_name="strawberry",  # Ganti dengan nama tanaman yang sesuai
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

                    # Mencocokkan nama penyakit dengan tabel Disease
                    try:
                        disease = Disease.objects.get(disease_type=condition)

                        # Mengambil data dari tabel Recomendation berdasarkan ID yang sesuai
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

            # Mengambil semua data dari tabel Recomendation
            # all_recomendations = Recomendation.objects.all().values()

            # Response yang menggabungkan hasil detection dan hasil dari fungsi detect_plant_disease1
            response = {
                'created_at': timezone.now(),
                'leafs_disease': data_disease,
                'message' : message
                # 'all_recomendations': list(all_recomendations),
            }

            return JsonResponse(response, status=200)

        except Exception as e:
            print(e.__class__)
            return JsonResponse({'data': {}, 'status': False, 'message': 'Error Exception', 'error_data': str(e)}, status=500)

    else:
        return JsonResponse({'data': {}, 'status': False, 'message': 'Method not allowed', 'error_data': 'Method not allowed'}, status=405)
    
def apply_segmentation_mask(original_image, mask):
    # Ambil array mask dari objek Masks dalam format normalized segments
    mask_array = mask.xyn

    # Buat salinan gambar asli untuk menggambarkan mask segmentasi
    masked_image = original_image.copy()

    # Gambar mask segmentasi ke gambar asli
    for segment in mask_array:
        segment = np.array(segment)
        if len(segment) >= 3:  # Pastikan setiap segment memiliki setidaknya tiga titik
            points = segment.reshape((-1, 2)).astype(np.int32)
            cv2.fillPoly(masked_image, [points], (0, 255, 0))  # Warna hijau untuk mask

    return masked_image




    
def plants_segmentation(request):
    if request.method == 'POST':
        try:
            data_disease_detection = []  # Inisialisasi data_disease_detection untuk deteksi penyakit
            data_disease_segmentation = []  # Inisialisasi data_disease_segmentation untuk segmentasi
            file_name_detection = ""
            file_name_segmentation = ""

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
                        return JsonResponse({'data': {}, 'status': False, 'message': 'No image data provided in request', 'error_data': 'No image data provided in request.'}, status=400)
                except json.JSONDecodeError:
                    return JsonResponse({'data': {}, 'status': False, 'message': 'Invalid JSON data in request body', 'error_data': 'Invalid JSON data in request body.'}, status=400)

            print("predict_detection")
            # Melakukan deteksi penyakit
            predict_result_detection = model.predict(image)

            for r in predict_result_detection:
                boxes = r.boxes
                image_with_boxes = draw_bounding_boxes(image.copy(), boxes, model.names)
                file_name_detection = f'{time.time()}_{threading.get_native_id()}_detection.png'
                file_path_detection = os.path.join(settings.MEDIA_ROOT, file_name_detection)
                cv2.imwrite(file_path_detection, image_with_boxes)
                for box in boxes:
                    c = box.cls
                    condition = model.names[int(c)]
                    print("Condition (Detection): " + condition)

                    # Mencocokkan nama penyakit dengan tabel Disease
                    try:
                        disease = Disease.objects.get(disease_type=condition)
                        
                        # Mengambil data dari tabel Recomendation berdasarkan ID yang sesuai
                        try:
                            recomendation = Recomendation.objects.get(disease_id=disease)
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

                            image_uri = urljoin(f'http://{request.get_host()}', 'media/') + file_name_detection
                            data_detection = {
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

                            data_disease_detection.append(data_detection)
                        except Recomendation.DoesNotExist:
                            pass

                    except Disease.DoesNotExist:
                        pass

            print("predict_segmentation")
            # Melakukan segmentasi
            predict_result_segmentation = segmentation_model.predict(image)

            for r in predict_result_segmentation:
                masks = r.masks

                for mask in masks:
                    # Apply the masks to the original image to obtain segmented regions
                    segmented_image = apply_segmentation_mask(image, mask)
                    file_name_segmentation = f'{time.time()}_{threading.get_native_id()}_segmentation.png'
                    file_path_segmentation = os.path.join(settings.MEDIA_ROOT, file_name_segmentation)
                    cv2.imwrite(file_path_segmentation, segmented_image)
                    condition_segmentation = "segmented_region"

                    # Simpan data ke dalam model Plant (gantilah nama dan nilai sesuai dengan kebutuhan)
                    plant_segmentation = Plant(
                        user_id=1, 
                        plant_img=file_name_segmentation,
                        plant_name="strawberry",  # Ganti dengan nama tanaman yang sesuai
                        condition=condition_segmentation,
                    )
                    plant_segmentation.save()
                    
                    try:
                        disease_segmentation = Disease.objects.get(disease_type=condition_segmentation)
                
                        try:
                            recomendation_segmentation = Recomendation.objects.get(disease_id=disease_segmentation)
                            recomendation_dict_segmentation = {
                                'disease_type': disease_segmentation.disease_type,
                                'symptoms': recomendation_segmentation.symptoms,
                                'recomendation': recomendation_segmentation.recomendation,
                                'organic_control': recomendation_segmentation.organic_control,
                                'chemical_control_1': recomendation_segmentation.chemical_control_1,
                                'chemical_control_2': recomendation_segmentation.chemical_control_2,
                                'chemical_control_3': recomendation_segmentation.chemical_control_3,
                                'chemical_control_4': recomendation_segmentation.chemical_control_4,
                                'chemical_control_5': recomendation_segmentation.chemical_control_5,
                                'chemical_control_1_dosage': recomendation_segmentation.chemical_control_1_dosage,
                                'chemical_control_2_dosage': recomendation_segmentation.chemical_control_2_dosage,
                                'chemical_control_3_dosage': recomendation_segmentation.chemical_control_3_dosage,
                                'chemical_control_4_dosage': recomendation_segmentation.chemical_control_4_dosage,
                                'chemical_control_5_dosage': recomendation_segmentation.chemical_control_5_dosage,
                                'additional_info': recomendation_segmentation.additional_info,
                            }
                            print(recomendation_dict_segmentation)

                            image_uri_segmentation = urljoin(f'http://{request.get_host()}', 'media/') + file_name_segmentation
                            data_segmentation = {
                                'created_at': timezone.now(),
                                'condition': condition_segmentation,
                                'image_uri': image_uri_segmentation,
                                'recomendation': recomendation_dict_segmentation
                            }

                            send_topic_push(
                                'Region Terdeteksi',
                                f'Region tanaman anda dengan jenis {condition_segmentation}. Silahkan cek aplikasi untuk informasi lebih lanjut.',
                                image_uri_segmentation
                            )

                            data_disease_segmentation.append(data_segmentation)
                        except Recomendation.DoesNotExist:
                            pass

                    except Disease.DoesNotExist:
                        pass

            if len(data_disease_detection) > 0 or len(data_disease_segmentation) > 0:
                message = "Proses deteksi penyakit dan segmentasi berhasil dilakukan"
            else:
                message = "Tidak ada penyakit atau region yang terdeteksi"

            response = {
                'created_at': timezone.now(),
                'detection_results': data_disease_detection,
                'segmentation_results': data_disease_segmentation,
                'message': message,
            }

            return JsonResponse(response, status=200)

        except Exception as e:
            print(e.__class__)
            return JsonResponse({'data': {}, 'status': False, 'message': 'Error Exception', 'error_data': str(e)}, status=500)

    else:
        return JsonResponse({'data': {}, 'status': False, 'message': 'Method not allowed', 'error_data': 'Method not allowed'}, status=405)

def plant_detection_history(request):
    history = PlantDetection.objects.order_by('-created_at')
    serialized_history = []

    for entry in history:
        serialized_history.append({
            'created_at': entry.created_at,
            'plant_name': entry.plant_name,
            'plant_image': entry.plant_img,
            'condition': entry.condition,
        })

    return JsonResponse({'history': serialized_history})


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
