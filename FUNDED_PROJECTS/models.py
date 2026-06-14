from django.db import models
from accounts.models import User


class FundedProject(models.Model):

    GRANT_AMOUNT_CHOICES = (
        ('gt_10', 'More than 10 Lakhs'),
        ('5_10', '5 to 10 Lakhs'),
        ('lt_5', 'Less than 5 Lakhs'),
    )

    ROLE_CHOICES = (
        ('pi', 'Principal Investigator (PI)'),
        ('co_pi', 'Co-Principal Investigator (Co-PI)'),
    )

    APPROVAL_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='funded_projects'
    )

    project_title = models.CharField(max_length=500)

    funding_agency = models.CharField(max_length=255)

    grant_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    grant_category = models.CharField(
        max_length=20,
        choices=GRANT_AMOUNT_CHOICES
    )

    investigator_role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES
    )

    sanction_date = models.DateField()

    completion_date = models.DateField(
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
        default='pending'
    )

    approved_by = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def __str__(self):
        return self.project_title