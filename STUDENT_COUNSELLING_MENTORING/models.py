from django.db import models
from accounts.models import User


class StudentCounselling(models.Model):

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    faculty = models.ForeignKey(User,on_delete=models.CASCADE,related_name='student_counselling')
    total_students = models.PositiveIntegerField()
    points = models.DecimalField(max_digits=5,decimal_places=2,default=0)
    approval_status = models.CharField(max_length=10,choices=APPROVAL_STATUS,default='pending')
    approved_by = models.CharField(max_length=100,blank=True,null=True)
    message = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.faculty} - {self.total_students} Students"