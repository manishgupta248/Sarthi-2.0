"""One place to record an audit event."""
import logging

from .context import current_request_var
from .models import AuditLog

logger = logging.getLogger(__name__)


def log_event(action, *, user=None, note="", model_label="", object_id="",
              object_repr="", changed_fields=None):
    """Write an audit entry. A failure here must never break the real work."""
    try:
        request = current_request_var.get()
        if user is None and request is not None:
            candidate = getattr(request, "user", None)
            if candidate is not None and getattr(candidate, "is_authenticated", False):
                user = candidate
        if user is not None:
            username = user.get_username()
        else:
            username = "system" if request is None else "anonymous"
        AuditLog.objects.create(
            user=user if (user is not None and user.pk) else None,
            username=username[:150],
            action=action,
            model_label=model_label[:100],
            object_id=str(object_id)[:64],
            object_repr=str(object_repr)[:200],
            changed_fields=list(changed_fields or []),
            ip_address=request.META.get("REMOTE_ADDR") if request is not None else None,
            request_id=getattr(request, "request_id", "") if request is not None else "",
            note=str(note)[:255],
        )
    except Exception:
        logger.exception("Could not write audit log entry")
