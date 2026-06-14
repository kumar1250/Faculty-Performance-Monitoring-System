from django.db import models
from accounts.models import User
from core.storage import FDPs_Organized_Storage


class FDPs_Organized(models.Model):

    ACTIVITY_CHOICES = (
        ('CONFERENCE', 'Conference/Seminar'),
        ('FDP', 'FDP/Workshop'),
    )

    FUNDING_CHOICES = (
        ('EXTERNAL', 'External'),
        ('INTERNAL', 'Internal'),
    )

    LEVEL_CHOICES = (
        ('INTERNATIONAL', 'International'),
        ('NATIONAL', 'National'),
    )

    DURATION_CHOICES = (
        ('GE_2W', '>= 2 Weeks'),
        ('BW_1W_2W', '1 Week to 2 Weeks'),
        ('LT_1W', '< 1 Week'),
    )

    CAPACITY_CHOICES = (
        ('CONVENOR', 'Convenor'),
        ('CO_CONVENOR', 'Co-Convenor'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fdps_organizeds'
    )

    title = models.CharField(max_length=255)

    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_CHOICES
    )

    funding_type = models.CharField(
        max_length=20,
        choices=FUNDING_CHOICES
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES
    )

    duration = models.CharField(
        max_length=20,
        choices=DURATION_CHOICES,
        blank=True,
        null=True,
        help_text="Applicable only for FDP/Workshop"
    )

    capacity = models.CharField(
        max_length=20,
        choices=CAPACITY_CHOICES
    )

    issue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)

    certificate_file = models.FileField(
        storage=FDPs_Organized_Storage(),
        blank=True,
        null=True
    )

    points = models.FloatField(default=0)

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