from rest_framework import serializers
from .models import Plant, PlantDetection, Disease, Recomendation, Notification, DetectionHistory

class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = '__all__'
 
class PlantDetectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantDetection
        fields = '__all__'
        
class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = '__all__'

class RecomendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recomendation
        fields = '__all__'
        
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        
class DetectionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionHistory
        fields = '__all__'