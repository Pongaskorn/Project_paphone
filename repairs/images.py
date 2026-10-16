"""จัดการรูปที่ลูกค้าอัปโหลด: ย่อขนาด หมุนให้ตรง และตัด EXIF (รวมพิกัด GPS) ทิ้ง"""
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_SIDE = 1600  # ด้านที่ยาวที่สุดไม่เกิน 1600 px พอสำหรับดูอาการเสียให้ชัด


def optimize_image(uploaded):
    """รับไฟล์ที่ผ่านการตรวจแล้ว คืน ContentFile (JPEG) ที่พร้อมบันทึก"""
    uploaded.seek(0)
    img = Image.open(uploaded)
    img = ImageOps.exif_transpose(img)  # รูปจากมือถือมักเก็บทิศทางไว้ใน EXIF
    if img.mode not in ("RGB", "L"):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))  # พื้นโปร่งใส -> ขาว
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = BytesIO()
    img.save(out, "JPEG", quality=85, optimize=True)  # บันทึกใหม่ = ไม่มี EXIF ติดไป
    return ContentFile(out.getvalue(), name="photo.jpg")
