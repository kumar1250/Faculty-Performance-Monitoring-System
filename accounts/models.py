from django.db import models
from django.contrib.auth.hashers import make_password
import random
import uuid
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class User(models.Model):
    ROLE_CHOICES = (
        ('principal', 'Principal'),
        ('dean', 'Dean'),
        ('hod', 'HOD'),
        ('committee_coordinator', 'Committee Coordinator'),
        ('department_incharge', 'Department Incharge'),
        ('faculty', 'Faculty'),
    )

    username = models.CharField(max_length=100)
    register_no = models.CharField(max_length=10, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    points=models.IntegerField(default=0,blank=True)
    
    def save(self, *args, **kwargs):
        # Hash the password before saving
        if not self.password.startswith('pbkdf2_'):  # Only hash on creation
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username
    
class BlacklistedToken(models.Model):
        token = models.TextField(unique=True)
        blacklisted_at = models.DateTimeField(auto_now_add=True)

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    reset_token = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # OTP and reset_token both expire in 10 minutes
        return not self.is_used and timezone.now() < self.created_at + timedelta(minutes=10)

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))