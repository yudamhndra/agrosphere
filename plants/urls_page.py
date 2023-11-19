from django.urls import path, include
from . import views
from .views import dashboard


urlpatterns = [
    path('dashboard/', (views.dashboard), name='dashboard'),
    path('splash/', (views.splash), name='splash'),
    path('login/', (views.login), name='login_web'),
    path('register/', (views.register), name='register_web'),
    path('logout/', (views.web_logout), name='logout_web'),
] 

