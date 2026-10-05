from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.manage, name="manage"),
    path("tickets/<int:pk>/status/", views.update_status, name="update_status"),
    path("tickets/<int:pk>/delete/", views.delete_ticket, name="delete"),
]
