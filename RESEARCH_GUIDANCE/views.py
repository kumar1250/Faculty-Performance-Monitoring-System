from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import ResearchGuidance
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import ResearchGuidanceSerializer, CreateResearchGuidanceSerializer
from accounts.models import User

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


def calculate_research_points(guide_type, registration_date, awarded_date, status):
    """
    Calculate points based on guide type, duration, and status.

    III.3 RESEARCH GUIDANCE (Ph.D/M.Phil)

    Guide:
        <= 1Y       → 10
        >1Y & <=2Y  → 7.5
        >2Y & <=3Y  → 5
        >3Y         → 2.5
        Awarded     → 10

    Co-Guide:
        <= 1Y       → 5
        >1Y & <=2Y  → 3.5
        >2Y & <=3Y  → 2
        >3Y         → 1
        Awarded     → 8
    """
    if status == "awarded":
        return 10.0 if guide_type == "Guide" else 8.0

    # Calculate duration from registration_date to today
    today = date.today()
    delta = relativedelta(today, registration_date)

    # Convert to total months for precise comparison
    total_months = delta.years * 12 + delta.months

    if guide_type == "Guide":
        if total_months <= 12:       # <= 1 year
            return 10.0
        elif total_months <= 24:     # > 1Y & <= 2Y
            return 7.5
        elif total_months <= 36:     # > 2Y & <= 3Y
            return 5.0
        else:                        # > 3Y
            return 2.5

    elif guide_type == "Co-Guide":
        if total_months <= 12:
            return 5.0
        elif total_months <= 24:
            return 3.5
        elif total_months <= 36:
            return 2.0
        else:
            return 1.0

    return 0.0


class ResearchGuidanceViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ["approve_guidance", "pending_list"]:
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /research/guidance/
    @action(detail=False, url_path="guidance", methods=["post"])
    def create_guidance(self, request):
        serializer = CreateResearchGuidanceSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /research/user-guidance/<register_no>/
    @action(
        detail=False,
        url_path="user-guidance/(?P<register_no>[^/.]+)",
        methods=["get"],
    )
    def user_guidance_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        guidances = user.research_guidance.all()
        serializer = ResearchGuidanceSerializer(guidances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /research/guidances/
    @action(detail=False, url_path="guidances", methods=["get"])
    def guidance_list(self, request):
        guidances = ResearchGuidance.objects.all()
        serializer = ResearchGuidanceSerializer(guidances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /research/<pk>/update/
    @action(detail=True, url_path="update", methods=["put"])
    def update_guidance(self, request, pk=None):
        try:
            decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            guidance = ResearchGuidance.objects.get(pk=pk)
        except ResearchGuidance.DoesNotExist:
            return Response(
                {"error": "Research guidance record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Collect fields
        scholar_name = request.data.get("scholar_name")
        guide_type = request.data.get("guide_type")
        registration_date = request.data.get("registration_date")
        awarded_date = request.data.get("awarded_date")
        status_value = request.data.get("status")
        user_id = request.data.get("user")

        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not scholar_name:
            errors["scholar_name"] = ["This field is required."]
        elif len(scholar_name.strip()) < 3:
            errors["scholar_name"] = [
                "Scholar name must contain at least 3 characters."
            ]

        allowed_guide_types = ["Guide", "Co-Guide"]
        if not guide_type:
            errors["guide_type"] = ["This field is required."]
        elif guide_type not in allowed_guide_types:
            errors["guide_type"] = [
                f"Invalid guide type. Allowed values are {allowed_guide_types}"
            ]

        if not registration_date:
            errors["registration_date"] = ["This field is required."]
        else:
            try:
                from datetime import datetime
                registration_date = datetime.strptime(
                    registration_date, "%Y-%m-%d"
                ).date()
            except ValueError:
                errors["registration_date"] = [
                    "Invalid date format. Use YYYY-MM-DD."
                ]

        allowed_statuses = ["ongoing", "awarded"]
        if not status_value:
            errors["status"] = ["This field is required."]
        elif status_value not in allowed_statuses:
            errors["status"] = [
                f"Invalid status. Allowed values are {allowed_statuses}"
            ]

        if status_value == "awarded":
            if not awarded_date:
                errors["awarded_date"] = [
                    "Awarded date is required when status is 'awarded'."
                ]
            else:
                try:
                    from datetime import datetime
                    awarded_date = datetime.strptime(awarded_date, "%Y-%m-%d").date()
                except ValueError:
                    errors["awarded_date"] = [
                        "Invalid date format. Use YYYY-MM-DD."
                    ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Apply updates
        guidance.user_id = user_id
        guidance.scholar_name = scholar_name
        guidance.guide_type = guide_type
        guidance.registration_date = registration_date
        guidance.awarded_date = awarded_date if status_value == "awarded" else None
        guidance.status = status_value

        # Reset approval on edit
        guidance.points = 0
        guidance.approval_status = "pending"
        guidance.approved_by = None
        guidance.message = None

        guidance.save()

        serializer = ResearchGuidanceSerializer(guidance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # POST /research/<pk>/approve/
    @action(detail=True, url_path="approve", methods=["post"])
    def approve_guidance(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            guidance = ResearchGuidance.objects.get(pk=pk)
        except ResearchGuidance.DoesNotExist:
            return Response(
                {"error": "Research guidance record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if guidance.approval_status in ["approved", "rejected"]:
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # HOD cannot approve their own submission
        if guidance.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        status_value = request.data.get("status")
        message = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response(
                {"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
            )

        guidance.approval_status = status_value
        guidance.message = message
        guidance.approved_by = user["username"]

        if status_value == "approved":
            guidance.points = calculate_research_points(
                guide_type=guidance.guide_type,
                registration_date=guidance.registration_date,
                awarded_date=guidance.awarded_date,
                status=guidance.status,
            )

        elif status_value == "rejected":
            guidance.points = 0
            if not guidance.message:
                guidance.message = (
                    f"Rejected by {user['username']} ({user['register_no']})"
                )
            guidance.save()
            return Response(
                {"message": guidance.message}, status=status.HTTP_200_OK
            )

        guidance.save()
        serializer = ResearchGuidanceSerializer(guidance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /research/<pk>/delete/
    @action(detail=True, url_path="delete", methods=["delete"])
    def delete_guidance(self, request, pk=None):
        try:
            guidance = ResearchGuidance.objects.get(pk=pk)
        except ResearchGuidance.DoesNotExist:
            return Response(
                {"error": "Research guidance record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Prevent self-deletion (same guard as CourseDone)
        if guidance.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )

        guidance.delete()
        return Response(
            {"message": "Deleted successfully"}, status=status.HTTP_200_OK
        )

    # GET /research/requests/
    @action(detail=False, url_path="requests", methods=["get"])
    def pending_list(self, request):
        guidances = ResearchGuidance.objects.filter(approval_status="pending")
        serializer = ResearchGuidanceSerializer(guidances, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)