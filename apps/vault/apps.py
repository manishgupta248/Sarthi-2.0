from django.apps import AppConfig


class VaultConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vault"
    label = "vault"

    def ready(self):
        from apps.core.navigation import register_menu

        register_menu("Document vault", "vault_list", icon="bi-safe", order=6,
                      section="Records", staff_only=True)
