from django.apps import AppConfig


class FamilyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.family"
    label = "family"

    def ready(self):
        from apps.core.navigation import register_menu

        register_menu("Family", "family_list", icon="bi-people", order=5,
                      section="Records", staff_only=True)
