# PhoneFix - ระบบร้านซ่อมมือถือ (Django + MySQL + Tailwind + Docker)

## เริ่มใช้งาน
1. `cp .env.example .env`   (Windows: `copy .env.example .env`)
2. สร้าง migration (ทำครั้งแรก และทุกครั้งที่แก้ models):
   `docker compose run --rm web python manage.py makemigrations accounts repairs shop inventory`
3. `docker compose up --build`
4. สร้างบัญชีทดลอง (รหัสผ่านทุกบัญชี `demo1234`):
   `docker compose exec web python manage.py seed_demo_users`

## บัญชีทดลอง
| username | บทบาท | หน้า login |
|---|---|---|
| member1 | สมาชิก | /login/ |
| tech1 | ช่าง | /tech-login/ |
| owner1 | เจ้าของร้าน | /admin-login/ |
| admin1 | ผู้ดูแลระบบ | /admin-login/ |

บัญชีช่าง/เจ้าของร้านจริง สร้างได้ที่ `/django-admin/` (ต้อง login ด้วย admin1)

## หน้าทั้งหมด
- สาธารณะ: `/`, `/shop/`, `/login/`, `/register/`, `/tech-login/`, `/admin-login/`
- สมาชิก: `/repair/new/`, `/repair/status/`
- ช่าง: `/tech/` (รายการงาน), `/tech/tickets/<id>/` (รายละเอียด/แจ้งสถานะ), `/tech/tickets/new/`, `/tech/notifications/`
- เจ้าของร้าน/ผู้ดูแล: `/manage/`, และเปิดหน้าของช่างได้ด้วย

## ระบบสต็อกอะไหล่ (`/stock/`)
- ทุกบทบาทพนักงาน (ช่าง/เจ้าของ/ผู้ดูแล): ดูรายการ ค้นหา กรองใกล้หมด ดูประวัติ และ**ใช้อะไหล่ในงานซ่อม**ที่หน้า `/tech/tickets/<id>/` (ตัดสต็อกอัตโนมัติ)
- เจ้าของร้าน/ผู้ดูแล: เพิ่ม/แก้ไขอะไหล่ รับเข้าสต็อก ปรับยอดตรวจนับ เปิด-ปิดใช้งาน และเห็นราคาทุน/มูลค่าสต็อก
- ทุกการเปลี่ยนยอดบันทึกใน `StockMovement` (ใคร/เมื่อไหร่/เท่าไหร่/งานไหน)
- อะไหล่เหลือ ≤ จุดสั่งซื้อ -> แจ้งเตือนเจ้าของร้านในหน้าแจ้งเตือน
- ลบงานซ่อม -> คืนอะไหล่เข้าสต็อกอัตโนมัติ
- ข้อมูลตัวอย่าง: `docker compose exec web python manage.py seed_parts`
