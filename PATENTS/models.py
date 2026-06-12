from django.db import models
from accounts.models import User
from core.storage import Patent_certificate


class Patent(models.Model):

    PATENT_TYPE_CHOICES = (
        ('GRANTED_FIRST', 'Granted Patent (1st Applicant)'),
        ('GRANTED_OTHER', 'Granted Patent (Other than 1st Applicant)'),
        ('PUBLISHED_FIRST', 'Patent Published (1st Applicant)'),
        ('PUBLISHED_OTHER', 'Patent Published (Other than 1st Applicant)'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='patent_activities'
    )

    title = models.CharField(max_length=255)

    patent_number = models.CharField(
        max_length=100,
        unique=True
    )

    patent_type = models.CharField(
        max_length=30,
        choices=PATENT_TYPE_CHOICES
    )

    issue_date = models.DateField(auto_now_add=True)

    update_date = models.DateField(auto_now=True)

    certificate_file = models.FileField(
        storage=Patent_certificate(),
        blank=True,
        null=True
    )

    points = models.IntegerField(default=0)

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

    def save(self, *args, **kwargs):

        point_map = {
            'GRANTED_FIRST': 10,
            'GRANTED_OTHER': 9,
            'PUBLISHED_FIRST': 8,
            'PUBLISHED_OTHER': 7,
        }

        self.points = point_map.get(self.patent_type, 0)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.points} Points"