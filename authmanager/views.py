from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from .serializers import UserSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .utils import make_response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            if User.objects.filter(email=email).exists():
                return make_response({}, 'Email address already registered.', status_code=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create_user(**serializer.validated_data)
            # Generate a JWT token for the user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response({'message': 'User registered successfully', 'access_token': access_token},
                            status=status.HTTP_201_CREATED)

        return make_response(None, 'Register gagal', status_code=status.HTTP_400_BAD_REQUEST,
                             error_data=serializer.errors)


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

                data_user = UserSerializer(user).data

                # Generate a JWT token for the user
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                data_user['access_token'] = access_token

                return make_response(data_user, 'Login berhasil', status_code=status.HTTP_200_OK)
            else:
                return make_response(None, 'Invalid login credentials', status_code=status.HTTP_401_UNAUTHORIZED)
        return make_response(None, 'Login gagal', status_code=status.HTTP_400_BAD_REQUEST,
                             error_data=serializer.errors)
