"""Request ID tracking and friendly handling of expected errors."""
import logging
import uuid

from django.shortcuts import render

from .exceptions import SarthiError
from .logging_utils import request_id_var

logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """Gives every request a short ID, used in logs and the X-Request-ID header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex[:12]
        request.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = request_id
        return response


class SarthiErrorMiddleware:
    """Shows a friendly page when a SarthiError escapes a normal web page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, SarthiError):
            logger.warning("%s: %s", type(exception).__name__, exception.message)
            return render(
                request,
                "errors/sarthi_error.html",
                {"message": exception.message,
                 "request_id": getattr(request, "request_id", "")},
                status=exception.status_code,
            )
        return None
