from django.db import models
from accounts.models import User
from core.storage import Sessioncertificate


class ChairingSession(models.Model):
    EVENT_TYPE_CHOICES = (
        ('CHAIRING_SESSION', 'Chairing Session'),
        ('INVITED_TALK', 'Invited Talk'),
        ('GUEST_LECTURE', 'Guest Lecture'),
        ('KEYNOTE_SPEECH', 'Keynote Speech'),
    )
    
    EVENT_LEVEL_CHOICES = (
        ('INTERNATIONAL', 'International'),
        ('NATIONAL', 'National'),
        ('IIT_NIT', 'National IIT/NIT Level'),
        ('UNIVERSITY', 'University Level'),
        ('COLLEGE', 'College Level'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(User,on_delete=models.CASCADE, related_name='chairing_sessions')
    event_name = models.CharField(max_length=255)
    event_type = models.CharField(max_length=30,choices=EVENT_TYPE_CHOICES)
    organization = models.CharField(max_length=255)
    event_level = models.CharField(max_length=20,choices=EVENT_LEVEL_CHOICES)
    event_date = models.DateField()
    certificate_file = models.FileField(storage=Sessioncertificate(),blank=True,null=True)
    points = models.IntegerField(default=0)
    approval_status = models.CharField(max_length=10,choices=APPROVAL_STATUS,default='pending' )
    approved_by = models.CharField(max_length=100,blank=True,null=True )
    message = models.TextField( blank=True,null=True )
    issue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)
    def __str__(self):
        return f"{self.event_name} - {self.points} Points"
