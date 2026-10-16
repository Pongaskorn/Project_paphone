from django.contrib import admin
from django.urls import include, path

from .views import home

urlpatterns = [
    path("", home, name="home"),
    path("", include("accounts.urls")),  # login / tech-login / admin-login / register / logout
    path("shop/", include("shop.urls")),
    path("repair/", include("repairs.urls")),
    path("stock/", include("inventory.urls")),  # สต็อกอะไหล่ (ช่าง/เจ้าของร้าน/ผู้ดูแล)
    path("accounting/", include("accounting.urls")),  # บัญชีร้าน (เจ้าของร้าน/ผู้ดูแล)
    path("manage/", include("dashboard.urls")),  # เจ้าของร้าน / ผู้ดูแล
    path("tech/", include("dashboard.tech_urls")),  # ช่าง
    path("django-admin/", admin.site.urls),  # หน้า admin ของ Django (ต้อง login superuser)
]
