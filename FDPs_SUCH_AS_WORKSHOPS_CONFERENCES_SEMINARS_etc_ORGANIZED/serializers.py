from rest_framework import serializers
from .models import FDPs_Organized


class FDPsOrganizedSerializer(serializers.ModelSerializer):

    def validate_CertificateError_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
            )

        return value

    class Meta:
        model = FDPs_Organized
        fields = '__all__'


class CreateFDPsOrganizedSerializer(serializers.ModelSerializer):

    def validate_CertificateError_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
            )

        return value

    class Meta:
        model = FDPs_Organized
        fields = [
            'id',
            'user',
            'title',
            'activity_type',
            'funding_type',
            'level',
            'duration',
            'capacity',
            'Certificate_file'
        ]