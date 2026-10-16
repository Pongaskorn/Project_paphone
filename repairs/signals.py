from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import TicketPhoto


@receiver(post_delete, sender=TicketPhoto)
def delete_photo_file(sender, instance, **kwargs):
    """ลบงานซ่อม/รูปแล้ว ไฟล์รูปบนดิสก์ต้องหายไปด้วย"""
    if instance.image:
        instance.image.delete(save=False)
