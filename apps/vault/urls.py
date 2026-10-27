from django.urls import path

from . import views

urlpatterns = [
    path("", views.document_list, name="vault_list"),
    path("upload/", views.document_upload, name="vault_upload"),
    path("<int:pk>/edit/", views.document_edit, name="vault_edit"),
    path("<int:pk>/download/", views.document_download, name="vault_download"),
    path("<int:pk>/delete/", views.document_delete, name="vault_delete"),
]
