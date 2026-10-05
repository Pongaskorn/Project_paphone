from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import PortalAuthenticationForm, RegisterForm
from .models import User

Role = User.Role

# หน้า login 3 แบบ ใช้ view เดียวกัน ต่างกันที่การตั้งค่า
PORTALS = {
    "member": {
        "roles": [Role.USER],
        "label": "สมาชิก",
        "title": "เข้าสู่ระบบสมาชิก",
        "subtitle": "เข้าสู่ระบบเพื่อแจ้งซ่อมและติดตามสถานะ",
        "icon": "smartphone",
        "staff": False,
    },
    "technician": {
        "roles": [Role.TECHNICIAN],
        "label": "ช่าง",
        "title": "เข้าสู่ระบบช่าง",
        "subtitle": "เฉพาะช่างซ่อมของร้านเท่านั้น",
        "icon": "wrench",
        "staff": True,
    },
    "admin": {
        "roles": [Role.ADMIN, Role.OWNER],
        "label": "ผู้ดูแลระบบ/เจ้าของร้าน",
        "title": "เข้าสู่ระบบผู้ดูแลระบบ",
        "subtitle": "สำหรับผู้ดูแลระบบและเจ้าของร้าน",
        "icon": "shield",
        "staff": True,
    },
}


def landing_url(user):
    if user.role == Role.TECHNICIAN:
        return reverse("tech:dashboard")
    if user.role in (Role.OWNER, Role.ADMIN):
        return reverse("dashboard:manage")
    return reverse("home")


def portal_login(request, portal):
    cfg = PORTALS[portal]
    if request.user.is_authenticated:
        return redirect(landing_url(request.user))

    form = PortalAuthenticationForm(
        request,
        data=request.POST or None,
        allowed_roles=cfg["roles"],
        portal_label=cfg["label"],
    )
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
            return redirect(nxt)
        return redirect(landing_url(user))
    return render(request, "accounts/login.html", {"form": form, "cfg": cfg, "next": nxt})


def register(request):
    if request.user.is_authenticated:
        return redirect(landing_url(request.user))
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()  # role เป็น "user" เสมอ (ค่า default) สมัครเองเลือก role ไม่ได้
        login(request, user)
        messages.success(request, "สมัครสมาชิกสำเร็จ ยินดีต้อนรับสู่ PAPhone!")
        return redirect("home")
    return render(request, "accounts/register.html", {"form": form})
