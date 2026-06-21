from django.contrib import admin
from .models import ChairingSession


@admin.register(ChairingSession)
class ChairingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_name",
        "user_display",
        "approval_status",
        "points",
        "approved_by",
        "issue_date",
    )
    list_display_links = ("id", "event_name")
    list_editable = ("approval_status", "points")
    list_filter = ("approval_status",)
    search_fields = (
        "event_name",
        "user__username",
        "user__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.register_no})"