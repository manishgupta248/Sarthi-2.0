from django.contrib import admin

from apps.core.admin_utils import AllRecordsAdminMixin

from .models import Person


@admin.register(Person)
class PersonAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("full_name", "relationship", "is_deleted")
    list_filter = ("is_deleted", "relationship")
    search_fields = ("full_name",)
