from django.contrib import admin
from .models import BookPublication


@admin.register(BookPublication)
class BookPublicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "book_title",
        "user_display",
        "approval_status",
        "points",
        "approved_by",
        "created_at",
    )
    list_display_links = ("id", "book_title")
    list_editable = ("approval_status", "points")
    list_filter = ("approval_status",)
    search_fields = (
        "book_title",
        "user__username",
        "user__register_no",
    )
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Faculty")
    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.register_no})"