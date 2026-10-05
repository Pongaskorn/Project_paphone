from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.part_list, name="list"),
    path("new/", views.part_create, name="create"),
    path("<int:pk>/", views.part_detail, name="detail"),
    path("<int:pk>/edit/", views.part_edit, name="edit"),
    path("<int:pk>/receive/", views.part_receive, name="receive"),
    path("<int:pk>/adjust/", views.part_adjust, name="adjust"),
    path("<int:pk>/toggle/", views.part_toggle, name="toggle"),
    # ใช้อะไหล่ในงานซ่อม
    path("tickets/<int:ticket_pk>/add-part/", views.ticket_add_part, name="ticket_add_part"),
    path("tickets/<int:ticket_pk>/parts/<int:pk>/remove/", views.ticket_remove_part, name="ticket_remove_part"),
]
