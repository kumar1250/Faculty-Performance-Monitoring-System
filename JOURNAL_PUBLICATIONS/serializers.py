from rest_framework import serializers
from .models import JournalPublication


class JournalPublicationSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only jpg, jpeg, png, gif, webp and pdf files are allowed."
            )

        return value

    class Meta:
        model = JournalPublication
        fields = '__all__'


class CreateJournalPublicationSerializer(serializers.ModelSerializer):

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only jpg, jpeg, png, gif, webp and pdf files are allowed."
            )

        return value

    class Meta:
        model = JournalPublication
        fields = [
            'id',
            'user',
            'publication_title',
            'journal_name',
            'publication_type',
            'author_type',
            'doi_number',
            'publication_date',
            'certificate_file'
        ]