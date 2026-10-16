from django.conf import settings
from django.db import models
from django.utils import timezone


class Transaction(models.Model):
    """รายการบัญชี 1 แถว = รายรับหรือรายจ่าย 1 รายการ"""

    class Type(models.TextChoices):
        INCOME = "income", "รายรับ"
        EXPENSE = "expense", "รายจ่าย"

    class Category(models.TextChoices):
        # รายรับ
        REPAIR = "repair", "ค่าซ่อม"
        SALE = "sale", "ขายสินค้า/อุปกรณ์เสริม"
        OTHER_IN = "other_in", "รายรับอื่นๆ"
        # รายจ่าย
        PARTS = "parts", "ซื้ออะไหล่/สินค้า"
        RENT = "rent", "ค่าเช่าที่"
        UTILITIES = "utilities", "ค่าน้ำ/ไฟ/อินเทอร์เน็ต"
        SALARY = "salary", "ค่าแรง/เงินเดือน"
        TOOLS = "tools", "เครื่องมือ/อุปกรณ์ร้าน"
        OTHER_OUT = "other_out", "รายจ่ายอื่นๆ"

    # หมวดไหนเป็นรายรับ ที่เหลือเป็นรายจ่าย (ประเภทของรายการดูจากหมวดเสมอ จึงไม่มีทางไม่ตรงกัน)
    INCOME_CATEGORIES = (Category.REPAIR, Category.SALE, Category.OTHER_IN)
    EXPENSE_CATEGORIES = (
        Category.PARTS, Category.RENT, Category.UTILITIES,
        Category.SALARY, Category.TOOLS, Category.OTHER_OUT,
    )

    class Source(models.TextChoices):
        MANUAL = "manual", "บันทึกเอง"
        STOCK = "stock", "รับอะไหล่เข้าสต็อก"

    type = models.CharField("ประเภท", max_length=10, choices=Type.choices, db_index=True)
    category = models.CharField("หมวดหมู่", max_length=20, choices=Category.choices)
    amount = models.DecimalField("จำนวนเงิน (บาท)", max_digits=10, decimal_places=2)
    date = models.DateField("วันที่", default=timezone.localdate, db_index=True)
    description = models.CharField("รายละเอียด", max_length=200, blank=True)
    ticket = models.ForeignKey(
        "repairs.RepairTicket", null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions"
    )
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]

    @property
    def is_income(self):
        return self.type == self.Type.INCOME

    # ชื่อ class ของ Tailwind (models.py ถูกสแกนโดย tailwind.config.js)
    @property
    def badge_class(self):
        return "bg-green-100 text-green-700" if self.is_income else "bg-red-100 text-red-700"

    @property
    def amount_class(self):
        return "text-green-600" if self.is_income else "text-red-600"

    def __str__(self):
        return f"{self.date} {self.get_type_display()} {self.amount}"
