from django.http.response import FileResponse
from django.shortcuts import *
from PIL import Image


def serve_image(request, file_path):
    print("file_path", file_path)

    image = get_object_or_404(Image, image=file_path)
    return FileResponse(image.image)
