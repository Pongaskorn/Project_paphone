from django import forms

from repairs.forms import INPUT

from .models import Part


class PartForm(forms.ModelForm):
    # ใช้ตอนเพิ่มอะไหล่ใหม่เท่านั้น (ตอนแก้ไขต้องปรับยอดผ่านปุ่มรับเข้า/ปรับยอด เพื่อให้มีประวัติ)
    initial_quantity = forms.IntegerField(
        label="จำนวนเริ่มต้น", min_value=0, required=False, initial=0, widget=forms.NumberInput(attrs={"class": INPUT})
    )

    class Meta:
        model = Part
        fields = [
            "sku", "name", "category", "compatible_models",
            "cost_price", "sell_price", "min_quantity", "location",
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"class": INPUT, "placeholder": "เช่น SCR-IP13-01"}),
            "name": forms.TextInput(attrs={"class": INPUT}),
            "category": forms.Select(attrs={"class": INPUT}),
            "compatible_models": forms.TextInput(attrs={"class": INPUT}),
            "cost_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "sell_price": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0"}),
            "min_quantity": forms.NumberInput(attrs={"class": INPUT, "min": "0"}),
            "location": forms.TextInput(attrs={"class": INPUT}),
        }

    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        if editing:
            del self.fields["initial_quantity"]

    def clean_sku(self):
        return self.cleaned_data["sku"].strip().upper()


class ReceiveForm(forms.Form):
    quantity = forms.IntegerField(label="จำนวนที่รับเข้า", min_value=1, widget=forms.NumberInput(attrs={"class": INPUT}))
    cost_price = forms.DecimalField(
        label="ราคาทุนใหม่ (ถ้าเปลี่ยน)", required=False, min_value=0, max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"class": INPUT, "step": "0.01"}),
    )
    note = forms.CharField(
        label="หมายเหตุ", required=False, max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "เช่น ซื้อจากร้าน ABC"}),
    )


class AdjustForm(forms.Form):
    new_quantity = forms.IntegerField(
        label="จำนวนที่นับได้จริง", min_value=0, widget=forms.NumberInput(attrs={"class": INPUT})
    )
    note = forms.CharField(
        label="เหตุผล", max_length=200, widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "เช่น ตรวจนับสิ้นเดือน, ของชำรุด"})
    )


class AddPartForm(forms.Form):
    """ช่างเลือกอะไหล่ที่ใช้ในงานซ่อม"""

    part = forms.ModelChoiceField(
        label="อะไหล่", queryset=Part.objects.none(), widget=forms.Select(attrs={"class": INPUT}),
        empty_label="-- เลือกอะไหล่ --",
    )
    quantity = forms.IntegerField(
        label="จำนวน", min_value=1, initial=1, widget=forms.NumberInput(attrs={"class": INPUT})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["part"].queryset = Part.objects.filter(is_active=True, quantity__gt=0)
        self.fields["part"].label_from_instance = lambda p: f"{p.sku} · {p.name} (เหลือ {p.quantity})"
