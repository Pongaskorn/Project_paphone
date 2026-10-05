from django.core.management.base import BaseCommand

from inventory.models import Part
from inventory.services import receive_stock

# (sku, ชื่อ, หมวด, รุ่นที่ใช้ได้, ทุน, ขาย, จำนวน, จุดสั่งซื้อ, ตำแหน่ง)
DEMO = [
    ("SCR-IP13-01", "จอ iPhone 13 (OEM)", "screen", "iPhone 13", 1800, 2800, 5, 2, "A1"),
    ("SCR-IP11-01", "จอ iPhone 11 (OEM)", "screen", "iPhone 11", 1100, 1900, 1, 2, "A1"),
    ("SCR-SS24-01", "จอ Samsung S24 แท้", "screen", "Samsung S24", 4200, 5900, 0, 1, "A2"),
    ("BAT-IP13-01", "แบตเตอรี่ iPhone 13", "battery", "iPhone 13", 450, 900, 8, 3, "B1"),
    ("BAT-IP11-01", "แบตเตอรี่ iPhone 11", "battery", "iPhone 11", 380, 800, 3, 3, "B1"),
    ("BAT-RM-01", "แบตเตอรี่ Redmi Note 12", "battery", "Redmi Note 12", 300, 650, 6, 2, "B2"),
    ("PRT-TC-01", "แพรชาร์จ Type-C (Samsung A series)", "port", "Samsung A14, A34, A54", 120, 350, 10, 3, "C1"),
    ("CAM-IP13-01", "กล้องหลัง iPhone 13", "camera", "iPhone 13", 900, 1600, 2, 2, "C2"),
    ("SPK-IP12-01", "ลำโพงล่าง iPhone 12", "speaker", "iPhone 12", 150, 400, 7, 2, "D1"),
]


class Command(BaseCommand):
    help = "เพิ่มอะไหล่ตัวอย่าง (ทำเฉพาะตอนที่ตารางอะไหล่ยังว่าง)"

    def handle(self, *args, **options):
        if Part.objects.exists():
            self.stdout.write("มีอะไหล่อยู่แล้ว ข้ามการ seed")
            return
        for sku, name, cat, models_, cost, sell, qty, min_q, loc in DEMO:
            part = Part.objects.create(
                sku=sku, name=name, category=cat, compatible_models=models_,
                cost_price=cost, sell_price=sell, min_quantity=min_q, location=loc,
            )
            if qty:
                receive_stock(part, qty, note="ยอดยกมา")
        self.stdout.write(self.style.SUCCESS(f"เพิ่มอะไหล่ตัวอย่าง {len(DEMO)} รายการ"))
