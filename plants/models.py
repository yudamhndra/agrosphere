from django.db import models
from django.contrib.auth.models import User

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
    
class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    