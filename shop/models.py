from django.db import models


class Product(models.Model):
    class Category(models.TextChoices):
        CHARGER = "charger", "ชาร์จไฟ"
        AUDIO = "audio", "หูฟัง"
        CASE = "case", "เคส/ฟิล์ม"

    name = models.CharField("ชื่อสินค้า", max_length=150)
    category = models.CharField("หมวดหมู่", max_length=20, choices=Category.choices)
    price = models.DecimalField("ราคา (บาท)", max_digits=8, decimal_places=2)
    description = models.CharField("คำอธิบายสั้น", max_length=200, blank=True)
    icon = models.CharField(
        "ไอคอน (ชื่อจาก lucide.dev)",
        max_length=50,
        default="package",
        help_text="เช่น zap, headphones, shield, smartphone, speaker",
    )
    is_active = models.BooleanField("แสดงในหน้าร้าน", default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name
