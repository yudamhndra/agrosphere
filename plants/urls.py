from django.urls import path, include
from . import views
from .views import PlantDetectionList, PlantDetectionDetail, RecomendationList, DiseaseList, plant_detection_history, notification, plants_segmentation
from django.contrib.auth.decorators import login_required
from allauth.account.views import LoginView 


urlpatterns = [
    # api klasifikasi
    path('plants/<int:plant_id>/image/', (views.get_plant_image), name='get_plant_image'),
    path('plants/create/', (views.create_plant), name='create_plant'),
    path('plants/<int:plant_id>/update/', (views.update_plant), name='update_plant'),
    path('plants/<int:plant_id>/delete/', (views.delete_plant), name='delete_plant'),
    
    # api deteksi
    path('plants/detection', PlantDetectionList.as_view(), name='plant-list'),
    path('plants/<int:pk>/', PlantDetectionDetail.as_view(), name='plant-detail'),

    path('plants/detect', views.detect_plant_disease, name='plant-detect'),
    path('media/file', views.download_media_file, name='download-media-file'),
    path('plant-detection/history/', views.plant_detection_history, name='plant_detection_history'),
    
    #api recomendation
    path('diseases/', views.DiseaseList.as_view(), name='disease-list'),
    path('recomendations/', views.RecomendationList.as_view(), name='recomendation-list'),
    
    #apisegmentation
    path('plants/segmentation', views.plants_segmentation, name='plant-detect'),
    path('plant-segmentation/history/', views.plants_segmentation, name='plant_segmentation_history'),

    #notif
    path('notification/', notification, name='notification'),
    path('notification/history/', views.notificationHistory, name='notification-history'),
    
] 

