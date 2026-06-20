from rest_framework import serializers
from .models import StudentProjectWork
from accounts.serializers import UserSerializer


class StudentProjectWorkSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files are 'jpg', 'jpeg', 'png', 'gif', 'webp' allowed."
            )

        return value

    class Meta:
        model = StudentProjectWork
        fields = '__all__'


class CreateStudentProjectWorkSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files are 'jpg', 'jpeg', 'png', 'gif', 'webp' allowed."
            )

        return value

    class Meta:
        model = StudentProjectWork
        fields = [
            'id',
            'user',
            'project_title',
            'project_type',
            'publication_status',
            'student_names',
            'academic_year',
            'certificate_file'
        ]