from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self):
        from . import signals  # noqa: F401  (connects the audit trail)
        from .navigation import register_menu

        register_menu("Dashboard", "dashboard", icon="bi-speedometer2", order=0, section="Main")
        register_menu("Backups", "backups", icon="bi-hdd-stack", order=10,
                      section="System", staff_only=True)
        register_menu("Audit log", "audit", icon="bi-journal-text", order=20,
                      section="System", staff_only=True)
        register_menu("Admin site", "admin:index", icon="bi-gear", order=30,
                      section="System", staff_only=True)
