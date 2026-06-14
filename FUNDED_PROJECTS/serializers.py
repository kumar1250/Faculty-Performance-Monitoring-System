from rest_framework import serializers
from .models import FundedProject


class FundedProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = FundedProject
        fields = '__all__'


class CreateFundedProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = FundedProject
        fields = [
            'id',
            'user',
            'project_title',
            'funding_agency',
            'grant_amount',
            'grant_category',
            'investigator_role',
            'sanction_date',
            'completion_date',
        ]