from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Consultancy
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import ConsultancySerializer, CreateConsultancySerializer

from accounts.models import User

import boto3
from django.conf import settings

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class ConsultancyViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action == 'approve_consultancy':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /consultancy/
    @action(detail=False, url_path='consultancy', methods=['post'])
    def create_consultancy(self, request):
        serializer = CreateConsultancySerializer(data=request.data)
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

    # GET /consultancy/user-consultancies/<register_no>/
    @action(detail=False, url_path='user-consultancies/(?P<register_no>[^/.]+)', methods=['get'])
    def user_consultancy_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        consultancies = user.consultancy_activities.all()
        serializer = ConsultancySerializer(consultancies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /consultancy/consultancies/
    @action(detail=False, url_path='consultancies', methods=['get'])
    def consultancies_list(self, request):
        consultancies = Consultancy.objects.all()
        serializer = ConsultancySerializer(consultancies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /consultancy/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_consultancy(self, request, pk=None):

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            consultancy = Consultancy.objects.get(pk=pk)
            old_file = consultancy.certificate_file
        except Consultancy.DoesNotExist:
            return Response(
                {"error": "Consultancy not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get data
        title = request.data.get("title")
        organization_name = request.data.get("organization_name")
        amount = request.data.get("amount")
        position = request.data.get("position")
        user_id = request.data.get("user")
        new_file = request.FILES.get("certificate_file")

        # Validation
        errors = {}

        # User validation
        if not user_id:
            errors["user"] = ["This field is required."]

        # Title validation
        if not title:
            errors["title"] = ["This field is required."]
        elif len(title.strip()) < 3:
            errors["title"] = ["Title must contain at least 3 characters."]

        # Organization name validation
        if not organization_name:
            errors["organization_name"] = ["This field is required."]
        elif len(organization_name.strip()) < 3:
            errors["organization_name"] = [
                "Organization name must contain at least 3 characters."
            ]

        # Amount validation
        if not amount:
            errors["amount"] = ["This field is required."]
        else:
            try:
                amount_value = float(amount)
                if amount_value < 0:
                    errors["amount"] = ["Amount must be a positive value."]
            except (ValueError, TypeError):
                errors["amount"] = ["Enter a valid number."]

        # Position validation
        allowed_positions = ["SINGLE", "OTHER"]
        if not position:
            errors["position"] = ["This field is required."]
        elif position not in allowed_positions:
            errors["position"] = [
                f"Invalid position. Allowed values are {allowed_positions}."
            ]

        # File validation
        if new_file:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            extension = new_file.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only image files (jpg, jpeg, png, gif, webp) are allowed."
                ]

        # Return errors if any
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Update fields
        consultancy.user_id = user_id
        consultancy.title = title
        consultancy.organization_name = organization_name
        consultancy.amount = amount
        consultancy.position = position

        # Update file if provided
        if new_file:
            if old_file:
                old_file.delete(save=False)
            consultancy.certificate_file = new_file

        # Reset approval
        consultancy.points = 0
        consultancy.approval_status = "pending"

        consultancy.save()

        return Response(
            {
                "id": consultancy.id,
                "user": consultancy.user_id,
                "title": consultancy.title,
                "organization_name": consultancy.organization_name,
                "amount": str(consultancy.amount),
                "position": consultancy.position,
                "certificate_file": (
                    consultancy.certificate_file.url
                    if consultancy.certificate_file
                    else None
                ),
                "approval_status": consultancy.approval_status,
                "points": consultancy.points,
            },
            status=status.HTTP_200_OK
        )

    # POST /consultancy/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_consultancy(self, request, pk=None):

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            consultancy = Consultancy.objects.get(pk=pk)
        except Consultancy.DoesNotExist:
            return Response(
                {"error": "Consultancy not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if consultancy.approval_status in ["approved", "rejected"]:
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if consultancy.user.register_no == user["register_no"]:
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

        consultancy.approval_status = status_value
        consultancy.message = message
        consultancy.approved_by = user["username"]
        consultancy.save()

        if consultancy.approval_status == "approved":
            if consultancy.position == "SINGLE":
                consultancy.points = 10
            elif consultancy.position == "OTHER":
                consultancy.points = 6
            consultancy.save()

        elif consultancy.approval_status == "rejected":
            if not consultancy.message:
                consultancy.message = (
                    f"Rejected by {user['username']} "
                    f"({user['register_no']})"
                )
            consultancy.save()

            return Response(
                {"message": consultancy.message},
                status=status.HTTP_200_OK
            )

        serializer = ConsultancySerializer(consultancy)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /consultancy/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_consultancy(self, request, pk=None):

        try:
            consultancy = Consultancy.objects.get(pk=pk)
            old_file = consultancy.certificate_file
        except Consultancy.DoesNotExist:
            return Response(
                {"error": "Consultancy not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if consultancy.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        if old_file:
            old_file.delete(save=False)

        consultancy.delete()

        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK
        )

    # GET /consultancy/<pk>/file/
    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):

        try:
            consultancy = Consultancy.objects.get(pk=pk)
        except Consultancy.DoesNotExist:
            return Response(
                {"error": "Consultancy not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not consultancy.certificate_file:
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

        key = f"Consultancy_Storage/{consultancy.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )

        return Response({"certificate_url": url})

    # GET /consultancy/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        consultancies = Consultancy.objects.filter(approval_status="pending")
        serializer = ConsultancySerializer(consultancies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)