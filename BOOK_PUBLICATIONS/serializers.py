from rest_framework import serializers
from .models import BookPublication
from accounts.serializers import UserSerializer


class BookPublicationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_proof_document(self, value):

        if not value:
            return value

        allowed_extensions = [
            'pdf',
            'jpg',
            'jpeg',
            'png',
            'gif',
            'webp'
        ]

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only pdf, jpg, jpeg, png, gif and webp files are allowed."
            )

        return value

    class Meta:
        model = BookPublication
        fields = '__all__'


class CreateBookPublicationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_proof_document(self, value):

        if not value:
            return value

        allowed_extensions = [
            'pdf',
            'jpg',
            'jpeg',
            'png',
            'gif',
            'webp'
        ]

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only pdf, jpg, jpeg, png, gif and webp files are allowed."
            )

        return value

    class Meta:
        model = BookPublication
        fields = [
            'id',
            'user',
            'book_title',
            'publisher_name',
            'publisher_type',
            'isbn_status',
            'isbn_number',
            'author_type',
            'publication_date',
            'certificate_file'
        ]