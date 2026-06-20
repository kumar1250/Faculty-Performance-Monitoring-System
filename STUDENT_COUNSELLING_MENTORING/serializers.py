from rest_framework import serializers
from .models import StudentCounselling
from accounts.serializers import UserSerializer


class StudentCounsellingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentCounselling
        fields = '__all__'


class CreateStudentCounsellingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = StudentCounselling
        fields = [
            'id',
            'faculty',
            'total_students'
        ]