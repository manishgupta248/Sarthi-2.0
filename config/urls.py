from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.dashboard, name="dashboard"),
    path("accounts/login/",
         auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("system/backups/", core_views.backups_page, name="backups"),
    path("system/audit/", core_views.audit_page, name="audit"),
    path("health/", core_views.health, name="health"),
    path("admin/", admin.site.urls),
]
