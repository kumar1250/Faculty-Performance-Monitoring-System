from django.contrib import admin
from .models import User, Profile, BlacklistedToken, PasswordResetOTP


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "register_no",
        "email",
        "role",
        "points",
    )
    list_display_links = ("id", "username")
    list_editable = ("role", "points")
    list_filter = ("role",)
    search_fields = ("username", "register_no", "email")
    ordering = ("-id",)
    list_per_page = 25
    # Password is hashed on save() in the model, so editing it here still
    # goes through make_password() — fine for resets, just don't paste a
    # hash back in.


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "headline",
        "department",
        "experience_years",
    )
    list_display_links = ("id", "user")
    search_fields = ("user__username", "user__register_no", "department")
    ordering = ("-id",)


admin.site.register(BlacklistedToken)
admin.site.register(PasswordResetOTP)