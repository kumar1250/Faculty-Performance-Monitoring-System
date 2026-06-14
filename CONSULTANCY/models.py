from django.db import models
from accounts.models import User
from core.storage import  Consultancy_Storage


class Consultancy(models.Model):

    POSITION_CHOICES = (
        ('SINGLE', 'Single'),
        ('OTHER', 'Other than First Person'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consultancy_activities'
    )

    title = models.CharField(max_length=255)

    organization_name = models.CharField(
        max_length=255
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES
    )

    issue_date = models.DateField(auto_now_add=True)

    update_date = models.DateField(auto_now=True)

    certificate_file = models.FileField(
        storage= Consultancy_Storage(),
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