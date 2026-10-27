from django.contrib import admin

from apps.core.admin_utils import AllRecordsAdminMixin

from .models import Document


@admin.register(Document)
class DocumentAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("title", "doc_type", "person", "expiry_date", "is_deleted")
    list_filter = ("is_deleted", "doc_type")
    search_fields = ("title",)
    readonly_fields = ("original_name", "content_type", "size_bytes", "sha256",
                       "stored_path", "uploaded_by")

    def has_add_permission(self, request):
        return False  # uploads go through the Vault page so files are validated and encrypted

    def has_delete_permission(self, request, obj=None):
        return False
