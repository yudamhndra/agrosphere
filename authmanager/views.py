from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from .serializers import UserSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            if User.objects.filter(email=email).exists():
                return Response({'message': 'Email address already registered.'}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.create_user(**serializer.validated_data)

            # Generate a JWT token for the user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response({'message': 'User registered successfully', 'access_token': access_token}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(generics.CreateAPIView):
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username_or_email = serializer.validated_data['username_or_email']
            password = serializer.validated_data['password']

            if '@' in username_or_email:
                kwargs = {'email': username_or_email}
            else:
                kwargs = {'username': username_or_email}

            user = authenticate(request, **kwargs, password=password)
            if user is not None:
                login(request, user)
                
                # Generate a JWT token for the user
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)

                return Response({'message': 'Login successful', 'access_token': access_token}, status=status.HTTP_200_OK)
            else:
                return Response({'message': 'Invalid login credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
