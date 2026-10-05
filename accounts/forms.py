from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User
from .utils import normalize_phone

INPUT = (
    "w-full px-4 py-3 rounded-xl border border-gray-300 bg-gray-50 "
    "focus:bg-white focus:ring-2 focus:ring-red-500 outline-none transition"
)


class PortalAuthenticationForm(AuthenticationForm):
    """ฟอร์ม login ที่จำกัดว่าหน้านี้รับ role ไหนได้บ้าง"""

    def __init__(self, *args, allowed_roles=(), portal_label="", **kwargs):
        self.allowed_roles = allowed_roles
        self.portal_label = portal_label
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "ชื่อผู้ใช้"
        self.fields["password"].label = "รหัสผ่าน"
        self.fields["username"].widget.attrs.update(
            {"class": INPUT, "placeholder": "ชื่อผู้ใช้", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update(
            {"class": INPUT, "placeholder": "รหัสผ่าน"}
        )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.role not in self.allowed_roles:
            raise forms.ValidationError(
                f"บัญชีนี้ไม่สามารถเข้าสู่ระบบจากหน้า{self.portal_label}ได้ "
                "กรุณาเลือกหน้าเข้าสู่ระบบให้ตรงกับประเภทบัญชี",
                code="wrong_portal",
            )


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "ชื่อผู้ใช้"
        self.fields["first_name"].label = "ชื่อ"
        self.fields["last_name"].label = "นามสกุล"
        self.fields["phone"].label = "เบอร์โทรศัพท์"
        self.fields["password1"].label = "รหัสผ่าน"
        self.fields["password2"].label = "ยืนยันรหัสผ่าน"
        self.fields["first_name"].required = True
        self.fields["phone"].required = True
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT
        self.fields["phone"].widget.attrs.update({"type": "tel", "placeholder": "062-630-3184"})

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not 9 <= len(phone) <= 10:
            raise forms.ValidationError("กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (9-10 หลัก)")
        return phone
