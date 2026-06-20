from rest_framework import serializers
from .models import ChairingSession
from accounts.serializers import UserSerializer


class ChairingSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_certificate_file(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

            extension = value.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files with extensions 'jpg', 'jpeg', 'png', 'gif', and 'webp' are allowed."
                )

        return value

    class Meta:
        model = ChairingSession
        fields = '__all__'

class CreateChairingSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_certificate_file(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

            extension = value.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files with extensions 'jpg', 'jpeg', 'png', 'gif', and 'webp' are allowed."
                )

        return value

    class Meta:
        model = ChairingSession
        fields = [
            'id',
            'user',
            'event_name',
            'event_type',
            'organization',
            'event_date',
            'certificate_file',
            'event_level',
        ]