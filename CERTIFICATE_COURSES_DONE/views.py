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

class CourseDone(ViewSet):
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
    
    @action(detail=True,url_path='update',methods=['put'])
    def update_course(self,request,pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
            {"error": "User not logged in"},
            status=status.HTTP_401_UNAUTHORIZED
            )
        try:
            course = Course.objects.get(pk=pk)
            old_file=course.certificate_file
        except Course.DoesNotExist:
            return Response({"error": "Course not found"},status=status.HTTP_404_NOT_FOUND)
        
        # if course.user.register_no != user["register_no"]:
        #     return Response(
        #         {"error": "Permission denied"},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        course_serializer=CreateCourseSerializer(course,data=request.data)
        if course_serializer.is_valid():
            new_file = request.FILES.get("certificate_file")

            if new_file:
                allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']

                extension = new_file.name.split('.')[-1].lower()

                if extension not in allowed_extensions:
                    return Response(
                        {
                            "certificate_file": [
                                "Only image files (jpg, jpeg, png, gif, webp) are allowed."
                            ]
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            course_serializer.save()
            if old_file and new_file:
                old_file.delete(save=False)    
            course.points = 0
            course.approval_status = "pending"
            course.save()
            return Response(course_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                                course_serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST
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
        if course.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        if old_file:
            old_file.delete(save=False)
        course.delete()
        return Response(
            {"message": "Deleted successfully"},status=status.HTTP_200_OK)


    @action(detail=True,url_path='file', methods=["get"])
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

        url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": course.certificate_file.name
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