from rest_framework import serializers
from .models import StudentFeedbackPerformance
from accounts.serializers import UserSerializer


class StudentFeedbackPerformanceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    # Flat fields the frontend reads directly from the record object
    register_no  = serializers.CharField(source='user.register_no', read_only=True)
    faculty_name = serializers.CharField(source='user.username',    read_only=True)

    # Who uploaded this entry — frontend uses this to decide if the
    # current viewer is allowed to edit/delete it.
    created_by          = serializers.IntegerField(source='created_by.id', read_only=True, default=None)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)

    class Meta:
        model  = StudentFeedbackPerformance
        fields = '__all__'