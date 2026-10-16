from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    path("", views.ledger, name="ledger"),
    path("export/", views.export_csv, name="export"),
    path("new/<slug:kind>/", views.transaction_create, name="create"),
    path("<int:pk>/edit/", views.transaction_edit, name="edit"),
    path("<int:pk>/delete/", views.transaction_delete, name="delete"),
]
