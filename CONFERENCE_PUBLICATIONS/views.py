from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import Publication
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD ,IsDean,IsPrincipal
from .serializers import PublicationSerializer, CreatePublicationSerializer

from accounts.models import User

import boto3
from django.conf import settings

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .utils import send_publication_status_email

def allocate_points(publication_type, indexing_type, author_type):
    """
    Points table:
    ---------------------------------------------------------------
    PROCEEDING | IEEE_SPRINGER_ELSEVIER | FIRST_AUTHOR       -> 10
    PROCEEDING | IEEE_SPRINGER_ELSEVIER | CO_AUTHOR          ->  8
    PROCEEDING | SCOPUS                 | FIRST_AUTHOR       ->  8
    PROCEEDING | SCOPUS                 | CO_AUTHOR          ->  7
    BOOK_CHAPTER | SCOPUS (only)        | FIRST_AUTHOR       -> 10
    BOOK_CHAPTER | SCOPUS (only)        | CO_AUTHOR          ->  8
    ---------------------------------------------------------------
    """
    if publication_type == 'PROCEEDING':
        if indexing_type == 'IEEE_SPRINGER_ELSEVIER':
            return 10 if author_type == 'FIRST_AUTHOR' else 8
        elif indexing_type == 'SCOPUS':
            return 8 if author_type == 'FIRST_AUTHOR' else 7

    elif publication_type == 'BOOK_CHAPTER':
        # Book chapters are Scopus indexed only
        return 10 if author_type == 'FIRST_AUTHOR' else 8

    return 0


class PublicationViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['approve_publication', 'pending_list']:
            permission_classes = [IsHOD | IsDean | IsPrincipal]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /publications/publication/
    @action(detail=False, url_path='publication', methods=['post'])
    def create_publication(self, request):
        serializer = CreatePublicationSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /publications/userpublications/<register_no>/
    @action(detail=False, url_path='userpublications/(?P<register_no>[^/.]+)', methods=['get'])
    def user_publication_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        publications = user.publications.all()
        serializer = PublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /publications/publications/
    @action(detail=False, url_path='publications', methods=['get'])
    def publications_list(self, request):
        publications = Publication.objects.all()
        serializer = PublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /publications/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_publication(self, request, pk=None):
        try:
            decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            publication = Publication.objects.get(pk=pk)
            old_file = publication.certificate_file
        except Publication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        title = request.data.get("title")
        publication_type = request.data.get("publication_type")
        indexing_type = request.data.get("indexing_type")
        author_type = request.data.get("author_type")
        publisher_name = request.data.get("publisher_name")
        publication_date = request.data.get("publication_date")
        user_id = request.data.get("user")
        new_file = request.FILES.get("certificate_file")

        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not title:
            errors["title"] = ["This field is required."]
        elif len(title.strip()) < 3:
            errors["title"] = ["Title must contain at least 3 characters."]

        allowed_publication_types = ["PROCEEDING", "BOOK_CHAPTER"]
        if not publication_type:
            errors["publication_type"] = ["This field is required."]
        elif publication_type not in allowed_publication_types:
            errors["publication_type"] = [
                f"Invalid publication type. Allowed values are {allowed_publication_types}"
            ]

        allowed_indexing_types = ["IEEE_SPRINGER_ELSEVIER", "SCOPUS"]
        if not indexing_type:
            errors["indexing_type"] = ["This field is required."]
        elif indexing_type not in allowed_indexing_types:
            errors["indexing_type"] = [
                f"Invalid indexing type. Allowed values are {allowed_indexing_types}"
            ]

        # Book chapters only support SCOPUS indexing
        if (
            publication_type == "BOOK_CHAPTER"
            and indexing_type == "IEEE_SPRINGER_ELSEVIER"
            and "indexing_type" not in errors
        ):
            errors["indexing_type"] = ["Book chapters support Scopus indexing only."]

        allowed_author_types = ["FIRST_AUTHOR", "CO_AUTHOR"]
        if not author_type:
            errors["author_type"] = ["This field is required."]
        elif author_type not in allowed_author_types:
            errors["author_type"] = [
                f"Invalid author type. Allowed values are {allowed_author_types}"
            ]

        if not publisher_name:
            errors["publisher_name"] = ["This field is required."]

        if not publication_date:
            errors["publication_date"] = ["This field is required."]

        if new_file:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            extension = new_file.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only image files (jpg, jpeg, png, gif, webp) are allowed."
                ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        publication.user_id = user_id
        publication.title = title
        publication.publication_type = publication_type
        publication.indexing_type = indexing_type
        publication.author_type = author_type
        publication.publisher_name = publisher_name
        publication.publication_date = publication_date

        if new_file:
            if old_file:
                old_file.delete(save=False)
            publication.certificate_file = new_file

        # Reset approval on edit
        publication.points = 0
        publication.approval_status = "pending"
        publication.approved_by = None
        publication.message = None

        publication.save()

        return Response(
            {
                "id": publication.id,
                "user": publication.user_id,
                "title": publication.title,
                "publication_type": publication.publication_type,
                "indexing_type": publication.indexing_type,
                "author_type": publication.author_type,
                "publisher_name": publication.publisher_name,
                "publication_date": publication.publication_date,
                "certificate_file": (
                    publication.certificate_file.url if publication.certificate_file else None
                ),
                "approval_status": publication.approval_status,
                "points": publication.points,
            },
            status=status.HTTP_200_OK
        )

    # POST /publications/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_publication(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            publication = Publication.objects.get(pk=pk)
        except Publication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        if publication.approval_status in ["approved", "rejected"]:
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if publication.user.register_no == user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        status_value = request.data.get("status")
        message = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        publication.approval_status = status_value
        publication.message = message
        publication.approved_by = user["username"]

        if status_value == "approved":
            publication.points = allocate_points(
                publication.publication_type,
                publication.indexing_type,
                publication.author_type
            )
            publication.save()
            try:
                send_publication_status_email(
                    email=publication.user.email,
                    username=publication.user.username,
                    publication_title=publication.title,  # replace with your actual field name
                    status=publication.approval_status,
                    message=publication.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            serializer = PublicationSerializer(publication)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif status_value == "rejected":
            publication.points = 0
            if not publication.message:
                publication.message = (
                    f"Rejected by {user['username']} ({user['register_no']})"
                )
            publication.save()
            try:
                send_publication_status_email(
                    email=publication.user.email,
                    username=publication.user.username,
                    publication_title=publication.title,  # replace with your actual field name
                    status=publication.approval_status,
                    message=publication.message,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            return Response({"message": publication.message}, status=status.HTTP_200_OK)

    # DELETE /publications/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_publication(self, request, pk=None):
        try:
            publication = Publication.objects.get(pk=pk)
            old_file = publication.certificate_file
        except Publication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        if publication.user.register_no != user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        if old_file:
            old_file.delete(save=False)

        publication.delete()
        return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)

    # GET /publications/<pk>/file/
    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            publication = Publication.objects.get(pk=pk)
        except Publication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        if not publication.certificate_file:
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

        key = f"conference_certificates/{publication.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )

        return Response({"certificate_url": url})

    # GET /publications/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        publications = Publication.objects.filter(approval_status="pending")
        serializer = PublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
