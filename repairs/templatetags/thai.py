from datetime import datetime

from django import template
from django.utils import timezone

register = template.Library()

MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


@register.filter
def thai_date(value, arg=""):
    """แสดงวันที่แบบ พ.ศ. เช่น 5 ต.ค. 2569  (ใส่ :"time" เพื่อแสดงเวลาด้วย)"""
    if not value:
        return "-"
    if isinstance(value, datetime) and timezone.is_aware(value):
        value = timezone.localtime(value)
    text = f"{value.day} {MONTHS[value.month - 1]} {value.year + 543}"
    if arg == "time":
        text += f" {value:%H:%M}"
    return text
