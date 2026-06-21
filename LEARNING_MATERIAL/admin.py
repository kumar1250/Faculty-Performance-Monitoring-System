from django.contrib import admin
from .models import SubjectContribution


@admin.register(SubjectContribution)
class SubjectContributionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject_name",
        "user_display",
        "approval_status",
        "points",
        "approved_by",
        "created_date",
    )
    list_display_links = ("id", "subject_name")
    list_editable = ("approval_status", "points")
    list_filter = ("approval_status",)
    search_fields = (
        "subject_name",
        "user__username",
        "user__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.register_no})"