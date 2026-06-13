from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import FDPs_Attended
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD, IsPrincipal, IsDean, IsFaculty, IsCommittee_Coordinator, IsDepartment_Incharge
from .serializers import FDPsAttendedSerializer, CreateFDPsAttendedSerializer
from accounts.models import User
import boto3
from django.conf import settings


def calculate_fdp_points(category, institute, duration=None, level=None):
    """
    Calculate points based on the scoring table.

    FDP/WORKSHOPS:
        IIT:        >=2W=10, 1W-2W=9, <1W=8
        NIT:        >=2W=9,  1W-2W=8, <1W=7
        University: >=2W=8,  1W-2W=7, <1W=6
        College:    >=2W=7,  1W-2W=6, <1W=5

    CONFERENCE/SEMINARS:
        Abroad:     International=10
        IIT:        International=9,  National=7
        NIT:        International=8,  National=6
        University: International=7,  National=5
        College:    International=5,  National=3
    """
    if category == 'FDP':
        fdp_points = {
            'IIT':        {'GE_2W': 10, 'BW_1W_2W': 9, 'LT_1W': 8},
            'NIT':        {'GE_2W': 9,  'BW_1W_2W': 8, 'LT_1W': 7},
            'UNIVERSITY': {'GE_2W': 8,  'BW_1W_2W': 7, 'LT_1W': 6},
            'COLLEGE':    {'GE_2W': 7,  'BW_1W_2W': 6, 'LT_1W': 5},
        }
        institute_map = fdp_points.get(institute)
        if institute_map and duration:
            return institute_map.get(duration, 0)
        return 0

    elif category == 'CONFERENCE':
        conference_points = {
            'ABROAD':     {'INTERNATIONAL': 10},
            'IIT':        {'INTERNATIONAL': 9,  'NATIONAL': 7},
            'NIT':        {'INTERNATIONAL': 8,  'NATIONAL': 6},
            'UNIVERSITY': {'INTERNATIONAL': 7,  'NATIONAL': 5},
            'COLLEGE':    {'INTERNATIONAL': 5,  'NATIONAL': 3},
        }
        institute_map = conference_points.get(institute)
        if institute_map and level:
            return institute_map.get(level, 0)
        return 0

    return 0


class FDPsAttendedViewSet(ViewSet):

    def get_permissions(self):
        if self.action == 'approve_fdp':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /fdp/create/
    @action(detail=False, url_path='create', methods=['post'])
    def create_fdp(self, request):
        serializer = CreateFDPsAttendedSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = decode_token(get_token_from_request(request))
            except Exception:
                return Response(
                    {"error": "User not logged in"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /fdp/user/<register_no>/
    @action(detail=False, url_path='user/(?P<register_no>[^/.]+)', methods=['get'])
    def user_fdp_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        fdps = user.fdp_activities.all()
        serializer = FDPsAttendedSerializer(fdps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /fdp/all/
    @action(detail=False, url_path='all', methods=['get'])
    def fdp_list(self, request):
        fdps = FDPs_Attended.objects.all()
        serializer = FDPsAttendedSerializer(fdps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /fdp/<pk>/update/
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
            fdp = FDPs_Attended.objects.get(pk=pk)
            old_file = fdp.certificate_file
        except FDPs_Attended.DoesNotExist:
            return Response(
                {"error": "FDP record not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if fdp.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        title = request.data.get("title")
        category = request.data.get("category")
        institute = request.data.get("institute")
        duration = request.data.get("duration")
        level = request.data.get("level")
        new_file = request.FILES.get("certificate_file")

        errors = {}

        # Title validation
        if not title:
            errors["title"] = ["This field is required."]
        elif len(title.strip()) < 3:
            errors["title"] = ["Title must contain at least 3 characters."]

        # Category validation
        allowed_categories = ["FDP", "CONFERENCE"]
        if not category:
            errors["category"] = ["This field is required."]
        elif category not in allowed_categories:
            errors["category"] = [
                f"Invalid category. Allowed values are {allowed_categories}"
            ]

        # Institute validation
        allowed_institutes = [
            "IIT",
            "NIT",
            "UNIVERSITY",
            "COLLEGE",
            "ABROAD"
        ]
        if not institute:
            errors["institute"] = ["This field is required."]
        elif institute not in allowed_institutes:
            errors["institute"] = [
                f"Invalid institute. Allowed values are {allowed_institutes}"
            ]

        # Duration validation
        allowed_durations = [
            "GE_2W",
            "BW_1W_2W",
            "LT_1W"
        ]
        if duration:
            if duration not in allowed_durations:
                errors["duration"] = [
                    f"Invalid duration. Allowed values are {allowed_durations}"
                ]

        # Level validation
        allowed_levels = [
            "INTERNATIONAL",
            "NATIONAL"
        ]
        if level:
            if level not in allowed_levels:
                errors["level"] = [
                    f"Invalid level. Allowed values are {allowed_levels}"
                ]

        # File validation
        if new_file:
            allowed_extensions = [
                'jpg',
                'jpeg',
                'png',
                'gif',
                'webp',
                'pdf'
            ]

            extension = new_file.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only jpg, jpeg, png, gif, webp and pdf files are allowed."
                ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Update fields
        fdp.title = title
        fdp.category = category
        fdp.institute = institute
        fdp.duration = duration
        fdp.level = level

        # Update file
        if new_file:
            if old_file:
                old_file.delete(save=False)

            fdp.certificate_file = new_file

        # Reset approval on edit
        fdp.points = 0
        fdp.approval_status = "pending"
        fdp.approved_by = None
        fdp.message = None

        fdp.save()

        return Response(
            {
                "id": fdp.id,
                "user": fdp.user.id,
                "title": fdp.title,
                "category": fdp.category,
                "institute": fdp.institute,
                "duration": fdp.duration,
                "level": fdp.level,
                "certificate_file": (
                    fdp.certificate_file.url
                    if fdp.certificate_file else None
                ),
                "approval_status": fdp.approval_status,
                "points": fdp.points,
            },
            status=status.HTTP_200_OK
        )

    # POST /fdp/<pk>/approve/
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
            fdp = FDPs_Attended.objects.get(pk=pk)
        except FDPs_Attended.DoesNotExist:
            return Response(
                {"error": "FDP record not found"},
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
        message = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )

        fdp.approval_status = status_value
        fdp.message = message
        fdp.approved_by = user["username"]

        if status_value == "approved":
            fdp.points = calculate_fdp_points(
                category=fdp.category,
                institute=fdp.institute,
                duration=fdp.duration,
                level=fdp.level
            )
            fdp.save()
            serializer = FDPsAttendedSerializer(fdp)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif status_value == "rejected":
            if not message:
                fdp.message = (
                    f"Rejected by {user['username']} "
                    f"({user['register_no']})"
                )
            fdp.save()
            return Response(
                {"message": fdp.message},
                status=status.HTTP_200_OK
            )

    # DELETE /fdp/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_fdp(self, request, pk=None):
        try:
            fdp = FDPs_Attended.objects.get(pk=pk)
            old_file = fdp.certificate_file
        except FDPs_Attended.DoesNotExist:
            return Response(
                {"error": "FDP record not found"},
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

    # GET /fdp/<pk>/file/
    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            fdp = FDPs_Attended.objects.get(pk=pk)
        except FDPs_Attended.DoesNotExist:
            return Response(
                {"error": "FDP record not found"},
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

        key = f"FDPS_certificate/{fdp.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )

    return Response({"certificate_url": url})

    # GET /fdp/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        fdps = FDPs_Attended.objects.filter(approval_status="pending")
        serializer = FDPsAttendedSerializer(fdps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)