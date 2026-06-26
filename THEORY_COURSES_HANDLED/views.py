from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import StudentFeedbackPerformance
from .serializers import StudentFeedbackPerformanceSerializer
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD ,IsDean,IsPrincipal
from accounts.models import User

from .utils import send_student_feedback_email
# ------------------------------------------------------------------ #
# POINTS TABLE
# ------------------------------------------------------------------ #
def compute_points(cycle_1, cycle_2, exam_result):
    """
    Points lookup based on the rubric table.

    cycle_1 / cycle_2 : 'excellent' | 'good' | 'satisfactory'
    exam_result        : 'ge_90' | 'ge_80' | 'ge_70' | 'lt_70'
    """
    table = {
        # Excellent / Excellent
        ("excellent", "excellent", "ge_90"): 10,
        ("excellent", "excellent", "ge_80"):  9,
        ("excellent", "excellent", "ge_70"):  8,
        ("excellent", "excellent", "lt_70"):  7,

        # Excellent / Good
        ("excellent", "good", "ge_90"): 9.5,
        ("excellent", "good", "ge_80"): 8.5,
        ("excellent", "good", "ge_70"): 7.5,
        ("excellent", "good", "lt_70"): 6.5,

        # Excellent / Satisfactory
        ("excellent", "satisfactory", "ge_90"): 9,
        ("excellent", "satisfactory", "ge_80"): 8,
        ("excellent", "satisfactory", "ge_70"): 7,
        ("excellent", "satisfactory", "lt_70"): 6,

        # Good / Excellent
        ("good", "excellent", "ge_90"): 9.5,
        ("good", "excellent", "ge_80"): 8.5,
        ("good", "excellent", "ge_70"): 7.5,
        ("good", "excellent", "lt_70"): 6.5,

        # Good / Good
        ("good", "good", "ge_90"): 9,
        ("good", "good", "ge_80"): 8,
        ("good", "good", "ge_70"): 7,
        ("good", "good", "lt_70"): 6,

        # Good / Satisfactory
        ("good", "satisfactory", "ge_90"): 8.5,
        ("good", "satisfactory", "ge_80"): 7.5,
        ("good", "satisfactory", "ge_70"): 6.5,
        ("good", "satisfactory", "lt_70"): 5.5,

        # Satisfactory / Excellent
        ("satisfactory", "excellent", "ge_90"): 9,
        ("satisfactory", "excellent", "ge_80"): 8,
        ("satisfactory", "excellent", "ge_70"): 7,
        ("satisfactory", "excellent", "lt_70"): 6,

        # Satisfactory / Good
        ("satisfactory", "good", "ge_90"): 8.5,
        ("satisfactory", "good", "ge_80"): 7.5,
        ("satisfactory", "good", "ge_70"): 6.5,
        ("satisfactory", "good", "lt_70"): 5.5,

        # Satisfactory / Satisfactory
        ("satisfactory", "satisfactory", "ge_90"): 8,
        ("satisfactory", "satisfactory", "ge_80"): 7,
        ("satisfactory", "satisfactory", "ge_70"): 6,
        ("satisfactory", "satisfactory", "lt_70"): 5,
    }
    return table.get((cycle_1, cycle_2, exam_result), 0)


class StudentFeedbackPerformanceViewSet(ViewSet):

    def get_permissions(self):
        if self.action in ("approve_feedback", "pending_list"):
            permission_classes = [IsHOD | IsDean | IsPrincipal]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # ------------------------------------------------------------------ #
    # CREATE  POST /student-feedback/create/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="create", methods=["post"])
    def create_feedback(self, request):
        try:
            token_data = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            requesting_user = User.objects.get(register_no=token_data["register_no"])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # HOD/Dean/Principal can pass a target user PK → assign record to that user
        target_user_id = request.data.get("user")
        PRIVILEGED_ROLES = ('hod', 'dean', 'principal', 'department_incharge')

        if target_user_id and requesting_user.role in PRIVILEGED_ROLES:
            try:
                target_user = User.objects.get(pk=target_user_id)
            except User.DoesNotExist:
                return Response({"error": "Target user not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Faculty creates for themselves
            target_user = requesting_user

        serializer = StudentFeedbackPerformanceSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cycle_1     = serializer.validated_data.get("cycle_1_feedback")
        cycle_2     = serializer.validated_data.get("cycle_2_feedback")
        exam_result = serializer.validated_data.get("exam_result")
        points      = compute_points(cycle_1, cycle_2, exam_result)

        # Save record assigned to the resolved target user
        serializer.save(user=target_user, created_by=requesting_user, points=points)

        try:
            send_student_feedback_email(
                email=target_user.email,
                username=target_user.username,
                subject_name=serializer.validated_data.get("subject_name"),
                academic_year=serializer.validated_data.get("academic_year"),
                cycle_1_feedback=cycle_1,
                cycle_2_feedback=cycle_2,
                exam_result=exam_result,
                points=points,
                message=serializer.validated_data.get("message"),
            )
        except Exception as e:
            print(f"Email sending failed: {e}")

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    # ------------------------------------------------------------------ #
    # LIST ALL  GET /student-feedback/list/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="list", methods=["get"])
    def feedback_list(self, request):
        feedbacks = StudentFeedbackPerformance.objects.all()
        serializer = StudentFeedbackPerformanceSerializer(
            feedbacks, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # MY UPLOADS  GET /student-feedback/my-uploads/
    # Records the logged-in HOD personally entered, across every faculty
    # member — used to scope edit/delete to entries they actually own.
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="my-uploads", methods=["get"])
    def my_uploads(self, request):
        try:
            token_data = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            requesting_user = User.objects.get(register_no=token_data["register_no"])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        feedbacks = StudentFeedbackPerformance.objects.filter(created_by=requesting_user)
        serializer = StudentFeedbackPerformanceSerializer(
            feedbacks, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # LIST BY USER  GET /student-feedback/user/<register_no>/
    # ------------------------------------------------------------------ #
    @action(
        detail=False,
        url_path=r"user/(?P<register_no>[^/.]+)",
        methods=["get"],
    )
    def user_feedbacks(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        feedbacks = user.student_feedback_performances.all()
        serializer = StudentFeedbackPerformanceSerializer(
            feedbacks, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # UPDATE  PUT /student-feedback/<pk>/update/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="update", methods=["put"])
    def update_feedback(self, request, pk=None):
        try:
            token_data = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            feedback = StudentFeedbackPerformance.objects.get(pk=pk)
        except StudentFeedbackPerformance.DoesNotExist:
            return Response(
                {"error": "Record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Permission check happens below once we know who created the record
        try:
            requesting_user = User.objects.get(register_no=token_data["register_no"])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Self-entry: faculty editing their own record is always allowed.
        # Otherwise, only the person who actually created this entry
        # (e.g. the HOD who logged it) can edit it — not every HOD.
        is_owner   = feedback.user and feedback.user.register_no == token_data["register_no"]
        is_creator = feedback.created_by_id == requesting_user.id

        if not (is_owner or is_creator):
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )
        academic_year    = request.data.get("academic_year")
        subject_name     = request.data.get("subject_name")
        cycle_1_feedback = request.data.get("cycle_1_feedback")
        cycle_2_feedback = request.data.get("cycle_2_feedback")
        exam_result      = request.data.get("exam_result")
        message          = request.data.get("message", "")

        # ---- Validation -----------------------------------------------
        errors = {}

        if not academic_year:
            errors["academic_year"] = ["This field is required."]

        if not subject_name:
            errors["subject_name"] = ["This field is required."]

        allowed_feedback = ["excellent", "good", "satisfactory"]

        if not cycle_1_feedback:
            errors["cycle_1_feedback"] = ["This field is required."]
        elif cycle_1_feedback not in allowed_feedback:
            errors["cycle_1_feedback"] = [
                f"Invalid value. Allowed: {allowed_feedback}"
            ]

        if not cycle_2_feedback:
            errors["cycle_2_feedback"] = ["This field is required."]
        elif cycle_2_feedback not in allowed_feedback:
            errors["cycle_2_feedback"] = [
                f"Invalid value. Allowed: {allowed_feedback}"
            ]

        allowed_results = ["ge_90", "ge_80", "ge_70", "lt_70"]

        if not exam_result:
            errors["exam_result"] = ["This field is required."]
        elif exam_result not in allowed_results:
            errors["exam_result"] = [
                f"Invalid value. Allowed: {allowed_results}"
            ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ---- Apply updates --------------------------------------------
        feedback.academic_year    = academic_year
        feedback.subject_name     = subject_name
        feedback.cycle_1_feedback = cycle_1_feedback
        feedback.cycle_2_feedback = cycle_2_feedback
        feedback.exam_result      = exam_result
        feedback.message          = message
        feedback.points           = compute_points(
            cycle_1_feedback, cycle_2_feedback, exam_result
        )
        feedback.save()

        serializer = StudentFeedbackPerformanceSerializer(
            feedback, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # DELETE  DELETE /student-feedback/<pk>/delete/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="delete", methods=["delete"])
    def delete_feedback(self, request, pk=None):
        try:
            token_data = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            feedback = StudentFeedbackPerformance.objects.get(pk=pk)
        except StudentFeedbackPerformance.DoesNotExist:
            return Response(
                {"error": "Record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Permission check happens below once we know who created the record
        try:
            requesting_user = User.objects.get(register_no=token_data["register_no"])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Self-entry: faculty deleting their own record is always allowed.
        # Otherwise, only the person who actually created this entry
        # (e.g. the HOD who logged it) can delete it — not every HOD.
        is_owner   = feedback.user and feedback.user.register_no == token_data["register_no"]
        is_creator = feedback.created_by_id == requesting_user.id

        if not (is_owner or is_creator):
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        feedback.delete()
        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK,
        )