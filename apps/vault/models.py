from django.conf import settings
from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Document(BaseModel):
    """Details about one stored file. The file itself lives encrypted in data/vault/."""

    class DocType(models.TextChoices):
        BANK = "bank", "Bank"
        IDENTITY = "identity", "Identity"
        INSURANCE = "insurance", "Insurance"
        INVESTMENT = "investment", "Investment"
        TAX = "tax", "Tax"
        PROPERTY = "property", "Property"
        HEALTH = "health", "Health"
        OTHER = "other", "Other"

    # The title is shown in lists and the audit log: never put account numbers in it.
    title = models.CharField(max_length=200)
    doc_type = models.CharField(max_length=20, choices=DocType.choices, default=DocType.OTHER)
    person = models.ForeignKey(
        "family.Person", null=True, blank=True,
        on_delete=models.PROTECT, related_name="documents",
    )
    notes = EncryptedTextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    original_name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    stored_path = models.CharField(max_length=100, unique=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
