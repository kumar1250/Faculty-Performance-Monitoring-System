from django.db import models
from accounts.models import User
from core.storage import FDPs_Attended_Storage


class FDPs_Attended(models.Model):

    CATEGORY_CHOICES = (
        ('FDP', 'FDP/Workshop'),
        ('CONFERENCE', 'Conference/Seminar'),
    )

    INSTITUTE_CHOICES = (
        ('IIT', 'IIT'),
        ('NIT', 'NIT'),
        ('UNIVERSITY', 'University'),
        ('COLLEGE', 'College'),
        ('ABROAD', 'Abroad'),
    )

    DURATION_CHOICES = (
        ('GE_2W', '>= 2 Weeks'),
        ('BW_1W_2W', '1 Week to 2 Weeks'),
        ('LT_1W', '< 1 Week'),
    )

    LEVEL_CHOICES = (
        ('INTERNATIONAL', 'International'),
        ('NATIONAL', 'National'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fdp_activities'
    )

    title = models.CharField(max_length=255)

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    institute = models.CharField(
        max_length=20,
        choices=INSTITUTE_CHOICES
    )

    duration = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES,
        blank=True,
        null=True
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        blank=True,
        null=True
    )

    issue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)

    certificate_file = models.FileField(
        storage=FDPs_Attended_Storage(),
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

    def __str__(self):
        return f"{self.title} - {self.points} Points"