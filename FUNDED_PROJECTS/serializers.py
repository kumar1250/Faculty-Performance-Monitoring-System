from rest_framework import serializers
from .models import FundedProject
from accounts.serializers import UserSerializer


class FundedProjectSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = FundedProject
        fields = '__all__'


class CreateFundedProjectSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

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