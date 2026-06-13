from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Patent
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import PatentSerializer, CreatePatentSerializer
from accounts.models import User
import boto3
from django.conf import settings


class PatentViewSet(ViewSet):
    def get_permissions(self):
        if self.action == 'approve_patent':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, url_path='patent', methods=['post'])
    def create_patent(self, request):
        patent_serializer = CreatePatentSerializer(data=request.data)
        if patent_serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            patent_serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(
                patent_serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            patent_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False, url_path='userpatents/(?P<register_no>[^/.]+)', methods=['get'])
    def user_patent_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        patents = user.patent_activities.all()
        serializer = PatentSerializer(patents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, url_path='patents', methods=['get'])
    def patents_list(self, request):
        patents = Patent.objects.all()
        serializer = PatentSerializer(patents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_path='update', methods=['put'])
    def update_patent(self, request, pk=None):
    
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
        try:
            patent = Patent.objects.get(pk=pk)
            old_file = patent.certificate_file
        except Patent.DoesNotExist:
            return Response(
                {"error": "Patent not found"},
                status=status.HTTP_404_NOT_FOUND
            )
    
        # Get data
        title = request.data.get("title")
        patent_number = request.data.get("patent_number")
        patent_type = request.data.get("patent_type")
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
            errors["title"] = [
                "Title must contain at least 3 characters."
            ]
    
        # Patent Number validation
        if not patent_number:
            errors["patent_number"] = ["This field is required."]
        else:
            exists = Patent.objects.exclude(pk=pk).filter(
                patent_number=patent_number
            ).exists()
    
            if exists:
                errors["patent_number"] = [
                    "Patent number already exists."
                ]
    
        # Patent Type validation
        allowed_types = [
            "GRANTED_FIRST",
            "GRANTED_OTHER",
            "PUBLISHED_FIRST",
            "PUBLISHED_OTHER"
        ]
    
        if not patent_type:
            errors["patent_type"] = ["This field is required."]
        elif patent_type not in allowed_types:
            errors["patent_type"] = [
                f"Invalid patent type. Allowed values are {allowed_types}"
            ]
    
        # File validation
        if new_file:
    
            allowed_extensions = [
                'pdf',
                'jpg',
                'jpeg',
                'png'
            ]
    
            extension = new_file.name.split('.')[-1].lower()
    
            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only pdf, jpg, jpeg and png files are allowed."
                ]
    
        # Return errors
        if errors:
            return Response(
                errors,
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # Update fields
        patent.user_id = user_id
        patent.title = title
        patent.patent_number = patent_number
        patent.patent_type = patent_type
    
        # Update file
        if new_file:
    
            if old_file:
                old_file.delete(save=False)
    
            patent.certificate_file = new_file
    
        # Reset approval
        patent.approval_status = "pending"
        patent.approved_by = None
        patent.message = None
    
        # Save (points will be recalculated automatically in model save())
        patent.save()
    
        return Response(
            {
                "id": patent.id,
                "user": patent.user_id,
                "title": patent.title,
                "patent_number": patent.patent_number,
                "patent_type": patent.patent_type,
                "certificate_file": (
                    patent.certificate_file.url
                    if patent.certificate_file
                    else None
                ),
                "points": patent.points,
                "approval_status": patent.approval_status
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, url_path='approve', methods=['post'])
    def approve_patent(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            patent = Patent.objects.get(pk=pk)
        except Patent.DoesNotExist:
            return Response(
                {"error": "Patent not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if patent.approval_status in ["approved", "rejected"]:
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if patent.user.register_no == user["register_no"]:
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
        patent.approval_status = status_value
        patent.message = message
        patent.approved_by = user["username"]
        patent.points = 0

        if status_value == "rejected":
            if not patent.message:
                patent.message = (
                    f"Rejected by {user['username']} "
                    f"({user['register_no']})"
                )
            patent.save()
            return Response(
                {"message": patent.message},
                status=status.HTTP_200_OK
            )

        # On approval, points are auto-assigned by Patent.save() via point_map:
        # GRANTED_FIRST -> 10, GRANTED_OTHER -> 9,
        # PUBLISHED_FIRST -> 8, PUBLISHED_OTHER -> 7
        patent.save()
        serializer = PatentSerializer(patent)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_patent(self, request, pk=None):
        try:
            patent = Patent.objects.get(pk=pk)
            old_file = patent.certificate_file
        except Patent.DoesNotExist:
            return Response(
                {"error": "Patent not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if patent.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        if old_file:
            old_file.delete(save=False)
        patent.delete()
        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            patent = Patent.objects.get(pk=pk)
        except Patent.DoesNotExist:
            return Response(
                {"error": "Patent not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        if not patent.certificate_file:
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
                "Key": f"Patent_Certificate/{patent.certificate_file.name}"
            },
            ExpiresIn=3600
        )
        return Response({"certificate_url": url})

    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        patents = Patent.objects.filter(approval_status="pending")
        serializer = PatentSerializer(patents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
