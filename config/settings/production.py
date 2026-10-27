"""Production settings (the stable copy on main)."""
from .base import *  # noqa: F401,F403

DEBUG = False

# Set HTTPS_ONLY=True in .env only when Sarthi is served over HTTPS.
HTTPS_ONLY = env.bool("HTTPS_ONLY", default=False)

if HTTPS_ONLY:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
