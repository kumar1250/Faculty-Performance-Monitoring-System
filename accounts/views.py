# Create your views here.
from urllib import request

from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import IsAuthenticated, IsPrincipal, IsDean, IsHOD, IsCommittee_Coordinator, IsDepartment_Incharge, IsFaculty
from .token_jwt import create_token, decode_token, get_token_from_request
from django.contrib.auth.hashers import check_password
from rest_framework import status
from .models import User, BlacklistedToken, PasswordResetOTP
from .serializers import (UserRegistrationSerializer, UserUpdateSerializer,ForgotPasswordSerializer, VerifyOTPSerializer,ResetPasswordSerializer)
from .utils import send_otp_email
from rest_framework import viewsets, status, permissions
from .models import Profile
from .serializers import ProfileSerializer
import boto3
from django.conf import settings


class UserViewSet(ViewSet):

    @action(detail=False, methods=['post'],url_path='register')
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            role_points = {
            'principal': 10,
            'dean': 9,
            'hod': 8,
            'committee_coordinator': 7,
            'department_incharge': 6,
            'faculty': 5,
        }
            if serializer.data['role']in role_points:
                user = User.objects.get(id=serializer.data['id'])
                user.points = role_points[serializer.data['role']]
                user.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'],url_path='login')
    def login(self, request):
        username = str(request.data.get('username'))
        password = request.data.get('password')
        try:
            if '@' in username:
                user = User.objects.get(email=username)
            else:
                user = User.objects.get(register_no=username)
            if check_password(password, user.password):
                token = create_token(user)
                return Response({'token': token}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['get'],url_path='details', permission_classes=[IsAuthenticated])
    def user_details(self, request):
        user = decode_token(get_token_from_request(request))
        if user:
            data = User.objects.get(id=user['user_id'])
            serializer = UserRegistrationSerializer(data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['post'], url_path='logout', permission_classes=[IsAuthenticated])
    def logout(self, request):
        token = get_token_from_request(request)
        if token:
            BlacklistedToken.objects.create(token=token)
            return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='list', permission_classes=[IsAuthenticated])
    def user_list(self, request):
        users = User.objects.all()
        serializer = UserRegistrationSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], url_path='delete', permission_classes=[IsAuthenticated])
    def delete_user(self, request, pk=None):
        user = decode_token(get_token_from_request(request))
        if user and user['role'] in ['principal', 'dean', 'hod']:
            try:
                user_to_delete = User.objects.get(id=pk)
                user_to_delete.delete()
                return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    @action(detail=True, methods=['patch'], url_path='updateuser', permission_classes=[IsAuthenticated])
    def update_user(self, request, pk=None):
        user = decode_token(get_token_from_request(request))
        
        if user and user['role'] in ['principal', 'dean', 'hod']:
            try:
                user_to_update = User.objects.get(id=pk)
                user_to_update_role = user_to_update.role
                serializer = UserUpdateSerializer(user_to_update, data=request.data,partial=True)
                if serializer.is_valid():
                    serializer.save()
                
                    role_points = {
                            'principal': 10,
                            'dean': 9,
                            'hod': 8,
                            'committee_coordinator': 7,
                            'department_incharge': 6,
                            'faculty': 5,
                            }
                    if serializer.data['role'] in role_points:
                        user_to_update.save()
                        new_role = serializer.validated_data.get('role', user_to_update_role)
                        user_to_update.points += role_points[new_role]
                        user_to_update.points -= role_points[user_to_update_role]
                        user_to_update.save()
                    return Response({"username": user_to_update.username,"email": user_to_update.email,"register_no": user_to_update.register_no,"role": user_to_update.role}, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    

    # ─────────────────────────────────────────────
    # STEP 1 — User enters email → OTP sent
    # ─────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='forgot-password')
    def forgot_password(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        email = serializer.validated_data['email']
    
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal whether email exists or not
            return Response(
                {'message': 'If this email exists, an OTP has been sent.'},
                status=status.HTTP_200_OK
            )
    
        # Invalidate all old unused OTPs for this user
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
    
        # Create new OTP
        otp = PasswordResetOTP.generate_otp()
        PasswordResetOTP.objects.create(user=user, otp=otp)
    
        try:
            send_otp_email(user.email, otp, user.username)
        except Exception as e:
            return Response(
                {'error': f'Failed to send email. Please try again later {str(e)} .'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
        return Response({'message': 'OTP sent to your email.'}, status=status.HTTP_200_OK)
    
    
    # ─────────────────────────────────────────────
    # STEP 2 — User enters OTP → gets reset_token
    # ─────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='verify-otp')
    def verify_otp(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
    
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid email.'}, status=status.HTTP_400_BAD_REQUEST)
    
        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            otp=otp,
            is_used=False
        ).order_by('-created_at').first()
    
        if not otp_record or not otp_record.is_valid():
            return Response({'error': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)
    
        # Generate reset_token and attach to this OTP record
        reset_token = PasswordResetOTP.generate_reset_token()
        otp_record.reset_token = reset_token
        otp_record.save()
    
        # Return reset_token to frontend (frontend stores it temporarily)
        return Response({
            'message': 'OTP verified successfully.',
            'reset_token': reset_token
        }, status=status.HTTP_200_OK)
    
    
    # ─────────────────────────────────────────────
    # STEP 3 — User enters new password → done
    # (no email or OTP needed again)
    # ─────────────────────────────────────────────
    @action(detail=False, methods=['post'], url_path='reset-password')
    def reset_password(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        reset_token = serializer.validated_data['reset_token']
        new_password = serializer.validated_data['new_password']
    
        # Find OTP record by reset_token
        otp_record = PasswordResetOTP.objects.filter(
            reset_token=reset_token,
            is_used=False
        ).order_by('-created_at').first()
    
        if not otp_record or not otp_record.is_valid():
            return Response(
                {'error': 'Invalid or expired reset token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Mark as used so this token cannot be reused
        otp_record.is_used = True
        otp_record.save()
    
        # Update the password
        user = otp_record.user
        user.password = new_password  # model.save() will hash it automatically
        user.save()

        return Response({'message': 'Password reset successfully.'}, status=status.HTTP_200_OK)
    
    
class ProfileViewSet(viewsets.ViewSet):
    
    def get_s3_client(self):
        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

    def _serialize_with_image_url(self, profile):
        """Shared by get_my_profile and get_profile_by_register_no so the
        presigned-URL logic only lives in one place."""
        serializer = ProfileSerializer(profile)
        data = serializer.data

        if profile.profile_image:
            s3 = self.get_s3_client()
            # Must match Profile_image storage's `location = "profile_image"`
            # in core/storage.py — that's the actual prefix S3Storage uses
            # when uploading, so the presigned URL has to use the same key
            # or it points at a file that was never written.
            key = f"profile_image/{profile.profile_image.name}"
            url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": key,
                },
                ExpiresIn=3600,
            )
            data['profile_image_url'] = url

        return data

    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def get_my_profile(self, request):
        user_data = decode_token(get_token_from_request(request))
        if not user_data:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(register_no=user_data["register_no"])
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        profile, _ = Profile.objects.get_or_create(user=user)
        return Response(self._serialize_with_image_url(profile))

    # Lets the Portfolio page show the profile header (avatar, headline,
    # department, experience, bio) when viewing someone else's portfolio in
    # read-only mode, e.g. /profile/:registerNo on the frontend.
    @action(detail=False, methods=['get'], url_path='by-register/(?P<register_no>[^/.]+)', permission_classes=[IsAuthenticated])
    def get_profile_by_register_no(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        profile, _ = Profile.objects.get_or_create(user=user)
        return Response(self._serialize_with_image_url(profile))

    @action(detail=False, methods=['put'], url_path='update', permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        user_data = decode_token(get_token_from_request(request))
        if not user_data:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(register_no=user_data["register_no"])
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Use get_or_create instead of user.profile so a missing Profile row
        # (e.g. never created for this user) doesn't raise
        # Profile.RelatedObjectDoesNotExist and crash with a 500.
        profile, _ = Profile.objects.get_or_create(user=user)

        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)