from rest_framework import serializers
from .models import Consultancy

class ConsultancySerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files are 'jpg', 'jpeg', 'png', 'gif', 'webp' allowed."
            )

        return value

    class Meta:
        model = Consultancy
        fields = '__all__'


class CreateConsultancySerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files are 'jpg', 'jpeg', 'png', 'gif', 'webp' allowed."
            )

        return value

    class Meta:
        model = Consultancy
        fields = [
            'id',
            'user',
            'title',
            'organization_name',
            'amount',
            'position',
            'certificate_file'
        ]
