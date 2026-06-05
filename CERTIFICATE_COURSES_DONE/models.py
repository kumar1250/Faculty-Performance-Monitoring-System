from django.db import models
from core.storage import CertificateStorage
from accounts.models import User


# Create your models here.

class Course(models.Model):
    CERTIFICATE_TYPES = (
        ('NPTEL', 'AICTE-QIP/NPTEL'),
        ('OTHER', 'Other'),
    )
    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='coursedone')
    Course_name = models.CharField(max_length=255)
    certificate_type = models.CharField(max_length=255, choices=CERTIFICATE_TYPES)
    isue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)
    approval_status = models.CharField(max_length=10, choices=APPROVAL_STATUS, default='pending', blank=True, null=True)
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    certificate_file = models.FileField(storage=CertificateStorage(),blank=True, null=True)
    points = models.IntegerField(default=0, blank=True, null=True)
    message =models.TextField(blank=True,null=True)
    def __str__(self):
        return f"{self.Course_name} - {self.certificate_type} - {self.points}"