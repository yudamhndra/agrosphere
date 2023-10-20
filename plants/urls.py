from django.urls import path, include
from . import views

urlpatterns = [
    path('plants/<int:plant_id>/image/', views.get_plant_image, name='get_plant_image'),
    path('plants/create/', views.create_plant, name='create_plant'),
    path('plants/<int:plant_id>/update/', views.update_plant, name='update_plant'),
    path('plants/<int:plant_id>/delete/', views.delete_plant, name='delete_plant'),
]
