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
from .models import Plant, PlantDetection, Recomendation, Disease, Recomendation, Notification, Plant
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


def detect_plant_disease(request):
    if request.method == 'POST':
        try:
            if 'image' in request.FILES:
                # If an image is provided as a file attachment in form-data
                uploaded_image = request.FILES['image'].read()
                image = np.asarray(Image.open(BytesIO(uploaded_image)))
            else:
                try:
                    json_body = json.loads(request.body)
                    image_data = json_body.get('image')
                    if image_data:
                        image = np.asarray(Image.open(BytesIO(base64.b64decode(image_data))))
                    else:
                        return make_response({}, "No image data provided in request", 400,
                                             {'error': 'No image data provided in request.'})
                except json.JSONDecodeError:
                    return make_response({}, "Invalid JSON data in request body", 400,
                                         {'error': 'Invalid JSON data in request body.'})

            print("predict")

            # Now you can proceed with your detection logic using the 'image' variable
            predict_result = model.predict(image)
            data_disease = []
            file_name = ""
            condition = ""

            for r in predict_result:
                boxes = r.boxes
                for box in boxes:
                    b = box.xyxy[0]
                    c = box.cls
                    cropped_image = image[int(b[1]):int(b[3]), int(b[0]):int(b[2])]

                    # Simpan gambar ke dalam media dan ambil path file
                    file_name = f'{time.time()}_{threading.get_native_id()}.png'
                    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
                    cv2.imwrite(file_path, cropped_image)

                    condition = model.names[int(c)]
                    print("Condition " + condition)
                    
                    plant_detection = PlantDetection(
                        user_id=1, 
                        plant_img=file_name,
                        plant_name="strawberry",  # Ganti dengan nama tanaman yang sesuai
                        condition=condition,
                    )
                    plant_detection.save()
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
                # 'all_recomendations': list(all_recomendations),
            }

            return make_response(response, message, 200)
        except Exception as e:
            print(e.__class__)
            return make_response({}, "Error Exception", 500, str(e))
    else:
        return make_response({}, "Method not allowed", 405, {'error': 'Method not allowed'})

def plants_segmentation(request):
    if request.method == 'POST':
        try:
            if 'image' in request.FILES:
                # If an image is provided as a file attachment in form-data
                uploaded_image = request.FILES['image'].read()
                image = np.asarray(Image.open(BytesIO(uploaded_image)))
            else:
                try:
                    json_body = json.loads(request.body)
                    image_data = json_body.get('image')
                    if image_data:
                        image = np.asarray(Image.open(BytesIO(base64.b64decode(image_data))))
                    else:
                        return make_response({}, "No image data provided in request", 400,
                                             {'error': 'No image data provided in request.'})
                except json.JSONDecodeError:
                    return make_response({}, "Invalid JSON data in request body", 400,
                                         {'error': 'Invalid JSON data in request body.'})

            print("predict")

            # Now you can proceed with your detection logic using the 'image' variable
            predict_result = segmentation_model.predict(image)
            data_disease = []
            file_name = ""
            condition = ""

            for r in predict_result:
                boxes = r.boxes
                for box in boxes:
                    b = box.xyxy[0]
                    c = box.cls
                    cropped_image = image[int(b[1]):int(b[3]), int(b[0]):int(b[2])]

                    # Simpan gambar ke dalam media dan ambil path file
                    file_name = f'{time.time()}_{threading.get_native_id()}.png'
                    file_path = os.path.join(settings.MEDIA_ROOT, file_name)
                    cv2.imwrite(file_path, cropped_image)

                    condition = segmentation_model.names[int(c)]
                    print("Condition " + condition)
                    
                    plant_clasification = Plant(
                        user_id=1, 
                        plant_img=file_name,
                        plant_name="strawberry",  # Ganti dengan nama tanaman yang sesuai
                        condition=condition,
                    )
                    plant_clasification.save()
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
                # 'all_recomendations': list(all_recomendations),
            }

            return make_response(response, message, 200)
        except Exception as e:
            print(e.__class__)
            return make_response({}, "Error Exception", 500, str(e))
    else:
        return make_response({}, "Method not allowed", 405, {'error': 'Method not allowed'})


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
