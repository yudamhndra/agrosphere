from django.db import models
from django.contrib.auth.models import User

# classification
class Plant(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plant_img = models.ImageField(upload_to='plants/images')  # Gunakan ImageField untuk menyimpan gambar
    plant_name = models.CharField(max_length=255)
    condition = models.CharField(max_length=255)
    disease = models.CharField(max_length=255, blank=True, null=True)  # Memungkinkan nilai NULL
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plant_name}/{self.condition}/{self.disease}"

