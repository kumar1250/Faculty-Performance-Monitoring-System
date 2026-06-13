from rest_framework import serializers
from .models import FDPs_Attended


class FDPsAttendedSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']

            extension = value.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only 'jpg', 'jpeg', 'png', 'gif', 'webp', and 'pdf' files are allowed."
                )

        return value

    class Meta:
        model = FDPs_Attended
        fields = '__all__'


class CreateFDPsAttendedSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']

            extension = value.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only 'jpg', 'jpeg', 'png', 'gif', 'webp', and 'pdf' files are allowed."
                )

        return value

    class Meta:
        model = FDPs_Attended
        fields = [
            'id',
            'user',
            'title',
            'category',
            'institute',
            'duration',
            'level',
            'certificate_file'
        ]