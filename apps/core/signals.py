"""Automatic audit trail: records who did what, never the sensitive values."""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .audit import log_event
from .models import AuditLog, BaseModel

IGNORED_FIELDS = {"last_login", "updated_at"}
EXTRA_AUDITED_MODELS = {"accounts.User"}


def _is_audited(instance):
    return isinstance(instance, BaseModel) or instance._meta.label in EXTRA_AUDITED_MODELS


def _describe(instance):
    try:
        return str(instance)[:200]
    except Exception:
        return "(unprintable)"


@receiver(pre_save)
def remember_changes(sender, instance, raw=False, **kwargs):
    if raw or not _is_audited(instance):
        return
    instance._audit_changed = []
    if instance.pk is None or instance._state.adding:
        return
    old = sender._base_manager.filter(pk=instance.pk).first()
    if old is None:
        return
    changed = []
    for field in instance._meta.concrete_fields:
        if field.name in IGNORED_FIELDS:
            continue
        if getattr(old, field.attname) != getattr(instance, field.attname):
            changed.append(field.name)
    instance._audit_changed = changed


@receiver(post_save)
def audit_save(sender, instance, created, raw=False, **kwargs):
    if raw or not _is_audited(instance):
        return
    if created:
        action, changed = AuditLog.Action.CREATE, []
    else:
        changed = getattr(instance, "_audit_changed", [])
        if not changed:
            return
        action = AuditLog.Action.UPDATE
        if "is_deleted" in changed and getattr(instance, "is_deleted", False):
            action = AuditLog.Action.DELETE
    log_event(
        action,
        model_label=instance._meta.label,
        object_id=instance.pk,
        object_repr=_describe(instance),
        changed_fields=changed,
    )


@receiver(post_delete)
def audit_hard_delete(sender, instance, **kwargs):
    if not _is_audited(instance):
        return
    log_event(
        AuditLog.Action.HARD_DELETE,
        model_label=instance._meta.label,
        object_id=instance.pk,
        object_repr=_describe(instance),
    )


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    log_event(AuditLog.Action.LOGIN, user=user)


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    log_event(AuditLog.Action.LOGOUT, user=user)


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, request=None, **kwargs):
    attempted = str(credentials.get("username", ""))[:50]
    log_event(AuditLog.Action.LOGIN_FAILED, note=f"Username tried: {attempted}")
