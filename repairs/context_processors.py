from .models import Notification
from .services import STAFF_ROLES


def notifications(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and user.role in STAFF_ROLES:
        return {"unread_count": Notification.objects.filter(recipient=user, is_read=False).count()}
    return {}
