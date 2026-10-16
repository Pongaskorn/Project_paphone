from django import forms

from repairs.forms import INPUT
from repairs.models import RepairTicket

from .models import Transaction

CATEGORY_BY_TYPE = {
    Transaction.Type.INCOME: Transaction.INCOME_CATEGORIES,
    Transaction.Type.EXPENSE: Transaction.EXPENSE_CATEGORIES,
}


class TransactionForm(forms.ModelForm):
    ticket_code = forms.CharField(
        label="รหัสงานซ่อม (ถ้ามี)",
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT, "placeholder": "เช่น RP-20261012-0001"}),
    )

    class Meta:
        model = Transaction
        fields = ["category", "amount", "date", "description"]
        widgets = {
            "category": forms.Select(attrs={"class": INPUT}),
            "amount": forms.NumberInput(attrs={"class": INPUT, "step": "0.01", "min": "0.01"}),
            "date": forms.DateInput(attrs={"class": INPUT, "type": "date"}, format="%Y-%m-%d"),
            "description": forms.TextInput(attrs={"class": INPUT, "placeholder": "เช่น ค่าเปลี่ยนจอ iPhone 13"}),
        }

    def __init__(self, *args, tx_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_type = tx_type
        allowed = CATEGORY_BY_TYPE[tx_type]
        self.fields["category"].choices = [(c.value, c.label) for c in allowed]
        if tx_type == Transaction.Type.EXPENSE:
            del self.fields["ticket_code"]  # รหัสงานซ่อมใช้เฉพาะรายรับ
        elif self.instance.pk and self.instance.ticket_id:
            self.fields["ticket_code"].initial = self.instance.ticket.ticket_code

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("จำนวนเงินต้องมากกว่า 0")
        return amount

    def clean_ticket_code(self):
        code = self.cleaned_data["ticket_code"].strip()
        if not code:
            return None
        try:
            return RepairTicket.objects.get(ticket_code__iexact=code)
        except RepairTicket.DoesNotExist:
            raise forms.ValidationError("ไม่พบรหัสงานซ่อมนี้")

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.type = self.tx_type
        obj.ticket = self.cleaned_data.get("ticket_code") if "ticket_code" in self.fields else None
        if commit:
            obj.save()
        return obj
