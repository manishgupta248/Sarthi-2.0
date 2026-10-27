import logging
from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .backup import create_backup, list_backups, verify_backup
from .exceptions import AccessDenied, SarthiError
from .models import AuditLog
from .navigation import collect_dashboard_widgets

logger = logging.getLogger(__name__)


def staff_required(view):
    """Logged-in administrators only."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise AccessDenied("This page is only for administrators.")
        return view(request, *args, **kwargs)

    return wrapper


def _database_ok():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        logger.exception("Database check failed")
        return False


def health(request):
    """Tiny status page: is Sarthi alive and can it reach its database?"""
    status = {"app": "ok", "version": settings.SARTHI_VERSION}
    if _database_ok():
        status["database"] = "ok"
        return JsonResponse(status)
    status["database"] = "error"
    return JsonResponse(status, status=503)


@login_required
def dashboard(request):
    context = {"db_ok": _database_ok()}
    if request.user.is_staff:
        backups = list_backups()
        latest = backups[0] if backups else None
        context.update({
            "latest_backup": latest,
            "backup_count": len(backups),
            "backup_warning": latest is None
            or (datetime.now() - latest["created"]) > timedelta(hours=48),
            "events_24h": AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).count(),
            "recent_events": AuditLog.objects.all()[:6],
        })
    context["widgets"] = collect_dashboard_widgets(request)
    return render(request, "core/dashboard.html", context)


@staff_required
def backups_page(request):
    if request.method == "POST":
        action = request.POST.get("do", "")
        try:
            if action == "create":
                result = create_backup(kind="manual")
                messages.success(request, f"Backup created: {result['name']}")
            elif action == "verify":
                info = verify_backup(request.POST.get("filename", ""))
                detail = f"{info['tables']} tables"
                if info["users"] is not None:
                    detail += f", {info['users']} user(s)"
                messages.success(
                    request, f"Verified {info['name']}: the backup is healthy ({detail})."
                )
        except SarthiError as exc:
            messages.error(request, exc.message)
        except Exception:
            logger.exception("Backup action failed")
            messages.error(request, "The backup action failed. Details are in the log.")
        return redirect("backups")
    return render(request, "core/backups.html", {
        "backups": list_backups(),
        "encrypted": bool(settings.BACKUP_ENCRYPTION_KEY),
        "copy_dir": settings.BACKUP_COPY_DIR,
    })


@staff_required
def audit_page(request):
    queryset = AuditLog.objects.all()
    selected = request.GET.get("action", "")
    if selected in dict(AuditLog.Action.choices):
        queryset = queryset.filter(action=selected)
    else:
        selected = ""
    page = Paginator(queryset, 50).get_page(request.GET.get("page"))
    return render(request, "core/audit.html", {
        "page": page,
        "actions": AuditLog.Action.choices,
        "selected_action": selected,
    })

