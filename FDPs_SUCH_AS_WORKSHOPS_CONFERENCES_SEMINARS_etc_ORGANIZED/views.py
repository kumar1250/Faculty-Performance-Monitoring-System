from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import FDPs_Organized
from .serializers import FDPsOrganizedSerializer, CreateFDPsOrganizedSerializer

from accounts.models import User
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD

import boto3
from django.conf import settings

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .utils import send_fdp_organized_status_email
class FDPsOrganizedViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action == 'approve_fdp':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /fdps/fdp/
    @action(detail=False, url_path='fdp', methods=['post'])
    def create_fdp(self, request):
        serializer = CreateFDPsOrganizedSerializer(data=request.data)
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

    # GET /fdps/userfdps/<register_no>/
    @action(detail=False, url_path='userfdps/(?P<register_no>[^/.]+)', methods=['get'])
    def user_fdp_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        fdps = user.fdps_organizeds.all()
        serializer = FDPsOrganizedSerializer(fdps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /fdps/fdps/
    @action(detail=False, url_path='fdps', methods=['get'])
    def fdps_list(self, request):
        fdps = FDPs_Organized.objects.all()
        serializer = FDPsOrganizedSerializer(fdps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /fdps/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_fdp(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            fdp = FDPs_Organized.objects.get(pk=pk)
            old_file = fdp.certificate_file
        except FDPs_Organized.DoesNotExist:
            return Response(
                {"error": "FDP not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get data
        title           = request.data.get("title")
        activity_type   = request.data.get("activity_type")
        funding_type    = request.data.get("funding_type")
        level           = request.data.get("level")
        duration        = request.data.get("duration")
        capacity        = request.data.get("capacity")
        user_id         = request.data.get("user")
        new_file        = request.FILES.get("certificate_file")

        errors = {}

        # User validation
        if not user_id:
            errors["user"] = ["This field is required."]

        # Title validation
        if not title:
            errors["title"] = ["This field is required."]
        elif len(title.strip()) < 3:
            errors["title"] = ["Title must contain at least 3 characters."]

        # Activity type validation
        allowed_activity_types = ["CONFERENCE", "FDP"]
        if not activity_type:
            errors["activity_type"] = ["This field is required."]
        elif activity_type not in allowed_activity_types:
            errors["activity_type"] = [
                f"Invalid activity type. Allowed values are {allowed_activity_types}."
            ]

        # Funding type validation
        allowed_funding_types = ["EXTERNAL", "INTERNAL"]
        if not funding_type:
            errors["funding_type"] = ["This field is required."]
        elif funding_type not in allowed_funding_types:
            errors["funding_type"] = [
                f"Invalid funding type. Allowed values are {allowed_funding_types}."
            ]

        # Level validation
        allowed_levels = ["INTERNATIONAL", "NATIONAL"]
        if not level:
            errors["level"] = ["This field is required."]
        elif level not in allowed_levels:
            errors["level"] = [
                f"Invalid level. Allowed values are {allowed_levels}."
            ]

        # Duration validation — required only for FDP/Workshop
        allowed_durations = ["GE_2W", "BW_1W_2W", "LT_1W"]
        if activity_type == "FDP":
            if not duration:
                errors["duration"] = ["Duration is required for FDP/Workshop."]
            elif duration not in allowed_durations:
                errors["duration"] = [
                    f"Invalid duration. Allowed values are {allowed_durations}."
                ]

        # Capacity validation
        allowed_capacities = ["CONVENOR", "CO_CONVENOR"]
        if not capacity:
            errors["capacity"] = ["This field is required."]
        elif capacity not in allowed_capacities:
            errors["capacity"] = [
                f"Invalid capacity. Allowed values are {allowed_capacities}."
            ]

        # File validation
        if new_file:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            extension = new_file.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only image files (jpg, jpeg, png, gif, webp) are allowed."
                ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Apply updates
        fdp.user_id       = user_id
        fdp.title         = title
        fdp.activity_type = activity_type
        fdp.funding_type  = funding_type
        fdp.level         = level
        fdp.capacity      = capacity
        fdp.duration      = duration if activity_type == "FDP" else None

        if new_file:
            if old_file:
                old_file.delete(save=False)
            fdp.certificate_file = new_file

        # Reset approval on update
        fdp.points          = 0
        fdp.approval_status = "pending"
        fdp.save()

        return Response(
            {
                "id":               fdp.id,
                "user":             fdp.user_id,
                "title":            fdp.title,
                "activity_type":    fdp.activity_type,
                "funding_type":     fdp.funding_type,
                "level":            fdp.level,
                "duration":         fdp.duration,
                "capacity":         fdp.capacity,
                "certificate_file": fdp.certificate_file.url if fdp.certificate_file else None,
                "approval_status":  fdp.approval_status,
                "points":           fdp.points,
            },
            status=status.HTTP_200_OK
        )

    # POST /fdps/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_fdp(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            fdp = FDPs_Organized.objects.get(pk=pk)
        except FDPs_Organized.DoesNotExist:
            return Response(
                {"error": "FDP not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if fdp.approval_status in ["approved", "rejected"]:
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if fdp.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        status_value = request.data.get("status")
        message      = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        fdp.approval_status = status_value
        fdp.message         = message
        fdp.approved_by     = user["username"]
        fdp.save()

        if fdp.approval_status == "approved":
            # Points logic based on activity_type, level, funding, duration, and capacity
            base_points = 0

            if fdp.activity_type == "CONFERENCE":
                if fdp.level == "INTERNATIONAL":
                    base_points = 10 if fdp.funding_type == "EXTERNAL" else 7
                elif fdp.level == "NATIONAL":
                    base_points = 7 if fdp.funding_type == "EXTERNAL" else 5

            elif fdp.activity_type == "FDP":
                if fdp.duration == "GE_2W":
                    base_points = 10
                elif fdp.duration == "BW_1W_2W":
                    base_points = 7
                elif fdp.duration == "LT_1W":
                    base_points = 5

            # Co-convenor gets half points
            if fdp.capacity == "CO_CONVENOR":
                base_points = base_points / 2

            fdp.points = base_points
            fdp.save()
            try:
                send_fdp_organized_status_email(
                email=fdp.user.email,
                username=fdp.user.username,
                event_title=fdp.title,  # Replace with your actual field name
                status=fdp.approval_status,
                message=fdp.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

        elif fdp.approval_status == "rejected":
            if not fdp.message:
                fdp.message = (
                    f"Rejected by {user['username']} "
                    f"({user['register_no']})"
                )
            fdp.save()
            try:
                send_fdp_organized_status_email(
                email=fdp.user.email,
                username=fdp.user.username,
                event_title=fdp.title,  # Replace with your actual field name
                status=fdp.approval_status,
                message=fdp.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

            return Response(
                {"message": fdp.message},
                status=status.HTTP_200_OK
            )

        serializer = FDPsOrganizedSerializer(fdp)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /fdps/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_fdp(self, request, pk=None):
        try:
            fdp = FDPs_Organized.objects.get(pk=pk)
            old_file = fdp.certificate_file
        except FDPs_Organized.DoesNotExist:
            return Response(
                {"error": "FDP not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if fdp.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        if old_file:
            old_file.delete(save=False)

        fdp.delete()
        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK
        )

    # GET /fdps/<pk>/file/
    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            fdp = FDPs_Organized.objects.get(pk=pk)
        except FDPs_Organized.DoesNotExist:
            return Response(
                {"error": "FDP not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not fdp.certificate_file:
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

        key = f"FDPs_Organized_Storage/{fdp.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key":    key
            },
            ExpiresIn=3600
        )

        return Response({"certificate_url": url})

    # GET /fdps/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        fdps = FDPs_Organized.objects.filter(approval_status="pending")
        serializer = FDPsOrganizedSerializer(fdps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)