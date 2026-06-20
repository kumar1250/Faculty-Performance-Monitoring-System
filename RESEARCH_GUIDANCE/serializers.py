from rest_framework import serializers
from .models import ResearchGuidance
from accounts.serializers import UserSerializer


class ResearchGuidanceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = ResearchGuidance
        fields = '__all__'


class CreateResearchGuidanceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
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