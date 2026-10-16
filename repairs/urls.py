from django.urls import path

from . import views

app_name = "repairs"

urlpatterns = [
    path("new/", views.booking, name="new"),
    path("status/", views.status, name="status"),
    path("photo/<int:pk>/", views.photo, name="photo"),
]
