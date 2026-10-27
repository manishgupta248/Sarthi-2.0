from django.conf import settings
from django.urls import NoReverseMatch, reverse

from .navigation import get_menu_items


def shell(request):
    """Builds the sidebar menu and shared page values for every template."""
    user = getattr(request, "user", None)
    is_staff = bool(user is not None and user.is_authenticated and user.is_staff)
    sections = {}
    for item in sorted(get_menu_items(), key=lambda i: (i.order, i.title)):
        if item.staff_only and not is_staff:
            continue
        try:
            url = reverse(item.url_name)
        except NoReverseMatch:
            continue
        if url == "/":
            active = request.path == "/"
        else:
            active = request.path.startswith(url)
        sections.setdefault(item.section, []).append(
            {"title": item.title, "url": url, "icon": item.icon, "active": active}
        )
    return {"menu_sections": sections, "sarthi_version": settings.SARTHI_VERSION}
