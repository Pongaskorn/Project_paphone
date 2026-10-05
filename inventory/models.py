from django.conf import settings
from django.db import models


class Part(models.Model):
    """อะไหล่ในสต็อก"""

    class Category(models.TextChoices):
        SCREEN = "screen", "หน้าจอ"
        BATTERY = "battery", "แบตเตอรี่"
        PORT = "port", "ช่องชาร์จ/แพรชาร์จ"
        CAMERA = "camera", "กล้อง"
        SPEAKER = "speaker", "ลำโพง/ไมค์"
        BUTTON = "button", "ปุ่ม/แพรปุ่ม"
        OTHER = "other", "อื่นๆ"

    sku = models.CharField("รหัสอะไหล่", max_length=30, unique=True)
    name = models.CharField("ชื่ออะไหล่", max_length=150)
    category = models.CharField("หมวดหมู่", max_length=20, choices=Category.choices, default=Category.OTHER)
    compatible_models = models.CharField(
        "รุ่นที่ใช้ได้", max_length=200, blank=True, help_text="เช่น iPhone 13, iPhone 13 Pro"
    )
    cost_price = models.DecimalField("ราคาทุน (บาท)", max_digits=8, decimal_places=2, default=0)
    sell_price = models.DecimalField("ราคาขาย/ราคาที่คิดลูกค้า (บาท)", max_digits=8, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField("จำนวนคงเหลือ", default=0)
    min_quantity = models.PositiveIntegerField("จุดสั่งซื้อ (แจ้งเตือนเมื่อเหลือไม่เกิน)", default=2)
    location = models.CharField("ตำแหน่งจัดเก็บ", max_length=50, blank=True, help_text="เช่น ชั้น A2")
    is_active = models.BooleanField("เปิดใช้งาน", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def is_out(self):
        return self.quantity == 0

    @property
    def is_low(self):
        return 0 < self.quantity <= self.min_quantity

    # ชื่อ class ของ Tailwind (models.py ถูกสแกนโดย tailwind.config.js)
    @property
    def stock_label(self):
        if self.is_out:
            return "หมด"
        return "ใกล้หมด" if self.is_low else "ปกติ"

    @property
    def stock_badge(self):
        if self.is_out:
            return "bg-red-100 text-red-700"
        return "bg-amber-100 text-amber-700" if self.is_low else "bg-green-100 text-green-700"

    def __str__(self):
        return f"{self.sku} - {self.name}"


class StockMovement(models.Model):
    """ประวัติการเคลื่อนไหวสต็อกทุกครั้ง (ตรวจสอบย้อนหลังได้)"""

    class Type(models.TextChoices):
        IN = "in", "รับเข้า"
        OUT = "out", "ใช้ในงานซ่อม"
        RETURN = "return", "คืนเข้าสต็อก"
        ADJUST = "adjust", "ปรับยอด"

    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=Type.choices)
    change = models.IntegerField("จำนวนที่เปลี่ยน (+/-)")
    balance_after = models.PositiveIntegerField("คงเหลือหลังทำรายการ")
    ticket = models.ForeignKey(
        "repairs.RepairTicket", null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_movements"
    )
    note = models.CharField("หมายเหตุ", max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_movements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def badge_class(self):
        return {
            "in": "bg-green-100 text-green-700",
            "out": "bg-blue-100 text-blue-700",
            "return": "bg-purple-100 text-purple-700",
            "adjust": "bg-amber-100 text-amber-700",
        }.get(self.movement_type, "bg-gray-100 text-gray-700")

    def __str__(self):
        return f"{self.part_id} {self.change:+d}"


class TicketPart(models.Model):
    """อะไหล่ที่ใช้ในงานซ่อมแต่ละงาน"""

    ticket = models.ForeignKey("repairs.RepairTicket", on_delete=models.CASCADE, related_name="parts_used")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="ticket_usages")
    quantity = models.PositiveIntegerField("จำนวน")
    unit_price = models.DecimalField("ราคาต่อชิ้น (ตอนใช้)", max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [models.UniqueConstraint(fields=["ticket", "part"], name="uniq_ticket_part")]

    @property
    def total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.ticket_id}: {self.part} x{self.quantity}"
