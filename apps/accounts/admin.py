from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SarthiUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Sarthi", {"fields": ("phone", "telegram_user_id")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Sarthi", {"fields": ("phone", "telegram_user_id")}),)
    list_display = ("username", "email", "is_staff", "is_active")
