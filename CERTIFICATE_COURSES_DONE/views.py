from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Course
from accounts.token_jwt import decode_token,get_token_from_request
from accounts.permissions import IsAuthenticated,IsHOD,IsPrincipal,IsDean,IsFaculty,IsCommittee_Coordinator,IsDepartment_Incharge
from .serializers import CourseSerializer,CreateCourseSerializer

from accounts.models import User

import boto3
from django.conf import settings

from rest_framework.parsers import MultiPartParser, FormParser , JSONParser
from .utils import send_course_status_email

class CourseDone(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    def get_permissions(self):
        if self.action == 'approvecourse':
            permission_classes = [IsHOD]
        elif self.action == "pending_list":
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False,url_path='course',methods=['post'])
    def create_course(self,request):
        course_serializer=CreateCourseSerializer(data=request.data)
        if course_serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            course_serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(
                course_serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            course_serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


    @action(detail=False, url_path='usercourses/(?P<register_no>[^/.]+)', methods=['get'])
    def user_course_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        courses = user.coursedone.all()

        serializer = CourseSerializer(courses, many=True)

        return Response(serializer.data,status=status.HTTP_200_OK)
    
    @action(detail=False,url_path='courses',methods=['get'])
    def courses_list(self,request):
        course = Course.objects.all()
        serializer = CourseSerializer(course,many=True)
        return Response( serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, url_path='update', methods=['put'])
    def update_course(self, request, pk=None):

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            course = Course.objects.get(pk=pk)
            old_file = course.certificate_file
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get data
        course_name = request.data.get("Course_name")
        certificate_type = request.data.get("certificate_type")
        user_id = request.data.get("user")
        new_file = request.FILES.get("certificate_file")

        # Validation
        errors = {}

        # User validation
        if not user_id:
            errors["user"] = ["This field is required."]

        # Course name validation
        if not course_name:
            errors["Course_name"] = ["This field is required."]
        elif len(course_name.strip()) < 3:
            errors["Course_name"] = [
                "Course name must contain at least 3 characters."
            ]

        # Certificate type validation
        allowed_types = ["NPTEL", "OTHER"]

        if not certificate_type:
            errors["certificate_type"] = ["This field is required."]
        elif certificate_type not in allowed_types:
            errors["certificate_type"] = [
                f"Invalid certificate type. Allowed values are {allowed_types}"
            ]

        # File validation
        if new_file:

            allowed_extensions = [
                'jpg',
                'jpeg',
                'png',
                'gif',
                'webp'
            ]

            extension = new_file.name.split('.')[-1].lower()

            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only image files (jpg, jpeg, png, gif, webp) are allowed."
                ]

        # Return errors if any
        if errors:
            return Response(
                errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update fields
        course.user_id = user_id
        course.Course_name = course_name
        course.certificate_type = certificate_type

        # Update file if provided
        if new_file:

            # Delete old file from S3
            if old_file:
                old_file.delete(save=False)

            # Save new file
            course.certificate_file = new_file

        # Reset approval
        course.points = 0
        course.approval_status = "pending"

        # Save
        course.save()

        return Response(
            {
                "id": course.id,
                "user": course.user_id,
                "certificate_type": course.certificate_type,
                "Course_name": course.Course_name,
                "certificate_file": (
                    course.certificate_file.url
                    if course.certificate_file
                    else None
                ),
                "approval_status": course.approval_status,
                "points": course.points
            },
            status=status.HTTP_200_OK
        )
    @action(detail=True,url_path='approve',methods=['post'],)
    def approvecourse(self,request,pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
            {"error": "User not logged in"},
            status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"},status=status.HTTP_404_NOT_FOUND)
        if course.approval_status in ["approved", "rejected"]:
            return Response(
            {"error": "Request already processed"},
            status=status.HTTP_400_BAD_REQUEST
            )
        if course.user.register_no == user["register_no"]:
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
        course.approval_status = status_value
        course.message = message
        course.approved_by = user["username"]
        course.save()
        if course.approval_status == "approved":
            if course.certificate_type == "NPTEL":
                course.points = 10
            elif course.certificate_type == "OTHER":
                course.points = 6
            course.save()
        elif course.approval_status == "rejected":
            if not course.message:
                course.message = (
                    f"Rejected by {user['username']} "
                    f"({user['register_no']})"
                )

            course.save()
            try:
                send_course_status_email(
                    email=course.user.email,
                    username=course.user.username,
                    course_name=course.Course_name,
                    status=course.approval_status,
                    message=course.message
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

            return Response(
                {"message": course.message},
                status=status.HTTP_200_OK
            )
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True,url_path='delete',methods=['delete'])
    def delete_course(self,request,pk=None):
        try:
            course = Course.objects.get(pk=pk)
            old_file=course.certificate_file
        except Course.DoesNotExist:
            return Response({"error": "Course not found"},status=status.HTTP_404_NOT_FOUND)
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
            {"error": "User not logged in"},
            status=status.HTTP_401_UNAUTHORIZED
            )
        if course.user.register_no!=user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        if old_file:
            old_file.delete(save=False)
        course.delete()
        return Response(
            {"message": "Deleted successfully"},status=status.HTTP_200_OK)

    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):

        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not course.certificate_file:
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

        key = f"certificates/{course.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )
        return Response({
            "certificate_url": url
        })
    @action(detail=False,url_path='requests',methods=['get'])
    def pending_list(self,request):
        course = Course.objects.filter(approval_status="pending")
        serializer= CourseSerializer(course,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
