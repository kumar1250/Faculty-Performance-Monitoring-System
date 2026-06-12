from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import ChairingSession
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import ChairingSessionSerializer,CreateChairingSessionSerializer
from accounts.models import User

from rest_framework.parsers import MultiPartParser, FormParser , JSONParser


# Points table:
#   CHAIRING_SESSION  → INTERNATIONAL=10, NATIONAL=8
#   INVITED_TALK /
#   GUEST_LECTURE  /
#   KEYNOTE_SPEECH  → INTERNATIONAL=9, IIT_NIT=7, UNIVERSITY=5, COLLEGE=4
POINTS_TABLE = {
    "CHAIRING_SESSION": {
        "INTERNATIONAL": 10,
        "NATIONAL":      8,
    },
    "INVITED_TALK": {
        "INTERNATIONAL": 9,
        "IIT_NIT":       7,
        "UNIVERSITY":    5,
        "COLLEGE":       4,
    },
    "GUEST_LECTURE": {
        "INTERNATIONAL": 9,
        "IIT_NIT":       7,
        "UNIVERSITY":    5,
        "COLLEGE":       4,
    },
    "KEYNOTE_SPEECH": {
        "INTERNATIONAL": 9,
        "IIT_NIT":       7,
        "UNIVERSITY":    5,
        "COLLEGE":       4,
    },
}

class ChairingSessionViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser,JSONParser]

    def get_permissions(self):
        if self.action in ("approve_session", "pending_list"):
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # ------------------------------------------------------------------ #
    #  CREATE  –  POST /chairing/session/                                  #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="session", methods=["post"])
    def create_session(self, request):
        serializer = CreateChairingSessionSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ #
    #  LIST BY USER  –  GET /chairing/usersessions/<register_no>/          #
    # ------------------------------------------------------------------ #
    @action(
        detail=False,
        url_path=r"usersessions/(?P<register_no>[^/.]+)",
        methods=["get"],
    )
    def user_session_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        sessions = user.chairing_sessions.all()
        serializer = ChairingSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  LIST ALL  –  GET /chairing/sessions/                               #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="sessions", methods=["get"])
    def sessions_list(self, request):
        sessions = ChairingSession.objects.all()
        serializer = ChairingSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  UPDATE  –  PUT /chairing/<pk>/update/                              #
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="update", methods=["put"])
    def update_session(self, request, pk=None):
        try:
            decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            session = ChairingSession.objects.get(pk=pk)
            old_file = session.certificate_file
        except ChairingSession.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Collect incoming data
        event_name    = request.data.get("event_name")
        event_type    = request.data.get("event_type")
        event_level   = request.data.get("event_level")
        organization  = request.data.get("organization")
        event_date    = request.data.get("event_date")
        user_id       = request.data.get("user")
        new_file      = request.FILES.get("certificate_file")

        # ---- Validation ------------------------------------------------
        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not event_name:
            errors["event_name"] = ["This field is required."]
        elif len(event_name.strip()) < 3:
            errors["event_name"] = ["Event name must be at least 3 characters."]

        allowed_event_types = [choice[0] for choice in ChairingSession.EVENT_TYPE_CHOICES]
        if not event_type:
            errors["event_type"] = ["This field is required."]
        elif event_type not in allowed_event_types:
            errors["event_type"] = [
                f"Invalid event type. Allowed values are {allowed_event_types}."
            ]

        allowed_event_levels = [choice[0] for choice in ChairingSession.EVENT_LEVEL_CHOICES]
        if not event_level:
            errors["event_level"] = ["This field is required."]
        elif event_level not in allowed_event_levels:
            errors["event_level"] = [
                f"Invalid event level. Allowed values are {allowed_event_levels}."
            ]

        # Warn if CHAIRING_SESSION is submitted with UNIVERSITY / COLLEGE level
        # (not defined in the rubric → 0 points).
        if (
            event_type == "CHAIRING_SESSION"
            and event_level in ("UNIVERSITY", "COLLEGE", "IIT_NIT")
            and "event_level" not in errors
            and "event_type" not in errors
        ):
            errors["event_level"] = [
                "Chairing/Co-chairing sessions are only defined for "
                "International and National levels in the points rubric."
            ]

        if not organization:
            errors["organization"] = ["This field is required."]

        if not event_date:
            errors["event_date"] = ["This field is required."]

        if new_file:
            allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
            extension = new_file.name.split(".")[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only image files (jpg, jpeg, png, gif, webp) are allowed."
                ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ---- Apply updates --------------------------------------------
        session.user_id      = user_id
        session.event_name   = event_name
        session.event_type   = event_type
        session.event_level  = event_level
        session.organization = organization
        session.event_date   = event_date

        if new_file:
            if old_file:
                old_file.delete(save=False)
            session.certificate_file = new_file

        # Reset approval when the record is edited
        session.points          = 0
        session.approval_status = "pending"
        session.approved_by     = None
        session.message         = None
        session.save()

        return Response(
            {
                "id":              session.id,
                "user":            session.user_id,
                "event_name":      session.event_name,
                "event_type":      session.event_type,
                "event_level":     session.event_level,
                "organization":    session.organization,
                "event_date":      str(session.event_date),
                "certificate_file": (
                    session.certificate_file.url if session.certificate_file else None
                ),
                "approval_status": session.approval_status,
                "points":          session.points,
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    #  APPROVE / REJECT  –  POST /chairing/<pk>/approve/                  #
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="approve", methods=["post"])
    def approve_session(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            session = ChairingSession.objects.get(pk=pk)
        except ChairingSession.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if session.approval_status in ("approved", "rejected"):
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Faculty cannot approve their own submissions
        if session.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        status_value = request.data.get("status")
        message      = request.data.get("message")

        if status_value not in ("approved", "rejected"):
            return Response(
                {"error": "Invalid status. Must be 'approved' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.approval_status = status_value
        session.message         = message
        session.approved_by     = user["username"]

        if status_value == "approved":

    # Chairing or Co-Chairing Sessions
            if session.event_type == "CHAIRING_SESSION":
                if session.event_level == "INTERNATIONAL":
                    session.points = 10
                elif session.event_level == "NATIONAL":
                    session.points = 8
                else:
                    session.points = 0

            # Delivering Talks & Lectures
            elif session.event_type in ["INVITED_TALK", "GUEST_LECTURE", "KEYNOTE_SPEECH"]:

                if session.event_level == "INTERNATIONAL":
                    session.points = 9

                elif session.event_level == "IIT_NIT":
                    session.points = 7

                elif session.event_level == "UNIVERSITY":
                    session.points = 5

                elif session.event_level == "COLLEGE":
                    session.points = 4

                else:
                    session.points = 0

            else:
                session.points = 0

            session.save()

            serializer = ChairingSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Rejected path
        if not session.message:
            session.message = (
                f"Rejected by {user['username']} ({user['register_no']})"
            )
        session.save()
        return Response({"message": session.message}, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  DELETE  –  DELETE /chairing/<pk>/delete/                           #
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="delete", methods=["delete"])
    def delete_session(self, request, pk=None):
        try:
            session  = ChairingSession.objects.get(pk=pk)
            old_file = session.certificate_file
        except ChairingSession.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if session.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if old_file:
            old_file.delete(save=False)
        session.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    #  PRESIGNED FILE URL  –  GET /chairing/<pk>/file/                    #
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="file", methods=["get"])
    def certificate_url(self, request, pk=None):
        try:
            session = ChairingSession.objects.get(pk=pk)
        except ChairingSession.DoesNotExist:
            return Response(
                {"error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not session.certificate_file:
            return Response(
                {"error": "No certificate file uploaded"},
                status=status.HTTP_404_NOT_FOUND,
            )

        import boto3
        from django.conf import settings

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        key = f"sessions/{session.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key":    key,
            },
            ExpiresIn=3600,
        )

        return Response({"certificate_url": url})

    # ------------------------------------------------------------------ #
    #  PENDING LIST  –  GET /chairing/requests/                           #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="requests", methods=["get"])
    def pending_list(self, request):
        sessions = ChairingSession.objects.filter(approval_status="pending")
        serializer = ChairingSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
