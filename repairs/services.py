"""ตรรกะที่หลาย view ใช้ร่วมกัน: เปลี่ยนสถานะ + บันทึก log + ส่งแจ้งเตือน"""
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import User

from .models import Notification, RepairTicket, StatusLog

Role = User.Role
STAFF_ROLES = (Role.TECHNICIAN, Role.OWNER, Role.ADMIN)
MANAGER_ROLES = (Role.OWNER, Role.ADMIN)


def notify(roles, ticket, message, exclude=None):
    recipients = get_user_model().objects.filter(role__in=roles, is_active=True)
    if exclude is not None:
        recipients = recipients.exclude(pk=exclude.pk)
    Notification.objects.bulk_create(
        [Notification(recipient=u, ticket=ticket, message=message[:255]) for u in recipients]
    )


def announce_new_ticket(ticket, actor=None):
    """แจ้งเตือนเมื่อมีงานซ่อมใหม่"""
    if actor is None or actor.role == Role.USER:
        notify(
            (Role.TECHNICIAN, Role.OWNER),
            ticket,
            f"มีงานซ่อมใหม่ {ticket.ticket_code}: {ticket.device_model} ({ticket.customer_name})",
        )
    else:
        notify(MANAGER_ROLES, ticket, f"{actor} เพิ่มงานซ่อมใหม่ {ticket.ticket_code}", exclude=actor)


def record_status_change(ticket, old_status, new_status, actor, note=""):
    StatusLog.objects.create(
        ticket=ticket, old_status=old_status, new_status=new_status, changed_by=actor, note=note
    )
    # ช่างรายงานสถานะ -> แจ้งเจ้าของร้าน/ผู้ดูแล
    if actor is not None and actor.role == Role.TECHNICIAN:
        label = RepairTicket.Status(new_status).label
        text = f"ช่าง {actor} แจ้งสถานะงาน {ticket.ticket_code}: {label}"
        if note:
            text += f" ({note})"
        notify(MANAGER_ROLES, ticket, text, exclude=actor)


@transaction.atomic
def change_status(ticket, new_status, actor, note=""):
    """เปลี่ยนสถานะ (หรือบันทึกรายงานเฉพาะหมายเหตุ) พร้อม log และแจ้งเตือน"""
    old = ticket.status
    if new_status == old and not note:
        return False
    ticket.status = new_status
    ticket.save(update_fields=["status", "updated_at"])
    record_status_change(ticket, old, new_status, actor, note)
    return True
