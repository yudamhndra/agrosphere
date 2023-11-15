from django.urls import path, include
from . import views
from .views import dashboard


urlpatterns = [
    path('dashboard/', (views.dashboard), name='dashboard'),
    
] 

