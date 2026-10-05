from django.core.management.base import BaseCommand

from accounts.models import User

PASSWORD = "demo1234"  # ใช้ตอนพัฒนาเท่านั้น! เปลี่ยนก่อนใช้งานจริง

DEMO = [
    ("member1", "สมชาย", "ใจดี", "0811111111", User.Role.USER),
    ("tech1", "ช่างเอก", "ซ่อมเก่ง", "0822222222", User.Role.TECHNICIAN),
    ("owner1", "เจ้าของ", "ร้านซ่อม", "0833333333", User.Role.OWNER),
    ("admin1", "ผู้ดูแล", "ระบบ", "0844444444", User.Role.ADMIN),
]


class Command(BaseCommand):
    help = "สร้างบัญชีทดลอง 4 บทบาท (รหัสผ่าน demo1234)"

    def handle(self, *args, **options):
        for username, first, last, phone, role in DEMO:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "phone": phone, "role": role},
            )
            if created:
                user.set_password(PASSWORD)
                if role == User.Role.ADMIN:
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f"สร้าง {username} ({role})"))
            else:
                self.stdout.write(f"มี {username} อยู่แล้ว ข้าม")
        self.stdout.write(f"รหัสผ่านทุกบัญชี: {PASSWORD}")
