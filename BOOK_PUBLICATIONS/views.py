from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .models import BookPublication
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD
from .serializers import BookPublicationSerializer, CreateBookPublicationSerializer
from accounts.models import User

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

import boto3
from django.conf import settings
from .utils import send_publication_status_email

def compute_points(publisher_type, isbn_status, author_type):
    """
    Points table:
    
    International Publisher:
        ISBN YES + 1st author        -> 10
        ISBN NO  + 1st author        -> 5
        ISBN YES + other than 1st    -> 7.5
        ISBN NO  + other than 1st    -> 2.5

    National Publisher:
        ISBN YES + 1st author        -> 7.5
        ISBN NO  + 1st author        -> 3.5
        ISBN YES + other than 1st    -> 5
        ISBN NO  + other than 1st    -> 1.5
    """
    table = {
        ("international", "yes", "first_author"):  10,
        ("international", "no",  "first_author"):   5,
        ("international", "yes", "co_author"):      7.5,
        ("international", "no",  "co_author"):      2.5,
        ("national",      "yes", "first_author"):   7.5,
        ("national",      "no",  "first_author"):   3.5,
        ("national",      "yes", "co_author"):      5,
        ("national",      "no",  "co_author"):      1.5,
    }
    return table.get((publisher_type, isbn_status, author_type), 0)


class BookPublicationViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ("approve_publication", "pending_list"):
            permission_classes = [IsHOD]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    # ------------------------------------------------------------------ #
    # CREATE  POST /book-publications/create/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="create", methods=["post"])
    def create_publication(self, request):
        serializer = CreateBookPublicationSerializer(data=request.data)
        if serializer.is_valid():
            user = decode_token(get_token_from_request(request))
            serializer.save(user=User.objects.get(register_no=user["register_no"]))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ #
    # LIST ALL  GET /book-publications/list/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="list", methods=["get"])
    def publications_list(self, request):
        publications = BookPublication.objects.all()
        serializer = BookPublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # LIST BY USER  GET /book-publications/user/<register_no>/
    # ------------------------------------------------------------------ #
    @action(
        detail=False,
        url_path=r"user/(?P<register_no>[^/.]+)",
        methods=["get"],
    )
    def user_publications(self, request, register_no=None):
        try:
            user = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        publications = user.book_publications.all()
        serializer = BookPublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # UPDATE  PUT /book-publications/<pk>/update/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="update", methods=["put"])
    def update_publication(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            publication = BookPublication.objects.get(pk=pk)
            old_file = publication.certificate_file
        except BookPublication.DoesNotExist:
            return Response(
                {"error": "Book publication not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Collect fields
        book_title      = request.data.get("book_title")
        publisher_name  = request.data.get("publisher_name")
        publisher_type  = request.data.get("publisher_type")
        isbn_status     = request.data.get("isbn_status")
        isbn_number     = request.data.get("isbn_number")
        author_type     = request.data.get("author_type")
        publication_date = request.data.get("publication_date")
        user_id         = request.data.get("user")
        new_file        = request.FILES.get("certificate_file")

        # ---- Validation ------------------------------------------------
        errors = {}

        if not user_id:
            errors["user"] = ["This field is required."]

        if not book_title:
            errors["book_title"] = ["This field is required."]
        elif len(book_title.strip()) < 3:
            errors["book_title"] = ["Book title must be at least 3 characters."]

        allowed_publisher_types = ["international", "national"]
        if not publisher_type:
            errors["publisher_type"] = ["This field is required."]
        elif publisher_type not in allowed_publisher_types:
            errors["publisher_type"] = [
                f"Invalid publisher type. Allowed: {allowed_publisher_types}"
            ]

        allowed_isbn_statuses = ["yes", "no"]
        if not isbn_status:
            errors["isbn_status"] = ["This field is required."]
        elif isbn_status not in allowed_isbn_statuses:
            errors["isbn_status"] = [
                f"Invalid ISBN status. Allowed: {allowed_isbn_statuses}"
            ]

        allowed_author_types = ["first_author", "co_author"]
        if not author_type:
            errors["author_type"] = ["This field is required."]
        elif author_type not in allowed_author_types:
            errors["author_type"] = [
                f"Invalid author type. Allowed: {allowed_author_types}"
            ]

        if not publication_date:
            errors["publication_date"] = ["This field is required."]

        if new_file:
            allowed_extensions = ["pdf", "jpg", "jpeg", "png", "gif", "webp"]
            extension = new_file.name.split(".")[-1].lower()
            if extension not in allowed_extensions:
                errors["certificate_file"] = [
                    "Only pdf, jpg, jpeg, png, gif, and webp files are allowed."
                ]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ---- Apply updates ---------------------------------------------
        publication.user_id          = user_id
        publication.book_title       = book_title
        publication.publisher_name   = publisher_name
        publication.publisher_type   = publisher_type
        publication.isbn_status      = isbn_status
        publication.isbn_number      = isbn_number
        publication.author_type      = author_type
        publication.publication_date = publication_date

        if new_file:
            if old_file:
                old_file.delete(save=False)
            publication.certificate_file = new_file

        # Reset approval on update
        publication.points          = 0
        publication.approval_status = "pending"
        publication.save()

        return Response(
            {
                "id":               publication.id,
                "user":             publication.user_id,
                "book_title":       publication.book_title,
                "publisher_type":   publication.publisher_type,
                "isbn_status":      publication.isbn_status,
                "author_type":      publication.author_type,
                "publication_date": str(publication.publication_date),
                "certificate_file": (
                    publication.certificate_file.url
                    if publication.certificate_file
                    else None
                ),
                "approval_status":  publication.approval_status,
                "points":           publication.points,
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # APPROVE / REJECT  POST /book-publications/<pk>/approve/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="approve", methods=["post"])
    def approve_publication(self, request, pk=None):
        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            publication = BookPublication.objects.get(pk=pk)
        except BookPublication.DoesNotExist:
            return Response(
                {"error": "Book publication not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if publication.approval_status in ("approved", "rejected"):
            return Response(
                {"error": "Request already processed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # HOD cannot approve their own submission
        if publication.user.register_no == user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        status_value = request.data.get("status")
        remarks      = request.data.get("remarks")

        if status_value not in ("approved", "rejected"):
            return Response(
                {"error": "Invalid status. Use 'approved' or 'rejected'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        publication.approval_status = status_value
        publication.remarks         = remarks
        publication.approved_by     = user["username"]

        if status_value == "approved":
            publication.points = compute_points(
                publication.publisher_type,
                publication.isbn_status,
                publication.author_type,
            )
            publication.save()
            try:
                send_publication_status_email(
                    email=publication.user.email,
                    username=publication.user.username,
                    publication_title=publication.book_title,
                    status=publication.approval_status,
                    remarks=publication.remarks,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")
            serializer = BookPublicationSerializer(publication)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Rejected
        if not publication.remarks:
            publication.remarks = (
                f"Rejected by {user['username']} ({user['register_no']})"
            )
        publication.save()
        try:
            send_publication_status_email(
                email=publication.user.email,
                username=publication.user.username,
                publication_title=publication.book_title,
                status=publication.approval_status,
                remarks=publication.remarks,
            )
        except Exception as e:
            print(f"Email sending failed: {e}")

        return Response(
            {"message": publication.remarks},
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # DELETE  DELETE /book-publications/<pk>/delete/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="delete", methods=["delete"])
    def delete_publication(self, request, pk=None):
        try:
            publication = BookPublication.objects.get(pk=pk)
            old_file = publication.certificate_file
        except BookPublication.DoesNotExist:
            return Response(
                {"error": "Book publication not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            user = decode_token(get_token_from_request(request))
        except Exception:
            return Response(
                {"error": "User not logged in"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if publication.user.register_no != user["register_no"]:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if old_file:
            old_file.delete(save=False)
        publication.delete()
        return Response(
            {"message": "Deleted successfully"},
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # PRESIGNED FILE URL  GET /book-publications/<pk>/file/
    # ------------------------------------------------------------------ #
    @action(detail=True, url_path="file", methods=["get"])
    def certificate_url(self, request, pk=None):
        try:
            publication = BookPublication.objects.get(pk=pk)
        except BookPublication.DoesNotExist:
            return Response(
                {"error": "Book publication not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not publication.certificate_file:
            return Response(
                {"error": "No certificate file uploaded"},
                status=status.HTTP_404_NOT_FOUND,
            )

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        key = f"book_publications/{publication.certificate_file.name}"

        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=3600,
        )
        return Response({"certificate_url": url})

    # ------------------------------------------------------------------ #
    # PENDING LIST (HOD only)  GET /book-publications/requests/
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path="requests", methods=["get"])
    def pending_list(self, request):
        publications = BookPublication.objects.filter(approval_status="pending")
        serializer = BookPublicationSerializer(publications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)