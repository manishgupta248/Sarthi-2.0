import re

from django.db import models
from django.db.models import Q

from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Institution(BaseModel):
    """A bank, post office, broker or scheme provider. Added once, reused by accounts."""

    class Kind(models.TextChoices):
        BANK = "bank", "Bank"
        POST_OFFICE = "post_office", "Post Office"
        BROKER = "broker", "Broker or Depository"
        GOVERNMENT = "government", "Government scheme"
        EMPLOYER = "employer", "Employer or EPFO"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.BANK)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AccountType(BaseModel):
    """Editable list (Savings, PPF, NPS, ...). Add more from the admin site."""

    name = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Account(BaseModel):
    holder = models.ForeignKey(
        "family.Person", on_delete=models.PROTECT, related_name="accounts"
    )
    joint_holders = models.ManyToManyField(
        "family.Person", blank=True, related_name="joint_accounts"
    )
    nominee = models.ForeignKey(
        "family.Person", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="nominee_accounts",
    )
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT, related_name="accounts")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="accounts")

    # Shown in lists and the audit log, so it must never contain account numbers.
    nickname = models.CharField(max_length=120, blank=True)
    account_number = EncryptedTextField(blank=True)
    account_number_last4 = models.CharField(max_length=4, blank=True, editable=False)
    ifsc_code = models.CharField(max_length=11, blank=True)
    customer_id = EncryptedTextField(blank=True)
    branch = models.CharField(max_length=120, blank=True)
    opening_date = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    closed_on = models.DateField(null=True, blank=True)
    remarks = EncryptedTextField(blank=True)
    documents = models.ManyToManyField("vault.Document", blank=True, related_name="accounts")

    class Meta:
        ordering = ["holder__full_name", "institution__name", "id"]

    @property
    def display_name(self):
        return self.nickname or f"{self.institution.name} {self.account_type.name}"

    def __str__(self):
        return f"{self.display_name} ({self.holder.full_name})"

    def save(self, *args, **kwargs):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", self.account_number or "")
        self.account_number_last4 = cleaned[-4:]
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "account_number" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["account_number_last4"]
        super().save(*args, **kwargs)


class BalanceSnapshot(BaseModel):
    """'On this date, this account held this amount' (rupees)."""

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="snapshots")
    as_of = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-as_of", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "as_of"],
                condition=Q(is_deleted=False),
                name="one_active_snapshot_per_account_per_day",
            )
        ]

    def __str__(self):
        return f"{self.account.display_name} on {self.as_of}"
