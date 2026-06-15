from rest_framework import serializers
from .models import StudentFeedbackPerformance


class StudentFeedbackPerformanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentFeedbackPerformance
        fields = '__all__'