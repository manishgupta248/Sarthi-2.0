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
        register_menu("Transactions", "transaction_list", icon="bi-arrow-left-right",
                      order=8, section="Wealth", staff_only=True)
        register_menu("Reports", "report_summary", icon="bi-bar-chart-line",
                      order=9, section="Wealth", staff_only=True)
        register_menu("Categories", "category_list", icon="bi-tags",
                      order=9, section="Wealth", staff_only=True)
        register_menu("Net worth", "networth_page", icon="bi-pie-chart",
                      order=7, section="Wealth", staff_only=True)
        register_menu("Update values", "update_values", icon="bi-pencil",
                      order=8, section="Wealth", staff_only=True)
        register_menu("Investments", "investment_list", icon="bi-piggy-bank",
                      order=9, section="Wealth", staff_only=True)
        register_menu("Liabilities", "liability_list", icon="bi-credit-card-2-front",
                      order=9, section="Wealth", staff_only=True)
        register_dashboard_widget("wealth/_dashboard_widget.html", wealth_widget,
                                  order=10, staff_only=True)



