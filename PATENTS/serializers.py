from rest_framework import serializers
from .models import Patent
from accounts.serializers import UserSerializer


class PatentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files with extensions 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
            )
        return value

    class Meta:
        model = Patent
        fields = '__all__'


class CreatePatentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files with extensions 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
            )
        return value

    class Meta:
        model = Patent
        fields = [
            'id',
            'user',
            'title',
            'patent_number',
            'patent_type',
            'certificate_file',
        ]
