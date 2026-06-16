from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import SubjectContribution
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import SubjectContributionSerializer, CreateSubjectContributionSerializer
from accounts.models import User
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .utils import send_subject_contribution_status_email

class SubjectContributionViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action == 'approve_contribution':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /subject/contribution/
    @action(detail=False, url_path='contribution', methods=['post'])
    def create_contribution(self, request):
        serializer = CreateSubjectContributionSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /subject/usercontributions/<register_no>/
    @action(detail=False, url_path='usercontributions/(?P<register_no>[^/.]+)', methods=['get'])
    def user_contribution_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        contributions = user.subject_contributions.all()
        serializer = SubjectContributionSerializer(contributions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /subject/contributions/
    @action(detail=False, url_path='contributions', methods=['get'])
    def contributions_list(self, request):
        contributions = SubjectContribution.objects.all()
        serializer = SubjectContributionSerializer(contributions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /subject/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_contribution(self, request, pk=None):
        try:
            decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            contribution = SubjectContribution.objects.get(pk=pk)
        except SubjectContribution.DoesNotExist:
            return Response({"error": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        subject_name  = request.data.get("subject_name")
        academic_year = request.data.get("academic_year")
        semester      = request.data.get("semester")
        user_id       = request.data.get("user")

        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not subject_name:
            errors["subject_name"] = ["This field is required."]
        elif len(subject_name.strip()) < 3:
            errors["subject_name"] = ["Subject name must contain at least 3 characters."]

        allowed_semesters = ['1-1', '1-2', '2-1', '2-2', '3-1', '3-2', '4-1', '4-2']
        if semester and semester not in allowed_semesters:
            errors["semester"] = [f"Invalid semester. Allowed values are {allowed_semesters}"]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        contribution.user_id       = user_id
        contribution.subject_name  = subject_name
        contribution.academic_year = academic_year
        contribution.semester      = semester

        # Reset approval on edit
        contribution.points          = 3
        contribution.approval_status = "pending"
        contribution.save()

        return Response(
            {
                "id":              contribution.id,
                "user":            contribution.user_id,
                "subject_name":    contribution.subject_name,
                "academic_year":   contribution.academic_year,
                "semester":        contribution.semester,
                "approval_status": contribution.approval_status,
                "points":          contribution.points,
            },
            status=status.HTTP_200_OK,
        )

    # POST /subject/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_contribution(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            contribution = SubjectContribution.objects.get(pk=pk)
        except SubjectContribution.DoesNotExist:
            return Response({"error": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        if contribution.approval_status in ["approved", "rejected"]:
            return Response({"error": "Request already processed"}, status=status.HTTP_400_BAD_REQUEST)

        if contribution.user.register_no == user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        status_value = request.data.get("status")
        message      = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        contribution.approval_status = status_value
        contribution.message         = message
        contribution.approved_by     = user["username"]
        contribution.save()

        if contribution.approval_status == "approved":
            # 3 points per subject as per the points table
            contribution.points = 3
            contribution.save()
            try:
                send_subject_contribution_status_email(
                    email=contribution.user.email,
                    username=contribution.user.username,
                    subject_name=contribution.subject_name,  # replace with your actual field name
                    status=contribution.approval_status,
                    message=contribution.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

        elif contribution.approval_status == "rejected":
            if not contribution.message:
                contribution.message = (
                    f"Rejected by {user['username']} ({user['register_no']})"
                )
            contribution.save()
            try:
                send_subject_contribution_status_email(
                    email=contribution.user.email,
                    username=contribution.user.username,
                    subject_name=contribution.subject_name,  # replace with your actual field name
                    status=contribution.approval_status,
                    message=contribution.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            return Response({"message": contribution.message}, status=status.HTTP_200_OK)

        serializer = SubjectContributionSerializer(contribution)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /subject/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_contribution(self, request, pk=None):
        try:
            contribution = SubjectContribution.objects.get(pk=pk)
        except SubjectContribution.DoesNotExist:
            return Response({"error": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        if contribution.user.register_no != user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        contribution.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

    # GET /subject/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        contributions = SubjectContribution.objects.filter(approval_status="pending")
        serializer = SubjectContributionSerializer(contributions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)