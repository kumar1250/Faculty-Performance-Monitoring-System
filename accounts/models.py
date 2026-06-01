from django.db import models
from django.contrib.auth.hashers import make_password

# Create your models here.

class User (models.Model):
    ROLE_CHOICES = (
        ('principal', 'Principal'),
        ('dean', 'Dean'),
        ('hod', 'HOD'),
        ('committee_coordinator', 'Committee Coordinator'),
        ('department_incharge', 'Department Incharge'),
        ('faculty', 'Faculty'),
    )

    username = models.CharField(max_length=100)
    register_no = models.CharField(max_length=10, unique=True,blank=True)
    email = models.EmailField(unique=True,blank=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    points=models.IntegerField(default=0,blank=True,null=True)
    
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
    