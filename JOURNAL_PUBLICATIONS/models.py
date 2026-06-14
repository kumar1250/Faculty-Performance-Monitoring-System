from django.db import models
from accounts.models import User
from core.storage import JournalPublicationStorage


class JournalPublication(models.Model):

    PUBLICATION_TYPES = (
        ('SCI', 'SCI'),
        ('SCOPUS', 'Scopus'),
        ('UGC', 'UGC'),
        ('PEER_REVIEWED', 'Peer Reviewed'),
    )

    AUTHOR_TYPES = (
        ('FIRST_AUTHOR', '1st Author'),
        ('OTHER_AUTHOR', 'Other Than 1st Author'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='journal_publications'
    )

    publication_title = models.CharField(max_length=255)

    journal_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    publication_type = models.CharField(
        max_length=20,
        choices=PUBLICATION_TYPES
    )

    author_type = models.CharField(
        max_length=20,
        choices=AUTHOR_TYPES
    )

    doi_number = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    publication_date = models.DateField(
        blank=True,
        null=True
    )

    certificate_file = models.FileField(
        storage=JournalPublicationStorage(),
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

    message = models.TextField(
        blank=True,
        null=True
    )

    issue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.publication_title} - {self.publication_type} - {self.points}"