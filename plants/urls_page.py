from django.urls import path, include
from . import views
from .views import dashboard


urlpatterns = [
    # api klasifikasi
    path('dashboard/', (views.dashboard), name='dashboard'),
    
] 

