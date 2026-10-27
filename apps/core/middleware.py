"""Request ID tracking and friendly handling of expected errors."""
import logging
import uuid

from django.shortcuts import render

from .context import current_request_var
from .exceptions import SarthiError
from .logging_utils import request_id_var

logger = logging.getLogger(__name__)


class RequestIdMiddleware:
    """Gives every request a short ID and remembers the request for the audit trail."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex[:12]
        request.request_id = request_id
        id_token = request_id_var.set(request_id)
        request_token = current_request_var.set(request)
        try:
            response = self.get_response(request)
        finally:
            current_request_var.reset(request_token)
            request_id_var.reset(id_token)
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
