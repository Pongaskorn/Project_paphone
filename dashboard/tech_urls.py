from django.urls import path

from . import tech_views as v

app_name = "tech"

urlpatterns = [
    path("", v.dashboard, name="dashboard"),
    path("tickets/new/", v.ticket_create, name="create"),
    path("tickets/<int:pk>/", v.ticket_detail, name="detail"),
    path("tickets/<int:pk>/edit/", v.ticket_edit, name="edit"),
    path("tickets/<int:pk>/delete/", v.ticket_delete, name="delete"),
    path("notifications/", v.notifications, name="notifications"),
    path("notifications/<int:pk>/open/", v.notification_open, name="notification_open"),
]
