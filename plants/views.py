import json
import base64
import os
from io import BytesIO
import time
import threading
import os
import mimetypes
import hashlib
import pytz
from datetime import datetime, timedelta

from urllib.parse import urljoin
from django.core.handlers.wsgi import WSGIRequest
from django.http.response import JsonResponse, FileResponse, HttpResponseNotFound, HttpResponseNotAllowed, HttpResponseBadRequest
from django.conf import settings
from django.db.models import F
from django.urls import reverse as url_reverse
from django.utils import timezone
# from django.utils import timezone
from django.shortcuts import render, redirect
from django.forms.models import model_to_dict


from firebase.auth_firebase import send_topic_push
from .models import *
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


def convert_time_to_gmt7_indonesia(time):
    # Set the timezone to GMT+7 Indonesia
    timezone.activate(timezone('Asia/Jakarta'))

    # Convert the time to the local timezone
    local_time = timezone.now()

    # Calculate the offset between the local timezone and GMT+7 Indonesia
    offset = local_time.tzinfo.utcoffset(local_time)

    # Convert the time to GMT+7 Indonesia
    gmt7_indonesia_time = time - offset

    return gmt7_indonesia_time

def get_plant_image(request, plant_id):
    plant = get_object_or_404(Plant, id=plant_id)

    if request.user.is_authenticated:
        response = HttpResponse(plant.plant_img.read(), content_type='image/jpeg')
        return response
    else:
        return HttpResponse(status=403)


@api_view(['POST'])
def create_plant(request):
    serializer = PlantSerializer(data=request.data)
    if serializer.is_valid():
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

                    try:
                        disease = Disease.objects.get(disease_type=condition)
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

                        image_uri = urljoin(f'http://{request.get_host()}', 'media/') + file_name

                        data = {
                            'created_at': timezone.now(),
                            'condition': condition,
                            'image_uri': image_uri,
                            'recomendation': recomendation_dict
                        }



                        data_disease.append(data)

                        if not existing_history:
                            plant_history = DetectionHistory(
                                source='detection',
                                plant_img=file_name,
                                plant_name='strawberry',
                                condition=condition,
                                recommendation=recomendation
                            )
                            plant_history.save() 
                            
                            print("Image send :" + image_uri)
                            send_topic_push(
                                'Penyakit Terdeteksi',
                                f'Ada penyakit pada tanaman anda dengan jenis {condition}. Silahkan cek aplikasi untuk informasi lebih lanjut.',
                                image_uri
                            )
                            
                    except Recomendation.DoesNotExist:
                        pass

                    except Disease.DoesNotExist:
                        pass

            if len(data_disease) > 0:
                message = "Penyakit tanaman berhasil dideteksi"
            else:
                message = "Tidak ada penyakit yang terdeteksi"
                
            response = {
                'created_at': timezone.now(),
                'leafs_disease': data_disease,
                'message' : message
            }
            return make_response(data=response, status_code=200, message='ok')

        except KeyboardInterrupt as e:
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



                    try:
                        disease = Disease.objects.get(disease_type=condition)
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

                        image_uri = urljoin(f'http://{request.get_host()}', 'media/') + file_name

                        data = {
                            'created_at': timezone.now(),
                            'condition': condition,
                            'image_uri': image_uri,
                            'recomendation': recomendation_dict
                        }

                        data_disease.append(data)

                        if not existing_history:
                            plant_history = DetectionHistory(
                                source='segmentation',
                                plant_img=file_name,
                                plant_name='strawberry',
                                condition=condition,
                                recommendation=recomendation
                            )
                            plant_history.save() 
                            
                            print("Image send :" + image_uri)
                            send_topic_push(
                                'Penyakit Terdeteksi',
                                f'Ada penyakit pada tanaman anda dengan jenis {condition}. Silahkan cek aplikasi untuk informasi lebih lanjut.',
                                image_uri
                            )
                            
                    except Recomendation.DoesNotExist:
                        pass

                    except Disease.DoesNotExist:
                        pass

            if len(data_disease) > 0:
                message = "Penyakit tanaman berhasil dideteksi"
            else:
                message = "Tidak ada penyakit yang terdeteksi"

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
    json_body = json.loads(request.body)
    last_start = json_body['last_start']
    last_end = json_body['last_end']
    if last_end==-1:
        history_entries = DetectionHistory.objects.all().order_by('-created_at')[last_start:]
    else:
        history_entries = DetectionHistory.objects.all().order_by('-created_at')[last_start:last_end]
        
    serializer = DetectionHistorySerializer(history_entries, many=True)
    data = serializer.data
    for entry in data:
        entry['image_url'] = urljoin(f'http://{request.get_host()}', 'media/') + entry['plant_img']
        entry['recommendation'] = model_to_dict(Recomendation.objects.get(pk=entry['recommendation']))

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


def login_core(username, password):
    valid_login = False
    user = CustomUser.objects.filter(username=username)
    if len(user)>0:
        user = user[0]
        hash_obj = hashlib.sha256()
        hash_obj.update(password.encode('utf-8'))
        if user.password==hash_obj.hexdigest():
            web_session = CustomSession(user=user)
            web_session.save()
            return True, web_session
    return False, None

def web_login_wrap(view):
    def wrapper(*args, **kwargs):
        request = args[0]
        session_id = request.session['session_id']
        web_session = CustomSession.objects.filter(session_id=session_id)
        if len(web_session)>0:
            return view(*args, **kwargs)
        return redirect('login_web')
    return wrapper

def login(request: WSGIRequest):
    if request.method=='GET':
        return render(request, 'login.html')
    elif request.method=='POST':
        valid_login, web_session = login_core(request.POST['username'], request.POST['password'])
        if valid_login:
            request.session['session_id'] = web_session.session_id
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error_message': 'Login Salah'})

def register(request: WSGIRequest):
    if request.method == 'GET':
        return render(request, 'register.html')
    elif request.method == 'POST':
        if request.POST['password']!=request.POST['password-confirm']:
            return render(request, 'register.html', {'error_message': 'Password tidak sesuai dengan konfirmasi'})
        old_users = CustomUser.objects.filter(username=request.POST['username'])
        if len(old_users)>0:
            return render(request, 'register.html', {'error_message': 'Username sudah terdaftar!'})   
        hash_obj = hashlib.sha256()
        hash_obj.update(request.POST['password'].encode('utf-8'))         
        new_user = CustomUser(username=request.POST['username'], name=request.POST['name'], password=hash_obj.hexdigest())
        new_user.save()
        return login(request)
    else:
        return HttpResponseBadRequest('Method not allowed')

@web_login_wrap
def dashboard(request: WSGIRequest):
    month_count = {num: 0 for num in range(1, 13)}
    groupped_detections = [[]]

    for detection in DetectionHistory.objects.all().order_by('-created_at'):
        if len(groupped_detections[-1]) == 4:
            groupped_detections.append([])

        detected_time = timezone.localtime(detection.created_at, timezone.get_fixed_timezone(420))
        detected_time_utc7 = detected_time.astimezone(timezone.utc) + timedelta(minutes=420)

        groupped_detections[-1].append({
            'plant_img': urljoin(f'http://{request.get_host()}', 'media/') + detection.plant_img,
            'condition': detection.condition,
            'created_at_date': detected_time_utc7.date(),
            'created_at_clock': detected_time_utc7.time()
        })

        month_detected = detected_time_utc7.date().month
        if month_detected not in month_count:
            month_count[month_detected] = 1
        else:
            month_count[month_detected] += 1

    return render(request, 'dashboard.html', {'line_data': list(month_count.values()), 'penyakit_list': groupped_detections})

def splash(request: WSGIRequest):
    return render(request, 'splash.html')

def web_logout(request: WSGIRequest):
    session = CustomSession.objects.get(session_id=request.session['session_id'])
    session.delete()
    return redirect('splash')