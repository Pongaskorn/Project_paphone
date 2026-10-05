from django.core.management.base import BaseCommand

from shop.models import Product

DEMO = [
    ("สายชาร์จ Fast Charge (Type-C)", "charger", 290, "zap", "ชาร์จไว ไม่ร้อน จ่ายไฟเสถียร"),
    ("สายชาร์จ Lightning แท้", "charger", 590, "zap", "สำหรับ iPhone/iPad มาตรฐาน MFi"),
    ("หูฟัง Bluetooth True Wireless", "audio", 1290, "headphones", "เสียงดี เบสแน่น ตัดเสียงรบกวน"),
    ("หูฟังแบบสาย EarPods", "audio", 450, "headphones", "เสียงใส ใส่สบาย ไมค์ชัด"),
    ("เคสกันกระแทก Military Grade", "case", 390, "shield", "ปกป้องรอบตัวเครื่อง ตกไม่แตก"),
    ("ฟิล์มกระจกนิรภัย 9H", "case", 199, "smartphone", "กันรอยขีดข่วน ทัชลื่น ภาพชัด"),
    ("หัวชาร์จ Adapter 20W", "charger", 490, "zap", "หัวชาร์จเร็ว ขนาดกะทัดรัด"),
    ("ลำโพง Bluetooth พกพา", "audio", 890, "speaker", "กันน้ำได้ เสียงดังฟังชัด แบตอึด"),
]


class Command(BaseCommand):
    help = "เพิ่มสินค้าตัวอย่าง (ทำเฉพาะตอนที่ตารางสินค้ายังว่าง)"

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("มีสินค้าอยู่แล้ว ข้ามการ seed")
            return
        Product.objects.bulk_create(
            Product(name=n, category=c, price=p, icon=i, description=d)
            for n, c, p, i, d in DEMO
        )
        self.stdout.write(self.style.SUCCESS(f"เพิ่มสินค้าตัวอย่าง {len(DEMO)} รายการ"))
