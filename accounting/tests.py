from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from inventory.models import Part
from inventory.services import receive_stock
from repairs.models import RepairTicket

from .models import Transaction


def make_tx(kind, category, amount, day=None, **kw):
    return Transaction.objects.create(
        type=kind, category=category, amount=Decimal(amount), date=day or timezone.localdate(), **kw
    )


class LedgerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x", role="owner")
        self.admin = User.objects.create_user("adm", password="x", role="admin")
        self.tech = User.objects.create_user("tech", password="x", role="technician")
        self.member = User.objects.create_user("mem", password="x", role="user")
        self.ticket = RepairTicket.objects.create(
            customer_name="a", customer_phone="0812345678", device_model="iPhone 13", symptom="y"
        )

    def test_only_owner_can_access(self):
        tx = make_tx("income", "repair", "100")
        url = reverse("accounting:ledger")
        self.assertEqual(self.client.get(url).status_code, 302)  # ยังไม่ login
        for user in (self.admin, self.tech, self.member):
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.get(reverse("accounting:create", args=["income"])).status_code, 403)
            self.assertEqual(self.client.get(reverse("accounting:export")).status_code, 403)
            self.assertEqual(self.client.get(reverse("accounting:edit", args=[tx.pk])).status_code, 403)
            self.assertEqual(self.client.post(reverse("accounting:delete", args=[tx.pk])).status_code, 403)
        self.assertEqual(Transaction.objects.count(), 1)  # แอดมินลบไม่ได้
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_does_not_see_accounting_link_or_django_admin_model(self):
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(reverse("tech:dashboard")), reverse("accounting:ledger"))
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("tech:dashboard")), reverse("accounting:ledger"))
        from django.contrib import admin as dj_admin

        self.assertNotIn(Transaction, dj_admin.site._registry)

    def test_totals_for_selected_month_only(self):
        today = timezone.localdate()
        last_month = today.replace(day=1) - timedelta(days=1)
        make_tx("income", "repair", "300")
        make_tx("income", "sale", "200")
        make_tx("expense", "rent", "150")
        make_tx("income", "repair", "9999", day=last_month)
        self.client.force_login(self.owner)

        t = self.client.get(reverse("accounting:ledger")).context["totals"]
        self.assertEqual(t["income"], Decimal("500"))
        self.assertEqual(t["expense"], Decimal("150"))
        self.assertEqual(t["profit"], Decimal("350"))

        t = self.client.get(reverse("accounting:ledger"), {"month": last_month.strftime("%Y-%m")}).context["totals"]
        self.assertEqual(t["income"], Decimal("9999"))

        t = self.client.get(reverse("accounting:ledger"), {"month": "all"}).context["totals"]
        self.assertEqual(t["income"], Decimal("10499"))

    def test_bad_month_falls_back_and_empty_month_works(self):
        self.client.force_login(self.owner)
        for m in ("zzz", "2026-13", ""):
            self.assertEqual(self.client.get(reverse("accounting:ledger"), {"month": m}).status_code, 200)

    def test_filters(self):
        make_tx("income", "repair", "300", description="เปลี่ยนจอ")
        make_tx("expense", "rent", "150", description="ค่าเช่า")
        self.client.force_login(self.owner)
        url = reverse("accounting:ledger")
        rows = list(self.client.get(url, {"type": "expense"}).context["page"])
        self.assertEqual([r.category for r in rows], ["rent"])
        rows = list(self.client.get(url, {"q": "จอ"}).context["page"])
        self.assertEqual(len(rows), 1)
        rows = list(self.client.get(url, {"cat": "repair", "type": "bogus"}).context["page"])
        self.assertEqual(len(rows), 1)

    def test_create_income_links_ticket_and_sets_type(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            reverse("accounting:create", args=["income"]),
            {"category": "repair", "amount": "1500.50", "date": timezone.localdate().isoformat(),
             "description": "เปลี่ยนจอ", "ticket_code": self.ticket.ticket_code.lower()},
        )
        self.assertRedirects(r, reverse("accounting:ledger"))
        tx = Transaction.objects.get()
        self.assertEqual(tx.type, "income")
        self.assertEqual(tx.ticket, self.ticket)
        self.assertEqual(tx.created_by, self.owner)
        self.assertEqual(tx.amount, Decimal("1500.50"))

    def test_invalid_ticket_code_amount_and_category_mismatch(self):
        self.client.force_login(self.owner)
        url = reverse("accounting:create", args=["income"])
        today = timezone.localdate().isoformat()
        base = {"category": "repair", "amount": "100", "date": today}
        self.assertEqual(self.client.post(url, {**base, "ticket_code": "RP-NOPE"}).status_code, 200)
        self.assertEqual(self.client.post(url, {**base, "amount": "0"}).status_code, 200)
        self.assertEqual(self.client.post(url, {**base, "amount": "-5"}).status_code, 200)
        # หมวดรายจ่ายส่งมาที่ฟอร์มรายรับ ต้องไม่ผ่าน
        self.assertEqual(self.client.post(url, {**base, "category": "rent"}).status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_expense_form_has_no_ticket_field_and_unknown_kind_404(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            reverse("accounting:create", args=["expense"]),
            {"category": "rent", "amount": "5000", "date": timezone.localdate().isoformat(), "ticket_code": self.ticket.ticket_code},
        )
        self.assertRedirects(r, reverse("accounting:ledger"))
        tx = Transaction.objects.get()
        self.assertEqual(tx.type, "expense")
        self.assertIsNone(tx.ticket)
        self.assertEqual(self.client.get(reverse("accounting:create", args=["bogus"])).status_code, 404)

    def test_prefill_from_ticket_page_link(self):
        self.client.force_login(self.owner)
        r = self.client.get(
            reverse("accounting:create", args=["income"]), {"ticket": self.ticket.ticket_code, "amount": "1800.00"}
        )
        init = r.context["form"].initial
        self.assertEqual(init["ticket_code"], self.ticket.ticket_code)
        self.assertEqual(init["amount"], Decimal("1800.00"))
        self.assertIn("iPhone 13", init["description"])

    def test_edit_and_delete(self):
        tx = make_tx("income", "repair", "100")
        self.client.force_login(self.owner)
        r = self.client.post(
            reverse("accounting:edit", args=[tx.pk]),
            {"category": "sale", "amount": "250", "date": tx.date.isoformat(), "description": "x"},
        )
        self.assertRedirects(r, reverse("accounting:ledger"))
        tx.refresh_from_db()
        self.assertEqual((tx.category, tx.amount, tx.type), ("sale", Decimal("250"), "income"))
        self.client.post(reverse("accounting:delete", args=[tx.pk]))
        self.assertEqual(Transaction.objects.count(), 0)
        # ลบต้องเป็น POST เท่านั้น
        tx2 = make_tx("income", "repair", "1")
        self.assertEqual(self.client.get(reverse("accounting:delete", args=[tx2.pk])).status_code, 405)

    def test_ticket_page_shows_finance_card_for_owner_only(self):
        url = reverse("tech:detail", args=[self.ticket.pk])
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(url), "การเงินของงานนี้")
        for user in (self.tech, self.admin):
            self.client.force_login(user)
            self.assertNotContains(self.client.get(url), "การเงินของงานนี้")

    def test_csv_export(self):
        make_tx("income", "repair", "300", description="=HYPERLINK(1)", ticket=self.ticket)
        make_tx("expense", "rent", "150", description="ค่าเช่า")
        self.client.force_login(self.owner)
        r = self.client.get(reverse("accounting:export"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        body = r.content.decode("utf-8")
        self.assertTrue(body.startswith("\ufeff"))
        self.assertIn("ค่าเช่า", body)
        self.assertIn(self.ticket.ticket_code, body)
        self.assertIn("'=HYPERLINK(1)", body)  # กันสูตรใน Excel

    def test_receiving_stock_records_expense(self):
        part = Part.objects.create(sku="P1", name="จอ", cost_price=100, sell_price=200)
        self.client.force_login(self.owner)
        url = reverse("inventory:receive", args=[part.pk])

        self.client.post(url, {"quantity": 3, "cost_price": "120", "record_expense": "on"})
        tx = Transaction.objects.get()
        self.assertEqual((tx.type, tx.category, tx.source), ("expense", "parts", "stock"))
        self.assertEqual(tx.amount, Decimal("360"))

        # ไม่ติ๊ก -> ไม่สร้างรายจ่าย แต่สต็อกยังเข้า
        self.client.post(url, {"quantity": 2})
        self.assertEqual(Transaction.objects.count(), 1)
        part.refresh_from_db()
        self.assertEqual(part.quantity, 5)

        # ยอดยกมา (ผ่าน service ตรงๆ) ไม่นับเป็นรายจ่าย
        receive_stock(part, 10, note="ยอดยกมา")
        self.assertEqual(Transaction.objects.count(), 1)


class EdgeTests(TestCase):
    def test_extreme_month_does_not_crash_and_thai_date_accepts_date(self):
        from datetime import date

        from repairs.templatetags.thai import thai_date

        owner = User.objects.create_user("o", password="x", role="owner")
        self.client.force_login(owner)
        for m in ("9999-12", "0001-01", "1999-12"):
            self.assertEqual(self.client.get(reverse("accounting:ledger"), {"month": m}).status_code, 200)
        self.assertEqual(thai_date(date(2026, 10, 12)), "12 ต.ค. 2569")
