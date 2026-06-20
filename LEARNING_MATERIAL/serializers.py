from rest_framework import serializers
from .models import SubjectContribution
from accounts.serializers import UserSerializer


class SubjectContributionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SubjectContribution
        fields = '__all__'


class CreateSubjectContributionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SubjectContribution
        fields = [
            'id',
            'user',
            'subject_name',
            'academic_year',
            'semester'
        ]