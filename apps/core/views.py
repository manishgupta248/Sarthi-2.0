import logging

from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health(request):
    """Tiny status page: is Sarthi alive and can it reach its database?"""
    status = {"app": "ok", "version": settings.SARTHI_VERSION}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["database"] = "ok"
    except Exception:
        logger.exception("Health check: database failed")
        status["database"] = "error"
        return JsonResponse(status, status=503)
    return JsonResponse(status)
