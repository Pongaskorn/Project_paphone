from django.db.models.signals import pre_delete
from django.dispatch import receiver

from repairs.models import RepairTicket

from .services import return_ticket_parts


@receiver(pre_delete, sender=RepairTicket)
def give_back_parts(sender, instance, **kwargs):
    """ลบงานซ่อมแล้ว อะไหล่ที่ตัดไปต้องกลับเข้าสต็อก"""
    return_ticket_parts(instance)
