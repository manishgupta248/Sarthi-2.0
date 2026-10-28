from django.contrib import admin

from apps.core.admin_utils import AllRecordsAdminMixin

from .models import Account, AccountType, BalanceSnapshot, Institution


@admin.register(AccountType)
class AccountTypeAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "sort_order", "is_deleted")
    list_filter = ("is_deleted",)


@admin.register(Institution)
class InstitutionAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "kind", "is_deleted")
    list_filter = ("is_deleted", "kind")
    search_fields = ("name",)


@admin.register(Account)
class AccountAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "account_type", "is_closed", "is_deleted")
    list_filter = ("is_deleted", "is_closed", "account_type")
    # Numbers are deliberately not editable here: use the Accounts pages (audited Reveal).
    exclude = ("account_number", "customer_id")


@admin.register(BalanceSnapshot)
class BalanceSnapshotAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("account", "as_of", "amount", "is_deleted")
    list_filter = ("is_deleted",)


from .models import AccountRemark  # noqa: E402


@admin.register(AccountRemark)
class AccountRemarkAdmin(AllRecordsAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "created_at", "is_deleted")
    list_filter = ("is_deleted",)
    exclude = ("text",)  # remarks are read on the account page
