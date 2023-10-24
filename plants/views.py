import json
import base64
import os
from io import BytesIO

from django.core.handlers.wsgi import WSGIRequest
from django.http.response import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import *
from django.core.serializers import serialize
from django.db.models import F

from utils.file import base64_to_image_file
from .models import Plant, PlantDetection,Recomendation, Disease

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

model = YOLO('best.pt')

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

def detect_plant_disease(request):
    if request.method == 'POST':
        try:
            json_body = json.loads(request.body)
            image = np.asarray(Image.open(BytesIO(base64.b64decode(json_body['image']))))
            predict_result = model.predict(image)
            data_disease = []

            for r in predict_result:
                boxes = r.boxes
                for box in boxes:
                    b = box.xyxy[0]
                    c = box.cls
                    cropped_image = image[int(b[1]):int(b[3]), int(b[0]):int(b[2])]
                    string_cropped = cv2.imencode('.png', cropped_image)[1].tostring()

                    condition = model.names[int(c)]

                    try:
                        disease = Disease.objects.get(disease_type=condition)

                        try:
                            recomendation = Recomendation.objects.get(disease_id=disease)
                            data = {
                                'condition': condition,
                                'image_64': base64.b64encode(string_cropped).decode('utf-8'),
                                'recomendation': recomendation.recomendation,
                            }
                            data_disease.append(data)
                        except Recomendation.DoesNotExist:
                            pass

                    except Disease.DoesNotExist:
                        pass

            if len(data_disease) > 0:
                message = "Penyakit tanaman berhasil dideteksi"
            else:
                message = "Tidak ada penyakit yang terdeteksi"

            data_response = {
                'leafs': data_disease
            }

            return JsonResponse({'data': data_response, 'message': message}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

class DiseaseList(generics.ListCreateAPIView):
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer

class RecomendationList(generics.ListCreateAPIView):
    queryset = Recomendation.objects.all()
    serializer_class = RecomendationSerializer
    

