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
from django.http.response import JsonResponse
from .models import Plant,PlantDetection

from rest_framework import viewsets
from .serializers import PlantSerializer, PlantDetectionSerializer, RecomendationSerializer, DiseaseSerializer
from rest_framework import status, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from PIL import Image
import numpy as np
import cv2

from .utils import make_response

print('Loading model...')
model = YOLO('best.pt')
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

def detect_plant_disease(request: WSGIRequest):
    json_body = json.loads(request.body)
    image = np.asarray(Image.open(BytesIO(base64.b64decode(json_body['image']))))
    predict_result = model.predict(image)
    cropped_images_base64 = []
    for r in predict_result:
        boxes = r.boxes
        for box in boxes:
            b = box.xyxy[0]  
            c = box.cls        
            cropped_image = image[int(b[1]):int(b[3]), int(b[0]):int(b[2])]
            string_cropped = cv2.imencode('.png', cropped_image)[1].tostring()
            cropped_images_base64.append((model.names[int(c)], base64.b64encode(string_cropped).decode('utf-8')))
    response = {
        'leafs': cropped_images_base64
    }
    return JsonResponse(response)