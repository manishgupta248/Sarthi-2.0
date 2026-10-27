"""Sarthi's own error types and the clean API error format."""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

logger = logging.getLogger(__name__)


class SarthiError(Exception):
    """Base class for all expected (handled) Sarthi errors."""

    default_message = "Something went wrong."
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class ValidationFailed(SarthiError):
    default_message = "The information provided is not valid."
    status_code = status.HTTP_400_BAD_REQUEST


class RecordNotFound(SarthiError):
    default_message = "The requested record was not found."
    status_code = status.HTTP_404_NOT_FOUND


class AccessDenied(SarthiError):
    default_message = "You do not have permission to do this."
    status_code = status.HTTP_403_FORBIDDEN


class ExternalServiceError(SarthiError):
    """Google, Telegram, an LLM provider, etc. failed."""

    default_message = "An outside service is not responding. Please try again later."
    status_code = status.HTTP_502_BAD_GATEWAY


class ConfigurationError(SarthiError):
    default_message = "Sarthi is not configured correctly."
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


def api_exception_handler(exc, context):
    """Every API error leaves Sarthi in the same safe, clean shape."""
    if isinstance(exc, SarthiError):
        logger.warning("%s: %s", type(exc).__name__, exc.message)
        return Response(
            {"error": {"code": type(exc).__name__, "message": exc.message}},
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "code": "api_error",
                "message": "The request could not be completed.",
                "details": response.data,
            }
        }
        return response

    # Unknown error: log everything privately, show nothing sensitive.
    logger.error("Unhandled API error", exc_info=exc)
    set_rollback()
    return Response(
        {"error": {"code": "server_error",
                   "message": "An internal error occurred. It has been logged."}},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
