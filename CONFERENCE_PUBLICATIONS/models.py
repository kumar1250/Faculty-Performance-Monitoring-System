from django.db import models
from accounts.models import User
from core.storage import ConferenceCertificate


class Publication(models.Model):

    PUBLICATION_TYPE_CHOICES = (
        ('PROCEEDING', 'Conference Proceeding'),
        ('BOOK_CHAPTER', 'Book Chapter'),
    )

    INDEXING_CHOICES = (
        ('IEEE_SPRINGER_ELSEVIER', 'IEEE/Springer/Elsevier or Equivalent'),
        ('SCOPUS', 'Other Scopus Indexed'),
    )

    AUTHOR_TYPE_CHOICES = (
        ('FIRST_AUTHOR', 'First Author'),
        ('CO_AUTHOR', 'Other than First Author'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='publications')
    title = models.CharField(max_length=500)
    publication_type = models.CharField(max_length=20,choices=PUBLICATION_TYPE_CHOICES)
    indexing_type = models.CharField( max_length=30,choices=INDEXING_CHOICES)
    author_type = models.CharField(max_length=20,choices=AUTHOR_TYPE_CHOICES)
    publisher_name = models.CharField(max_length=255)
    publication_date = models.DateField()
    certificate_file = models.FileField(storage=ConferenceCertificate(),blank=True,null=True)
    points = models.IntegerField(default=0)
    approval_status = models.CharField(max_length=10,choices=APPROVAL_STATUS,default='pending')
    approved_by = models.CharField(max_length=100,blank=True,null=True)
    message = models.TextField(blank=True,null=True)
    issue_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)
    def __str__(self):
        return f"{self.title} - {self.points} Points"