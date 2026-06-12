from rest_framework import serializers
from .models import Publication


class PublicationSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

            extension = value.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
                )

        return value

    class Meta:
        model = Publication
        fields = '__all__'


class CreatePublicationSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        if value:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

            extension = value.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only image files 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
                )

        return value

    class Meta:
        model = Publication
        fields = [
            'id',
            'user',
            'title',
            'publication_type',
            'indexing_type',
            'author_type',
            'publisher_name',
            'publication_date',
            'certificate_file'
        ]