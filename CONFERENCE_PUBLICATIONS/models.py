from django.db import models
from accounts.models import User


class ConferencePublication(models.Model):

    PUBLICATION_TYPE = (
        ('conference', 'Conference Publication'),
        ('book_chapter', 'Book Chapter'),
    )

    PROCEEDING_TYPE = (
        ('ieee_springer_elsevier', 'IEEE/Springer/Elsevier or Equivalent'),
        ('other_scopus', 'Other Scopus Proceedings'),
    )

    AUTHOR_TYPE = (
        ('first_author', 'First Author'),
        ('co_author', 'Other than First Author'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conference_publications'
    )

    publication_type = models.CharField(
        max_length=20,
        choices=PUBLICATION_TYPE
    )

    title = models.CharField(max_length=500)

    proceeding_type = models.CharField(
        max_length=50,
        choices=PROCEEDING_TYPE,
        blank=True,
        null=True
    )

    author_type = models.CharField(
        max_length=20,
        choices=AUTHOR_TYPE
    )

    publisher_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    isbn_issn = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    scopus_indexed = models.BooleanField(default=True)

    publication_date = models.DateField()

    document = models.FileField(
        upload_to='conference_publications/',
        blank=True,
        null=True
    )

    points = models.IntegerField(
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
        return self.title