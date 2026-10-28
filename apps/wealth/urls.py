from django.urls import path

from . import views, views_attachments

urlpatterns = [
    path("", views.wealth_dashboard, name="wealth_dashboard"),
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/add/", views.account_edit, name="account_add"),
    path("accounts/<int:pk>/", views.account_detail, name="account_detail"),
    path("accounts/<int:pk>/edit/", views.account_edit, name="account_edit"),
    path("accounts/<int:pk>/delete/", views.account_delete, name="account_delete"),
    path("accounts/<int:pk>/reveal/", views.account_reveal, name="account_reveal"),
    path("accounts/<int:pk>/snapshots/add/", views.snapshot_add, name="snapshot_add"),
    path("accounts/<int:pk>/remarks/add/", views_attachments.remark_add, name="remark_add"),
    path("remarks/<int:pk>/delete/", views_attachments.remark_delete, name="remark_delete"),
    path("accounts/<int:pk>/documents/upload/",
         views_attachments.account_document_upload, name="account_document_upload"),
    path("accounts/<int:pk>/documents/<int:doc_pk>/unlink/",
         views_attachments.account_document_unlink, name="account_document_unlink"),
    path("snapshots/<int:pk>/edit/", views.snapshot_edit, name="snapshot_edit"),
    path("snapshots/<int:pk>/delete/", views.snapshot_delete, name="snapshot_delete"),
    path("balances/update/", views.update_balances, name="update_balances"),
    path("institutions/", views.institution_list, name="institution_list"),
    path("institutions/add/", views.institution_edit, name="institution_add"),
    path("institutions/<int:pk>/edit/", views.institution_edit, name="institution_edit"),
    path("institutions/<int:pk>/delete/", views.institution_delete, name="institution_delete"),
    path("export/", views.export_accounts, name="export_accounts"),
]
