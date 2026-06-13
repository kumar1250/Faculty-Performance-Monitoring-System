from django.db import models
from accounts.models import User


class ResearchGuidance(models.Model):
    GUIDE_TYPE = (
        ('Guide', 'Guide'),
        ('Co-Guide', 'Co-Guide'),
    )

    STATUS_CHOICES = (
        ('ongoing', 'Ongoing'),
        ('awarded', 'Awarded'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='research_guidance'
    )

    scholar_name = models.CharField(max_length=255)
    guide_type = models.CharField(
        max_length=20,
        choices=GUIDE_TYPE
    )

    registration_date = models.DateField()
    awarded_date = models.DateField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ongoing'
    )

    points = models.FloatField(default=0)

    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS,
        default='pending',
        blank=True,
        null=True
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

    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return f"{self.scholar_name} - {self.guide_type}"