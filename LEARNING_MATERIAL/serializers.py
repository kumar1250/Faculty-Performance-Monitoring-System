from rest_framework import serializers
from .models import SubjectContribution


class SubjectContributionSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubjectContribution
        fields = '__all__'


class CreateSubjectContributionSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubjectContribution
        fields = [
            'id',
            'user',
            'subject_name',
            'academic_year',
            'semester'
        ]