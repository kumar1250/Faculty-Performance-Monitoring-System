from rest_framework import serializers
from .models import ResearchGuidance


class ResearchGuidanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchGuidance
        fields = '__all__'


class CreateResearchGuidanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResearchGuidance
        fields = [
            'id',
            'user',
            'scholar_name',
            'guide_type',
            'registration_date',
            'awarded_date',
            'status'
        ]