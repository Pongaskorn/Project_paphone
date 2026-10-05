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


class BookingForm(PhoneCleanMixin, forms.ModelForm):
    """ฟอร์มแจ้งซ่อมของลูกค้า (สมาชิก)"""

    class Meta:
        model = RepairTicket
        fields = ["customer_name", "customer_phone", "device_model", "symptom"]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": INPUT}),
            "customer_phone": forms.TextInput(
                attrs={"class": INPUT, "type": "tel", "placeholder": "062-6303184"}
            ),
            "device_model": forms.TextInput(
                attrs={"class": INPUT, "placeholder": "เช่น iPhone 13 Pro, Samsung S24"}
            ),
            "symptom": forms.Textarea(
                attrs={"class": INPUT, "rows": 3, "placeholder": "เช่น จอแตกทัชไม่ได้, ชาร์จไฟไม่เข้า"}
            ),
        }


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
