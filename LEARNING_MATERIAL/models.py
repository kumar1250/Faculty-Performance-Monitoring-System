from django.db import models
from accounts.models import User

class SubjectContribution(models.Model):

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    SEMESTER_CHOICES = (
        ('1-1', '1-1'),
        ('1-2', '1-2'),
        ('2-1', '2-1'),
        ('2-2', '2-2'),
        ('3-1', '3-1'),
        ('3-2', '3-2'),
        ('4-1', '4-1'),
        ('4-2', '4-2'),
    )

    semester = models.CharField(
        max_length=10,
        choices=SEMESTER_CHOICES,
        blank=True,
        null=True
    )


    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subject_contributions'
    )

    subject_name = models.CharField(max_length=255)
    academic_year = models.CharField(max_length=20, blank=True, null=True)
    semester = models.CharField(
        max_length=10,
        choices=SEMESTER_CHOICES,
        blank=True,
        null=True
    )

    created_date = models.DateField(auto_now_add=True)
    updated_date = models.DateField(auto_now=True)

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

    points = models.IntegerField(
        blank=True,
        null=True
    )

    message = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.subject_name} - {self.user.username} - {self.points}"