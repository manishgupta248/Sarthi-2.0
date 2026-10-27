"""Base building blocks every future Sarthi data model should use."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    """Default manager: hides soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    """Adds created/updated times and soft delete (nothing is lost by accident).

    Use Model.all_objects to see deleted records too.
    Use hard_delete() only for deliberate permanent removal.
    Changes to these models are written to the audit trail automatically.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class AuditLog(models.Model):
    """One line in the audit trail. Stores field NAMES only, never values."""

    class Action(models.TextChoices):
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        DELETE = "delete", "Deleted (soft)"
        HARD_DELETE = "hard_delete", "Permanently deleted"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        LOGIN_FAILED = "login_failed", "Login failed"
        BACKUP = "backup", "Backup created"
        RESTORE = "restore", "Backup restored"
        DOWNLOAD = "download", "Document downloaded"
        REVEAL = "reveal", "Value revealed"
        EXPORT = "export", "Data exported"
        OTHER = "other", "Other"

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    model_label = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    request_id = models.CharField(max_length=20, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.username} {self.action}"

    def save(self, *args, **kwargs):
        if self.pk is not None and not self._state.adding:
            raise PermissionError("Audit log entries cannot be changed.")
        super().save(*args, **kwargs)


