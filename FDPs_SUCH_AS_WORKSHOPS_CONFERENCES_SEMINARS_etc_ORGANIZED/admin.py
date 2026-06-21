from django.contrib import admin
from .models import FDPs_Organized


@admin.register(FDPs_Organized)
class FDPs_OrganizedAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "user_display",
        "approval_status",
        "points",
        "approved_by",
        "issue_date",
    )
    list_display_links = ("id", "title")
    list_editable = ("approval_status", "points")
    list_filter = ("approval_status",)
    search_fields = (
        "title",
        "user__username",
        "user__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.register_no})"