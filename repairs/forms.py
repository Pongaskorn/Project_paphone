from django import forms

from accounts.utils import normalize_phone

from .models import RepairTicket

INPUT = (
    "w-full px-4 py-2.5 rounded-lg border border-gray-300 bg-gray-50 "
    "focus:bg-white focus:ring-2 focus:ring-red-500 outline-none transition"
)


class PhoneCleanMixin:
    def clean_customer_phone(self):
        phone = normalize_phone(self.cleaned_data["customer_phone"])
        if not 9 <= len(phone) <= 10:
            raise forms.ValidationError("กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (9-10 หลัก)")
        return phone


MIN_PHOTOS = 2
MAX_PHOTOS = 3
MAX_PHOTO_MB = 10
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """ช่องอัปโหลดรูปได้หลายไฟล์ (ตรวจว่าเป็นรูปจริงด้วย Pillow ทีละไฟล์)"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        clean_one = super().clean
        if isinstance(data, (list, tuple)):
            return [clean_one(d, initial) for d in data]
        return [clean_one(data, initial)] if data else []


class BookingForm(forms.ModelForm):
    """ฟอร์มแจ้งซ่อมของสมาชิก — ชื่อและเบอร์โทรดึงจากบัญชีที่ login (ไม่ให้กรอก)"""

    photos = MultipleImageField(
        label="รูปอาการเสีย",
        help_text=f"แนบรูป {MIN_PHOTOS}-{MAX_PHOTOS} รูป (JPG, PNG, WEBP ไม่เกิน {MAX_PHOTO_MB} MB ต่อรูป)",
        widget=MultipleFileInput(
            attrs={
                "accept": "image/jpeg,image/png,image/webp",
                "class": "w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-lg "
                "file:border-0 file:bg-red-50 file:text-red-600 file:font-bold hover:file:bg-red-100",
            }
        ),
    )

    class Meta:
        model = RepairTicket
        fields = ["device_model", "symptom"]
        widgets = {
            "device_model": forms.TextInput(
                attrs={"class": INPUT, "placeholder": "เช่น iPhone 13 Pro, Samsung S24"}
            ),
            "symptom": forms.Textarea(
                attrs={"class": INPUT, "rows": 3, "placeholder": "เช่น จอแตกทัชไม่ได้, ชาร์จไฟไม่เข้า"}
            ),
        }

    def clean_photos(self):
        files = self.cleaned_data["photos"]
        if not MIN_PHOTOS <= len(files) <= MAX_PHOTOS:
            raise forms.ValidationError(
                f"กรุณาแนบรูปภาพ {MIN_PHOTOS}-{MAX_PHOTOS} รูป (คุณเลือกมา {len(files)} รูป)"
            )
        for f in files:
            if f.size > MAX_PHOTO_MB * 1024 * 1024:
                raise forms.ValidationError(f"รูป {f.name} ใหญ่เกิน {MAX_PHOTO_MB} MB")
            fmt = getattr(getattr(f, "image", None), "format", None)
            if fmt not in ALLOWED_FORMATS:
                raise forms.ValidationError(f"รูป {f.name} ไม่รองรับ (ใช้ได้เฉพาะ JPG, PNG, WEBP)")
        return files


class StaffTicketForm(PhoneCleanMixin, forms.ModelForm):
    """ฟอร์มเพิ่ม/แก้ไขงานซ่อมสำหรับช่าง/เจ้าของร้าน"""

    class Meta:
        model = RepairTicket
        fields = ["customer_name", "customer_phone", "device_model", "symptom", "status", "note"]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": INPUT}),
            "customer_phone": forms.TextInput(attrs={"class": INPUT, "type": "tel"}),
            "device_model": forms.TextInput(attrs={"class": INPUT}),
            "symptom": forms.Textarea(attrs={"class": INPUT, "rows": 4}),
            "status": forms.Select(attrs={"class": INPUT}),
            "note": forms.Textarea(
                attrs={"class": INPUT, "rows": 3, "placeholder": "เช่น รออะไหล่ 3 วัน, ลูกค้าขอรับเครื่องวันเสาร์"}
            ),
        }
        labels = {"status": "สถานะ"}


class StatusUpdateForm(forms.Form):
    """ช่างแจ้งสถานะการซ่อม (พร้อมหมายเหตุสั้น ๆ ถึงเจ้าของร้าน)"""

    status = forms.ChoiceField(
        label="สถานะ",
        choices=RepairTicket.Status.choices,
        widget=forms.Select(attrs={"class": INPUT}),
    )
    note = forms.CharField(
        label="หมายเหตุถึงเจ้าของร้าน (ไม่บังคับ)",
        required=False,
        max_length=300,
        widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "เช่น เปลี่ยนจอเสร็จแล้ว รอทดสอบ"}),
    )
