from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import StudentProjectWork
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import StudentProjectWorkSerializer, CreateStudentProjectWorkSerializer
from accounts.models import User

import boto3
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .utils import send_project_status_email

class StudentProjectWorkViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['approve_project', 'pending_list']:
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /studentproject/create/
    @action(detail=False, url_path='create', methods=['post'])
    def create_project(self, request):
        serializer = CreateStudentProjectWorkSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /studentproject/user/<register_no>/
    @action(detail=False, url_path='user/(?P<register_no>[^/.]+)', methods=['get'])
    def user_project_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        projects = user.student_project_works.all()
        serializer = StudentProjectWorkSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /studentproject/all/
    @action(detail=False, url_path='all', methods=['get'])
    def projects_list(self, request):
        projects = StudentProjectWork.objects.all()
        serializer = StudentProjectWorkSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /studentproject/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_project(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            project = StudentProjectWork.objects.get(pk=pk)
            old_file = project.certificate_file
        except StudentProjectWork.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        project_title = request.data.get("project_title")
        project_type = request.data.get("project_type")
        publication_status = request.data.get("publication_status")
        student_names = request.data.get("student_names")
        academic_year = request.data.get("academic_year")
        user_id = request.data.get("user")
        new_file = request.FILES.get("certificate_file")

        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not project_title:
            errors["project_title"] = ["This field is required."]
        elif len(project_title.strip()) < 3:
            errors["project_title"] = ["Project title must contain at least 3 characters."]

        allowed_project_types = ["BTECH", "MTECH"]
        if not project_type:
            errors["project_type"] = ["This field is required."]
        elif project_type not in allowed_project_types:
            errors["project_type"] = [f"Invalid project type. Allowed values are {allowed_project_types}"]

        allowed_pub_statuses = ["WITH_PUBLICATION", "WITHOUT_PUBLICATION"]
        if not publication_status:
            errors["publication_status"] = ["This field is required."]
        elif publication_status not in allowed_pub_statuses:
            errors["publication_status"] = [f"Invalid publication status. Allowed values are {allowed_pub_statuses}"]

        if new_file:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            extension = new_file.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = ["Only image files (jpg, jpeg, png, gif, webp) are allowed."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        project.user_id = user_id
        project.project_title = project_title
        project.project_type = project_type
        project.publication_status = publication_status
        project.student_names = student_names
        project.academic_year = academic_year

        if new_file:
            if old_file:
                old_file.delete(save=False)
            project.certificate_file = new_file

        # Reset approval on any update
        project.points = 0
        project.approval_status = "pending"
        project.save()

        return Response(
            {
                "id": project.id,
                "user": project.user_id,
                "project_title": project.project_title,
                "project_type": project.project_type,
                "publication_status": project.publication_status,
                "student_names": project.student_names,
                "academic_year": project.academic_year,
                "certificate_file": project.certificate_file.url if project.certificate_file else None,
                "approval_status": project.approval_status,
                "points": project.points,
            },
            status=status.HTTP_200_OK
        )

    # POST /studentproject/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_project(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            project = StudentProjectWork.objects.get(pk=pk)
        except StudentProjectWork.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        if project.approval_status in ["approved", "rejected"]:
            return Response({"error": "Request already processed"}, status=status.HTTP_400_BAD_REQUEST)

        if project.user.register_no == user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        status_value = request.data.get("status")
        message = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        project.approval_status = status_value
        project.message = message
        project.approved_by = user["username"]
        project.save()

        if project.approval_status == "approved":
            # Points rubric:
            # BTECH  + WITH_PUBLICATION    = 10
            # BTECH  + WITHOUT_PUBLICATION = 7
            # MTECH  + WITH_PUBLICATION    = 15
            # MTECH  + WITHOUT_PUBLICATION = 10
            points_map = {
                ("BTECH", "WITH_PUBLICATION"): 10,
                ("BTECH", "WITHOUT_PUBLICATION"): 7,
                ("MTECH", "WITH_PUBLICATION"): 15,
                ("MTECH", "WITHOUT_PUBLICATION"): 10,
            }
            project.points = points_map.get((project.project_type, project.publication_status), 0)
            project.save()
            try:
                send_project_status_email(
                    email=project.user.email,
                    username=project.user.username,
                    project_title=project.project_title,
                    project_type=project.project_type,
                    publication_status=project.publication_status,
                    status=project.approval_status,
                    points=project.points,
                    message=project.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")


        elif project.approval_status == "rejected":
            if not project.message:
                project.message = f"Rejected by {user['username']} ({user['register_no']})"
            project.save()
            try:
                send_project_status_email(
                    email=project.user.email,
                    username=project.user.username,
                    project_title=project.project_title,
                    project_type=project.project_type,
                    publication_status=project.publication_status,
                    status=project.approval_status,
                    points=project.points,
                    message=project.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

            return Response({"message": project.message}, status=status.HTTP_200_OK)

        serializer = StudentProjectWorkSerializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /studentproject/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_project(self, request, pk=None):
        try:
            project = StudentProjectWork.objects.get(pk=pk)
            old_file = project.certificate_file
        except StudentProjectWork.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        if project.user.register_no != user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if old_file:
            old_file.delete(save=False)
        project.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

    # GET /studentproject/<pk>/file/
    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            project = StudentProjectWork.objects.get(pk=pk)
        except StudentProjectWork.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        if not project.certificate_file:
            return Response({"error": "No certificate file uploaded"}, status=status.HTTP_404_NOT_FOUND)

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        key = f"student_project_certificate/{project.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )
        return Response({"certificate_url": url})

    # GET /studentproject/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        projects = StudentProjectWork.objects.filter(approval_status="pending")
        serializer = StudentProjectWorkSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)