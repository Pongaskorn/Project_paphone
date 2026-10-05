from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.portal_login, {"portal": "member"}, name="login"),
    path("tech-login/", views.portal_login, {"portal": "technician"}, name="tech_login"),
    path("admin-login/", views.portal_login, {"portal": "admin"}, name="admin_login"),
    path("register/", views.register, name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),  # ต้องเรียกแบบ POST
]
