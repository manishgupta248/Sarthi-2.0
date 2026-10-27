from django.urls import path

from . import views

urlpatterns = [
    path("", views.person_list, name="family_list"),
    path("add/", views.person_edit, name="family_add"),
    path("<int:pk>/edit/", views.person_edit, name="family_edit"),
    path("<int:pk>/delete/", views.person_delete, name="family_delete"),
]
