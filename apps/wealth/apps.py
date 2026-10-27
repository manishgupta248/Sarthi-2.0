from django.apps import AppConfig


class WealthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.wealth"
    label = "wealth"

    def ready(self):
        from apps.core.navigation import register_dashboard_widget, register_menu

        from .widgets import wealth_widget

        register_menu("Wealth dashboard", "wealth_dashboard", icon="bi-graph-up-arrow",
                      order=7, section="Wealth", staff_only=True)
        register_menu("Accounts", "account_list", icon="bi-bank",
                      order=8, section="Wealth", staff_only=True)
        register_menu("Update balances", "update_balances", icon="bi-pencil-square",
                      order=8, section="Wealth", staff_only=True)
        register_menu("Institutions", "institution_list", icon="bi-building",
                      order=9, section="Wealth", staff_only=True)
        register_dashboard_widget("wealth/_dashboard_widget.html", wealth_widget,
                                  order=10, staff_only=True)
