from django.contrib import admin
from .models import StudentCounselling


@admin.register(StudentCounselling)
class StudentCounsellingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "total_students",
        "faculty_display",
        "approval_status",
        "points",
        "approved_by",
        "created_at",
    )
    list_display_links = ("id", "total_students")
    list_editable = ("approval_status", "points")
    list_filter = ("approval_status",)
    search_fields = (
        "total_students",
        "faculty__username",
        "faculty__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def faculty_display(self, obj):
        return f"{obj.faculty.username} ({obj.faculty.register_no})"