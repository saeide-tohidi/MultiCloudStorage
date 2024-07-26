from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import (
    User,
)


class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
        "id",
        "email",
        "username",
        "is_staff",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "username",
                    "password",
                    "date_joined",
                    "last_login",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_staff", "user_permissions", "groups"), "classes": ("",)},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "is_staff",
                ),
            },
        ),
    )
    list_filter = ("is_staff", "is_superuser")
    search_fields = ("email", "username")
    readonly_fields = (
        "date_joined",
        "last_login",
    )


admin.site.register(User, CustomUserAdmin)
