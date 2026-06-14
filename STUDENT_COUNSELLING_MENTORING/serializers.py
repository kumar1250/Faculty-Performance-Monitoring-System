from rest_framework import serializers
from .models import StudentCounselling


class StudentCounsellingSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentCounselling
        fields = '__all__'


class CreateStudentCounsellingSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentCounselling
        fields = [
            'id',
            'faculty',
            'total_students'
        ]