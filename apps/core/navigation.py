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
