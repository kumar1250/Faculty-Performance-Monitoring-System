from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import FundedProject
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD ,IsDean,IsPrincipal
from .serializers import FundedProjectSerializer, CreateFundedProjectSerializer
from accounts.models import User

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .utils import send_project_status_email
def compute_points(grant_category, investigator_role):
    """
    Points table:

    More than 10 lakhs  ->  PI: 10  |  Co-PI: 9
    5 to 10 lakhs       ->  PI: 9   |  Co-PI: 8
    Less than 5 lakhs   ->  PI: 8   |  Co-PI: 7
    """
    table = {
        ("gt_10", "pi"):    10,
        ("gt_10", "co_pi"):  9,
        ("5_10",  "pi"):     9,
        ("5_10",  "co_pi"):  8,
        ("lt_5",  "pi"):     8,
        ("lt_5",  "co_pi"):  7,
    }
    return table.get((grant_category, investigator_role), 0)


class FundedProjectViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ("approve_project", "pending_list"):
            permission_classes = [IsHOD | IsDean | IsPrincipal]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # ------------------------------------------------------------------ #
    # CREATE  POST /funded-projects/create/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="create", methods=["post"])
    def create_project(self, request):
        serializer = CreateFundedProjectSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ #
    # LIST ALL  GET /funded-projects/list/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="list", methods=["get"])
    def projects_list(self, request):
        projects = FundedProject.objects.all()
        serializer = FundedProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # LIST BY USER  GET /funded-projects/user/<register_no>/
    # ------------------------------------------------------------------ #
    @action(
        detail=False,
        url_path=r"user/(?P<register_no>[^/.]+)",
        methods=["get"],
    )
    def user_projects(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        projects = user.funded_projects.all()
        serializer = FundedProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # UPDATE  PUT /funded-projects/<pk>/update/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="update", methods=["put"])
    def update_project(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            project = FundedProject.objects.get(pk=pk)
        except FundedProject.DoesNotExist:
            return Response(
                {"error": "Funded project not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Collect fields
        project_title      = request.data.get("project_title")
        funding_agency     = request.data.get("funding_agency")
        grant_amount       = request.data.get("grant_amount")
        grant_category     = request.data.get("grant_category")
        investigator_role  = request.data.get("investigator_role")
        sanction_date      = request.data.get("sanction_date")
        completion_date    = request.data.get("completion_date")
        user_id            = request.data.get("user")

        # ---- Validation ------------------------------------------------
        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not project_title:
            errors["project_title"] = ["This field is required."]
        elif len(project_title.strip()) < 3:
            errors["project_title"] = ["Project title must be at least 3 characters."]

        if not funding_agency:
            errors["funding_agency"] = ["This field is required."]

        if not grant_amount:
            errors["grant_amount"] = ["This field is required."]

        allowed_grant_categories = ["gt_10", "5_10", "lt_5"]
        if not grant_category:
            errors["grant_category"] = ["This field is required."]
        elif grant_category not in allowed_grant_categories:
            errors["grant_category"] = [
                f"Invalid grant category. Allowed: {allowed_grant_categories}"
            ]

        allowed_roles = ["pi", "co_pi"]
        if not investigator_role:
            errors["investigator_role"] = ["This field is required."]
        elif investigator_role not in allowed_roles:
            errors["investigator_role"] = [
                f"Invalid investigator role. Allowed: {allowed_roles}"
            ]

        if not sanction_date:
            errors["sanction_date"] = ["This field is required."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ---- Apply updates ---------------------------------------------
        project.user_id           = user_id
        project.project_title     = project_title
        project.funding_agency    = funding_agency
        project.grant_amount      = grant_amount
        project.grant_category    = grant_category
        project.investigator_role = investigator_role
        project.sanction_date     = sanction_date
        project.completion_date   = completion_date

        # Reset approval on update
        project.points          = 0
        project.approval_status = "pending"
        project.save()

        return Response(
            {
                "id":                project.id,
                "user":              project.user_id,
                "project_title":     project.project_title,
                "funding_agency":    project.funding_agency,
                "grant_amount":      str(project.grant_amount),
                "grant_category":    project.grant_category,
                "investigator_role": project.investigator_role,
                "sanction_date":     str(project.sanction_date),
                "completion_date":   str(project.completion_date) if project.completion_date else None,
                "approval_status":   project.approval_status,
                "points":            project.points,
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # APPROVE / REJECT  POST /funded-projects/<pk>/approve/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="approve", methods=["post"])
    def approve_project(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            project = FundedProject.objects.get(pk=pk)
        except FundedProject.DoesNotExist:
            return Response(
                {"error": "Funded project not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if project.approval_status in ("approved", "rejected"):
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # HOD cannot approve their own submission
        if project.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        status_value = request.data.get("status")
        # Frontend sends { status, message } for every module's approve
        # action — this one previously read "remarks" instead of "message",
        # so rejection/approval notes from the Approval Inbox were silently
        # dropped for Funded Projects only.
        remarks      = request.data.get("message")

        if status_value not in ("approved", "rejected"):
            return Response(
                {"error": "Invalid status. Use 'approved' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project.approval_status = status_value
        project.remarks         = remarks
        project.approved_by     = user["username"]

        if status_value == "approved":
            project.points = compute_points(
                project.grant_category,
                project.investigator_role,
            )
            project.save()
            try:
                send_project_status_email(
                email=project.user.email,
                username=project.user.username,
                project_title=project.project_title,  # replace with your actual field name
                status=project.approval_status,
                remarks=project.remarks,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            serializer = FundedProjectSerializer(project)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Rejected
        if not project.remarks:
            project.remarks = (
                f"Rejected by {user['username']} ({user['register_no']})"
            )
        project.save()
        try:
            send_project_status_email(
                email=project.user.email,
                username=project.user.username,
                project_title=project.project_title,  # replace with your actual field name
                status=project.approval_status,
                remarks=project.remarks,
                )
        except Exception as e:
            print(f"Email sending failed: {e}")
        return Response(
            {"message": project.remarks},
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # DELETE  DELETE /funded-projects/<pk>/delete/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="delete", methods=["delete"])
    def delete_project(self, request, pk=None):
        try:
            project = FundedProject.objects.get(pk=pk)
        except FundedProject.DoesNotExist:
            return Response(
                {"error": "Funded project not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if project.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        project.delete()
        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # PENDING LIST (HOD only)  GET /funded-projects/requests/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="requests", methods=["get"])
    def pending_list(self, request):
        projects = FundedProject.objects.filter(approval_status="pending")
        serializer = FundedProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)