"""Holds the request currently being handled (used by the audit trail)."""
from contextvars import ContextVar

current_request_var = ContextVar("current_request", default=None)
