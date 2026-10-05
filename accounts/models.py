from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "ลูกค้า"
        TECHNICIAN = "technician", "ช่าง"
        OWNER = "owner", "เจ้าของร้าน"
        ADMIN = "admin", "ผู้ดูแลระบบ"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    phone = models.CharField("เบอร์โทร", max_length=20, blank=True)

    def save(self, *args, **kwargs):
        # createsuperuser จะได้ role admin อัตโนมัติ
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_customer(self):
        return self.role == self.Role.USER

    @property
    def is_technician(self):
        return self.role == self.Role.TECHNICIAN

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username
