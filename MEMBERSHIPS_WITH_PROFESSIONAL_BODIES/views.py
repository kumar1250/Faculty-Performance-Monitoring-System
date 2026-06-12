from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import ProfessionalMembership
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import ProfessionalMembershipSerializer, CreateProfessionalMembershipSerializer
from accounts.models import User
import boto3
from django.conf import settings


class ProfessionalMembershipViewSet(ViewSet):

    def get_permissions(self):
        if self.action == 'approve_membership':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, url_path='membership', methods=['post'])
    def create_membership(self, request):
        serializer = CreateProfessionalMembershipSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, url_path='usermemberships/(?P<register_no>[^/.]+)', methods=['get'])
    def user_membership_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        memberships = user.professional_memberships.all()
        serializer = ProfessionalMembershipSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, url_path='memberships', methods=['get'])
    def memberships_list(self, request):
        memberships = ProfessionalMembership.objects.all()
        serializer = ProfessionalMembershipSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_path='update', methods=['put'])
    def update_membership(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            membership = ProfessionalMembership.objects.get(pk=pk)
            old_file = membership.certificate_file
        except ProfessionalMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CreateProfessionalMembershipSerializer(membership, data=request.data, partial=True)
        if serializer.is_valid():
            updated_data = serializer.save()
            if old_file and old_file != updated_data.certificate_file:
                old_file.delete(save=False)
            membership.points = 0
            membership.approval_status = "pending"
            membership.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, url_path='approve', methods=['post'])
    def approve_membership(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            membership = ProfessionalMembership.objects.get(pk=pk)
        except ProfessionalMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if membership.approval_status in ["approved", "rejected"]:
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if membership.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        status_value = request.data.get("status")
        message = request.data.get("message")
        if status_value not in ["approved", "rejected"]:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        membership.approval_status = status_value
        membership.message = message
        membership.approved_by = user["username"]
        membership.save()

        if membership.approval_status == "approved":
            if membership.membership_type == "INTERNATIONAL":
                membership.points = 10
            elif membership.membership_type == "NATIONAL":
                membership.points = 8
            membership.save()

        elif membership.approval_status == "rejected":
            if not membership.message:
                membership.message = (
                    f"Rejected by {user['username']} "
                    f"({user['register_no']})"
                )
            membership.save()
            return Response(
                {"message": membership.message},
                status=status.HTTP_200_OK
            )

        serializer = ProfessionalMembershipSerializer(membership)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_membership(self, request, pk=None):
        try:
            membership = ProfessionalMembership.objects.get(pk=pk)
            old_file = membership.certificate_file
        except ProfessionalMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if membership.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        if old_file:
            old_file.delete(save=False)
        membership.delete()
        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            membership = ProfessionalMembership.objects.get(pk=pk)
        except ProfessionalMembership.DoesNotExist:
            return Response(
                {"error": "Membership not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not membership.certificate_file:
            return Response(
                {"error": "No certificate file uploaded"},
                status=status.HTTP_404_NOT_FOUND
            )
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": f"MembershipStorage/{membership.certificate_file.name}"
            },
            ExpiresIn=3600
        )
        return Response({"certificate_url": url})

    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        memberships = ProfessionalMembership.objects.filter(approval_status="pending")
        serializer = ProfessionalMembershipSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)