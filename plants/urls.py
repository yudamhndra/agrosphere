from django.urls import path, include
from . import views
from django.contrib.auth.decorators import login_required


urlpatterns = [
    path('plants/<int:plant_id>/image/', login_required(views.get_plant_image), name='get_plant_image'),
    path('plants/create/', login_required(views.create_plant), name='create_plant'),
    path('plants/<int:plant_id>/update/', login_required(views.update_plant), name='update_plant'),
    path('plants/<int:plant_id>/delete/', login_required(views.delete_plant), name='delete_plant'),
]
