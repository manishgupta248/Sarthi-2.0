"""The sidebar menu. Every app adds its own entries here; the core never changes."""
from dataclasses import dataclass


@dataclass(frozen=True)
class MenuItem:
    title: str
    url_name: str
    icon: str = "bi-circle"
    order: int = 100
    section: str = "Apps"
    staff_only: bool = False


_registry = []


def register_menu(title, url_name, icon="bi-circle", order=100,
                  section="Apps", staff_only=False):
    item = MenuItem(title, url_name, icon, order, section, staff_only)
    if item not in _registry:
        _registry.append(item)


def get_menu_items():
    return list(_registry)


@dataclass(frozen=True)
class DashboardWidget:
    template: str
    provider: object
    order: int = 100
    staff_only: bool = False


_widgets = []


def register_dashboard_widget(template, provider, order=100, staff_only=False):
    """An app calls this to show a summary card on the home dashboard."""
    widget = DashboardWidget(template, provider, order, staff_only)
    if widget not in _widgets:
        _widgets.append(widget)


def collect_dashboard_widgets(request):
    import logging

    user = getattr(request, "user", None)
    is_staff = bool(user is not None and user.is_authenticated and user.is_staff)
    cards = []
    for widget in sorted(_widgets, key=lambda item: (item.order, item.template)):
        if widget.staff_only and not is_staff:
            continue
        try:
            data = widget.provider(request)
        except Exception:
            logging.getLogger(__name__).exception("Dashboard widget failed: %s", widget.template)
            continue
        cards.append({"template": widget.template, "data": data})
    return cards
