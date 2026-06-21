from django.contrib import admin
from .models import ResearchGuidance


@admin.register(ResearchGuidance)
class ResearchGuidanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "scholar_name",
        "user_display",
        "approval_status",
        "points",
        "approved_by",
        "created_at",
    )
    list_display_links = ("id", "scholar_name")
    list_editable = ("approval_status", "points")
    list_filter = ("approval_status",)
    search_fields = (
        "scholar_name",
        "user__username",
        "user__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.register_no})"