from django.db import models
from accounts.models import User
from core.storage import Student_project_Storage


class StudentProjectWork(models.Model):

    PROJECT_TYPES = (
        ('BTECH', 'B.Tech Project'),
        ('MTECH', 'M.Tech Project'),
    )

    PUBLICATION_STATUS = (
        ('WITH_PUBLICATION', 'With Publication'),
        ('WITHOUT_PUBLICATION', 'Without Publication'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_project_works'
    )

    project_title = models.CharField(max_length=255)

    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPES
    )

    publication_status = models.CharField(
        max_length=30,
        choices=PUBLICATION_STATUS
    )

    student_names = models.TextField(
        blank=True,
        null=True,
        help_text="Names of students guided"
    )

    academic_year = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    certificate_file = models.FileField(
        storage=Student_project_Storage(),
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

    issue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)


    def __str__(self):
        return f"{self.project_title} - {self.project_type} - {self.points}"