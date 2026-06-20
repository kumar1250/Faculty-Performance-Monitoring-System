from rest_framework import serializers
from .models import User
from .models import Profile

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'register_no', 'email', 'password', 'role',]

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username','email','register_no', 'password','role']
        
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    reset_token = serializers.CharField()    # received from verify-otp step
    new_password = serializers.CharField(min_length=8)

class ProfileSerializer(serializers.ModelSerializer):
    username= UserRegistrationSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'username', 'profile_image', 'headline', 'bio', 'department', 'experience_years']