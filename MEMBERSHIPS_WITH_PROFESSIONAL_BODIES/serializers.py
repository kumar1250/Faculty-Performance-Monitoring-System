from rest_framework import serializers
from .models import ProfessionalMembership
from accounts.serializers import UserSerializer


class ProfessionalMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        extension = value.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
            )
        return value
    class Meta:
        model = ProfessionalMembership
        fields = '__all__'


class CreateProfessionalMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    def validate_certificate_file(self, value):
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
        extension = value.name.split('.')[-1].lower()
        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only image files 'jpg', 'jpeg', 'png', 'gif', 'webp' are allowed."
            )
        return value

    class Meta:
        model = ProfessionalMembership
        fields = [
            'id',
            'user',
            'organization_name',
            'membership_type',
            'membership_id',
            'membership_date',
            'certificate_file'
        ]