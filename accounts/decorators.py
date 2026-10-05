from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url


def role_required(*roles, login_url=None):
    """ใช้: @role_required("owner", "admin", login_url="accounts:admin_login")

    - ยังไม่ login  -> ส่งไปหน้า login ที่กำหนด (หรือ LOGIN_URL)
    - login แล้วแต่ role ไม่ตรง -> 403
    """

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                target = resolve_url(login_url) if login_url else None
                return redirect_to_login(request.get_full_path(), target)
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
