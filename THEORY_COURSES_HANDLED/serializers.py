from rest_framework import serializers
from .models import StudentFeedbackPerformance

from accounts.serializers import UserSerializer


class StudentFeedbackPerformanceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentFeedbackPerformance
        fields = '__all__'