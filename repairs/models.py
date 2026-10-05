from django.conf import settings
from django.db import models
from django.utils import timezone


class RepairTicket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "รอรับเรื่อง"
        REPAIRING = "repairing", "กำลังซ่อม"
        WAITING_PARTS = "waiting_parts", "รออะไหล่"
        COMPLETED = "completed", "เสร็จสิ้น"

    ticket_code = models.CharField(max_length=30, unique=True, null=True, blank=True, editable=False)
    # ยังไม่มีระบบ login จึงเว้นว่างไว้ก่อน (เฟสถัดไปจะผูกกับ User)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets",
    )
    customer_name = models.CharField("ชื่อลูกค้า", max_length=100)
    customer_phone = models.CharField("เบอร์โทรศัพท์", max_length=20)
    device_model = models.CharField("รุ่นมือถือ", max_length=100)
    symptom = models.TextField("อาการเสีย")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    note = models.TextField("หมายเหตุจากช่าง (ภายในร้าน)", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    # ชื่อ class ของ Tailwind (ไฟล์นี้ถูกสแกนโดย tailwind.config.js)
    _BADGE = {
        "new": "bg-yellow-100 text-yellow-700",
        "repairing": "bg-blue-100 text-blue-700",
        "waiting_parts": "bg-purple-100 text-purple-700",
        "completed": "bg-green-100 text-green-700",
    }
    _BAR = {
        "new": "bg-yellow-500",
        "repairing": "bg-blue-500",
        "waiting_parts": "bg-purple-500",
        "completed": "bg-green-500",
    }
    _PROGRESS = {"new": 25, "repairing": 50, "waiting_parts": 75, "completed": 100}

    @property
    def badge_class(self):
        return self._BADGE.get(self.status, "bg-gray-100 text-gray-700")

    @property
    def bar_class(self):
        return self._BAR.get(self.status, "bg-gray-400")

    @property
    def progress(self):
        return self._PROGRESS.get(self.status, 0)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.ticket_code:
            day = timezone.localtime(self.created_at).strftime("%Y%m%d")
            self.ticket_code = f"RP-{day}-{self.pk:04d}"
            type(self).objects.filter(pk=self.pk).update(ticket_code=self.ticket_code)

    def __str__(self):
        return f"{self.ticket_code or self.pk} - {self.device_model}"


class StatusLog(models.Model):
    """ประวัติการเปลี่ยนสถานะ / การรายงานของช่าง"""

    ticket = models.ForeignKey(RepairTicket, on_delete=models.CASCADE, related_name="logs")
    old_status = models.CharField(max_length=20, choices=RepairTicket.Status.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=RepairTicket.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="status_changes"
    )
    note = models.CharField("หมายเหตุ", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_id}: {self.old_status} -> {self.new_status}"


class Notification(models.Model):
    """การแจ้งเตือนในระบบ (ช่าง/เจ้าของร้าน/ผู้ดูแล)"""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    ticket = models.ForeignKey(
        RepairTicket, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
