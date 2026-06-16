from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import StudentCounselling
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import StudentCounsellingSerializer, CreateStudentCounsellingSerializer
from accounts.models import User
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .utils import send_counselling_status_email

class StudentCounsellingViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action == 'approve_contribution':
            permission_classes = [IsHOD]
        elif self.action == 'pending_list':
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /counselling/contribution/
    @action(detail=False, url_path='contribution', methods=['post'])
    def create_contribution(self, request):
        serializer = CreateStudentCounsellingSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(faculty=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /counselling/usercontributions/<register_no>/
    @action(detail=False, url_path='usercontributions/(?P<register_no>[^/.]+)', methods=['get'])
    def user_contribution_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        contributions = user.student_counselling.all()
        serializer = StudentCounsellingSerializer(contributions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /counselling/contributions/
    @action(detail=False, url_path='contributions', methods=['get'])
    def contributions_list(self, request):
        contributions = StudentCounselling.objects.all()
        serializer = StudentCounsellingSerializer(contributions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /counselling/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_contribution(self, request, pk=None):
        try:
            decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            contribution = StudentCounselling.objects.get(pk=pk)
        except StudentCounselling.DoesNotExist:
            return Response({"error": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        faculty_id     = request.data.get("faculty")
        total_students = request.data.get("total_students")

        errors = {}

        if not faculty_id:
            errors["faculty"] = ["This field is required."]

        if not total_students:
            errors["total_students"] = ["This field is required."]
        else:
            try:
                total_students = int(total_students)
                if total_students <= 0:
                    errors["total_students"] = ["Total students must be a positive integer."]
            except (ValueError, TypeError):
                errors["total_students"] = ["Total students must be a valid integer."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        contribution.faculty_id     = faculty_id
        contribution.total_students = total_students

        # Reset approval on edit
        contribution.points          = 0
        contribution.approval_status = "pending"
        contribution.save()

        return Response(
            {
                "id":              contribution.id,
                "faculty":         contribution.faculty_id,
                "total_students":  contribution.total_students,
                "approval_status": contribution.approval_status,
                "points":          contribution.points,
            },
            status=status.HTTP_200_OK,
        )

    # POST /counselling/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_contribution(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            contribution = StudentCounselling.objects.get(pk=pk)
        except StudentCounselling.DoesNotExist:
            return Response({"error": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        if contribution.approval_status in ["approved", "rejected"]:
            return Response({"error": "Request already processed"}, status=status.HTTP_400_BAD_REQUEST)

        if contribution.faculty.register_no == user["register_no"]:
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
            # Points based on total students counselled (e.g., 0.1 point per student)
            contribution.points = round(contribution.total_students * 2.5, 2)
            contribution.save()
            try:
                send_counselling_status_email(
                    email=contribution.faculty.email,
                    username=contribution.faculty.username,
                    total_students=contribution.total_students,
                    status=contribution.approval_status.title(),
                    points=contribution.points,
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
                send_counselling_status_email(
                    email=contribution.faculty.email,
                    username=contribution.faculty.username,
                    total_students=contribution.total_students,
                    status=contribution.approval_status.title(),
                    points=contribution.points,
                    message=contribution.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            return Response({"message": contribution.message}, status=status.HTTP_200_OK)

        serializer = StudentCounsellingSerializer(contribution)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /counselling/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_contribution(self, request, pk=None):
        try:
            contribution = StudentCounselling.objects.get(pk=pk)
        except StudentCounselling.DoesNotExist:
            return Response({"error": "Contribution not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        if contribution.faculty.register_no != user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        contribution.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

    # GET /counselling/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        contributions = StudentCounselling.objects.filter(approval_status="pending")
        serializer = StudentCounsellingSerializer(contributions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)