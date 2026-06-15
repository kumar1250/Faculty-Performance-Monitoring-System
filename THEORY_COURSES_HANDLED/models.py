from django.db import models
from accounts.models import User


class StudentFeedbackPerformance(models.Model):

    FEEDBACK_CHOICES = (
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('satisfactory', 'Satisfactory'),
    )

    EXAM_RESULT_CHOICES = (
        ('ge_90', '>=90%'),
        ('ge_80', '>=80%'),
        ('ge_70', '>=70%'),
        ('lt_70', '<70%'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_feedback_performances',
        blank=True,
        null=True
    )

    academic_year = models.CharField(
        max_length=20
    )

    subject_name = models.CharField(
        max_length=255
    )

    cycle_1_feedback = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        blank=True,
        null=True
    )

    cycle_2_feedback = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        blank=True,
        null=True
    )

    exam_result = models.CharField(
        max_length=10,
        choices=EXAM_RESULT_CHOICES,
        blank=True,
        null=True
    )

    points = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        blank=True,
        null=True
    )

    message = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.user} - "
            f"{self.subject_name} - "
            f"{self.get_cycle_1_feedback_display()} / "
            f"{self.get_cycle_2_feedback_display()}"
        )