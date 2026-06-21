from django.contrib import admin
from .models import StudentFeedbackPerformance


@admin.register(StudentFeedbackPerformance)
class StudentFeedbackPerformanceAdmin(admin.ModelAdmin):
    # Note: this model has no approval_status field (the approve_feedback
    # action referenced in views.py was never implemented), so there's no
    # status to approve here yet — admin can only view/edit the raw record.
    list_display = (
        "id",
        "subject_name",
        "user_display",
        "academic_year",
        "cycle_1_feedback",
        "cycle_2_feedback",
        "exam_result",
        "points",
    )
    list_display_links = ("id", "subject_name")
    list_editable = ("points",)
    search_fields = (
        "subject_name",
        "user__username",
        "user__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def user_display(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.register_no})"
        return "-"