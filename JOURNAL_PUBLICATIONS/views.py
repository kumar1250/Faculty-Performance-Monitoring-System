from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import JournalPublication
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import JournalPublicationSerializer, CreateJournalPublicationSerializer
from accounts.models import User

import boto3
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class JournalPublicationViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['approve_publication', 'pending_list']:
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # POST /journalpublication/create/
    @action(detail=False, url_path='create', methods=['post'])
    def create_publication(self, request):
        serializer = CreateJournalPublicationSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # GET /journalpublication/user/<register_no>/
    @action(detail=False, url_path='user/(?P<register_no>[^/.]+)', methods=['get'])
    def user_publication_list(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        publications = user.journal_publications.all()
        serializer = JournalPublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # GET /journalpublication/all/
    @action(detail=False, url_path='all', methods=['get'])
    def publications_list(self, request):
        publications = JournalPublication.objects.all()
        serializer = JournalPublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # PUT /journalpublication/<pk>/update/
    @action(detail=True, url_path='update', methods=['put'])
    def update_publication(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            publication = JournalPublication.objects.get(pk=pk)
            old_file = publication.certificate_file
        except JournalPublication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        publication_title = request.data.get("publication_title")
        journal_name = request.data.get("journal_name")
        publication_type = request.data.get("publication_type")
        author_type = request.data.get("author_type")
        doi_number = request.data.get("doi_number")
        publication_date = request.data.get("publication_date")
        user_id = request.data.get("user")
        new_file = request.FILES.get("certificate_file")

        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not publication_title:
            errors["publication_title"] = ["This field is required."]
        elif len(publication_title.strip()) < 3:
            errors["publication_title"] = ["Publication title must contain at least 3 characters."]

        allowed_publication_types = ["SCI", "SCOPUS", "UGC", "PEER_REVIEWED"]
        if not publication_type:
            errors["publication_type"] = ["This field is required."]
        elif publication_type not in allowed_publication_types:
            errors["publication_type"] = [f"Invalid publication type. Allowed values are {allowed_publication_types}"]

        allowed_author_types = ["FIRST_AUTHOR", "OTHER_AUTHOR"]
        if not author_type:
            errors["author_type"] = ["This field is required."]
        elif author_type not in allowed_author_types:
            errors["author_type"] = [f"Invalid author type. Allowed values are {allowed_author_types}"]

        if new_file:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'pdf']
            extension = new_file.name.split('.')[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = ["Only jpg, jpeg, png, gif, webp and pdf files are allowed."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        publication.user_id = user_id
        publication.publication_title = publication_title
        publication.journal_name = journal_name
        publication.publication_type = publication_type
        publication.author_type = author_type
        publication.doi_number = doi_number
        publication.publication_date = publication_date

        if new_file:
            if old_file:
                old_file.delete(save=False)
            publication.certificate_file = new_file

        # Reset approval on any update
        publication.points = 0
        publication.approval_status = "pending"
        publication.save()

        return Response(
            {
                "id": publication.id,
                "user": publication.user_id,
                "publication_title": publication.publication_title,
                "journal_name": publication.journal_name,
                "publication_type": publication.publication_type,
                "author_type": publication.author_type,
                "doi_number": publication.doi_number,
                "publication_date": str(publication.publication_date) if publication.publication_date else None,
                "certificate_file": publication.certificate_file.url if publication.certificate_file else None,
                "approval_status": publication.approval_status,
                "points": publication.points,
            },
            status=status.HTTP_200_OK
        )

    # POST /journalpublication/<pk>/approve/
    @action(detail=True, url_path='approve', methods=['post'])
    def approve_publication(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response({"error": "User not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            publication = JournalPublication.objects.get(pk=pk)
        except JournalPublication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        if publication.approval_status in ["approved", "rejected"]:
            return Response({"error": "Request already processed"}, status=status.HTTP_400_BAD_REQUEST)

        if publication.user.register_no == user["register_no"]:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        status_value = request.data.get("status")
        message = request.data.get("message")

        if status_value not in ["approved", "rejected"]:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        publication.approval_status = status_value
        publication.message = message
        publication.approved_by = user["username"]
        publication.save()

        if publication.approval_status == "approved":
            # Points rubric:
            # SCI          + FIRST_AUTHOR  = 25
            # SCI          + OTHER_AUTHOR  = 15
            # SCOPUS       + FIRST_AUTHOR  = 20
            # SCOPUS       + OTHER_AUTHOR  = 12
            # UGC          + FIRST_AUTHOR  = 15
            # UGC          + OTHER_AUTHOR  = 10
            # PEER_REVIEWED + FIRST_AUTHOR = 10
            # PEER_REVIEWED + OTHER_AUTHOR = 7
            points_map = {
                ("SCI", "FIRST_AUTHOR"): 25,
                ("SCI", "OTHER_AUTHOR"): 15,
                ("SCOPUS", "FIRST_AUTHOR"): 20,
                ("SCOPUS", "OTHER_AUTHOR"): 12,
                ("UGC", "FIRST_AUTHOR"): 15,
                ("UGC", "OTHER_AUTHOR"): 10,
                ("PEER_REVIEWED", "FIRST_AUTHOR"): 10,
                ("PEER_REVIEWED", "OTHER_AUTHOR"): 7,
            }
            publication.points = points_map.get((publication.publication_type, publication.author_type), 0)
            publication.save()

        elif publication.approval_status == "rejected":
            if not publication.message:
                publication.message = f"Rejected by {user['username']} ({user['register_no']})"
            publication.save()
            return Response({"message": publication.message}, status=status.HTTP_200_OK)

        serializer = JournalPublicationSerializer(publication)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # DELETE /journalpublication/<pk>/delete/
    @action(detail=True, url_path='delete', methods=['delete'])
    def delete_publication(self, request, pk=None):
        try:
            publication = JournalPublication.objects.get(pk=pk)
            old_file = publication.certificate_file
        except JournalPublication.DoesNotExist:
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

    # GET /journalpublication/<pk>/file/
    @action(detail=True, url_path='file', methods=['get'])
    def certificate_url(self, request, pk=None):
        try:
            publication = JournalPublication.objects.get(pk=pk)
        except JournalPublication.DoesNotExist:
            return Response({"error": "Publication not found"}, status=status.HTTP_404_NOT_FOUND)

        if not publication.certificate_file:
            return Response({"error": "No certificate file uploaded"}, status=status.HTTP_404_NOT_FOUND)

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )

        key = f"journal_publications/{publication.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key
            },
            ExpiresIn=3600
        )
        return Response({"certificate_url": url})

    # GET /journalpublication/requests/
    @action(detail=False, url_path='requests', methods=['get'])
    def pending_list(self, request):
        publications = JournalPublication.objects.filter(approval_status="pending")
        serializer = JournalPublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)