from django.db import models
from django.contrib.auth.models import User
import base64


# segmentation
class Plant(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plant_img = models.CharField(max_length=255)
    plant_name = models.CharField(max_length=255)
    condition = models.CharField(max_length=255)
    disease = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plant_name}/{self.condition}/{self.disease}"

# detection
class PlantDetection(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plant_img = models.CharField(max_length=255)
    plant_name = models.CharField(max_length=255)
    condition = models.CharField(max_length=255)
    disease = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.plant_name}/{self.condition}/{self.disease}"
    
class Disease(models.Model):
    id = models.AutoField(primary_key=True)
    disease_type = models.CharField(max_length=255)
    
    def __str__(self):
        return self.disease_type

class Recomendation(models.Model):
    id = models.AutoField(primary_key=True)
    disease_id = models.ForeignKey(Disease, on_delete=models.CASCADE)
    symptoms = models.CharField(max_length=255)
    recomendation = models.CharField(max_length=255, null=True)
    organic_control = models.CharField(max_length=255, null=True)
    chemical_control_1 = models.TextField(null=True)
    chemical_control_2 = models.TextField(null=True)
    chemical_control_3 = models.TextField(null=True)
    chemical_control_4 = models.TextField(null=True)
    chemical_control_5 = models.TextField(null=True)
    chemical_control_1_dosage = models.TextField(null=True)
    chemical_control_2_dosage = models.TextField(null=True)
    chemical_control_3_dosage = models.TextField(null=True)
    chemical_control_4_dosage = models.TextField(null=True)
    chemical_control_5_dosage = models.TextField(null=True)
    additional_info = models.TextField(null=True)
    
    def __str__(self):
        return f"Recomendation for {self.disease_id.disease_type} - Symptoms: {self.symptoms}"
    
class DetectionHistory(models.Model):
    id = models.AutoField(primary_key=True)
    recommendation = models.ForeignKey(Recomendation, on_delete= models.CASCADE)
    source = models.CharField(max_length=255)
    plant_img = models.CharField(max_length=255)
    plant_name = models.CharField(max_length=255)
    condition = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.source} - {self.plant_name} ({self.condition})"
    
class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class CustomUser(models.Model):
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True)
    password = models.CharField(max_length=510)
    
class CustomSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField(blank=True, null=True)
    infinite_session = models.BooleanField(default=True)
    session_id = models.CharField(max_length=1000, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.session_id = base64.b64encode(self.user.username.encode('utf-8')+self.user.password.encode('utf-8')).decode('utf-8')
        super().save(*args, **kwargs)
