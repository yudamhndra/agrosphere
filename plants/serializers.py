from rest_framework import serializers
from .models import Plant, PlantDetection

class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = '__all__'
 
class PlantDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantDetection
        fields = '__all__'
