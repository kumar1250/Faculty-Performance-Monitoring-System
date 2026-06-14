from django.db import models
from accounts.models import User
from core.storage import Book_publication_Storage


class BookPublication(models.Model):

    PUBLISHER_TYPE = (
        ('international', 'International Publisher'),
        ('national', 'National Publisher'),
    )

    ISBN_STATUS = (
        ('yes', 'ISBN Available'),
        ('no', 'ISBN Not Available'),
    )

    AUTHOR_TYPE = (
        ('first_author', '1st Author'),
        ('co_author', 'Other than 1st Author'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='book_publications'
    )

    book_title = models.CharField(max_length=500)

    publisher_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    publisher_type = models.CharField(
        max_length=20,
        choices=PUBLISHER_TYPE
    )

    isbn_status = models.CharField(
        max_length=10,
        choices=ISBN_STATUS
    )

    isbn_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    author_type = models.CharField(
        max_length=20,
        choices=AUTHOR_TYPE
    )

    publication_date = models.DateField()

    certificate_file = models.FileField(
        storage=Book_publication_Storage(),
        blank=True,
        null=True
    )

    points = models.FloatField(
        default=0,
        blank=True,
        null=True
    )

    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS,
        default='pending'
    )

    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):
        return self.book_title