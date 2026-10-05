from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from repairs.models import Notification, RepairTicket

from .models import Part, StockMovement
from .services import StockError, adjust_stock, receive_stock, remove_part, use_part


class StockTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x", role="owner")
        self.tech = User.objects.create_user("tech", password="x", role="technician")
        self.member = User.objects.create_user("mem", password="x", role="user")
        self.part = Part.objects.create(sku="P1", name="จอ", cost_price=100, sell_price=200, min_quantity=2)
        receive_stock(self.part, 5, self.owner, "ยอดยกมา")
        self.ticket = RepairTicket.objects.create(customer_name="a", customer_phone="0812345678", device_model="x", symptom="y")

    def qty(self):
        self.part.refresh_from_db()
        return self.part.quantity

    def test_use_part_deducts_and_logs(self):
        use_part(self.ticket, self.part, 2, self.tech)
        self.assertEqual(self.qty(), 3)
        self.assertEqual(self.ticket.parts_used.get().quantity, 2)
        self.assertEqual(self.part.movements.first().change, -2)

    def test_use_same_part_twice_merges(self):
        use_part(self.ticket, self.part, 1, self.tech)
        use_part(self.ticket, self.part, 1, self.tech)
        self.assertEqual(self.ticket.parts_used.count(), 1)
        self.assertEqual(self.ticket.parts_used.get().quantity, 2)

    def test_cannot_use_more_than_stock(self):
        with self.assertRaises(StockError):
            use_part(self.ticket, self.part, 6, self.tech)
        self.assertEqual(self.qty(), 5)
        self.assertEqual(self.ticket.parts_used.count(), 0)

    def test_low_stock_notifies_managers_only(self):
        use_part(self.ticket, self.part, 3, self.tech)  # เหลือ 2 = จุดสั่งซื้อ
        self.assertTrue(Notification.objects.filter(recipient=self.owner, message__contains="ควรสั่งซื้อ").exists())
        self.assertFalse(Notification.objects.filter(recipient=self.tech).exists())

    def test_remove_returns_stock(self):
        usage = use_part(self.ticket, self.part, 2, self.tech)
        remove_part(usage, self.tech)
        self.assertEqual(self.qty(), 5)
        self.assertEqual(self.ticket.parts_used.count(), 0)

    def test_delete_ticket_returns_stock(self):
        use_part(self.ticket, self.part, 2, self.tech)
        self.ticket.delete()
        self.assertEqual(self.qty(), 5)

    def test_adjust(self):
        adjust_stock(self.part, 1, self.owner, "นับได้ 1")
        self.assertEqual(self.qty(), 1)
        self.assertEqual(self.part.movements.first().change, -4)
        self.assertIsNone(adjust_stock(self.part, 1, self.owner))

    def test_inactive_part_cannot_be_used(self):
        self.part.is_active = False
        self.part.save()
        with self.assertRaises(StockError):
            use_part(self.ticket, self.part, 1, self.tech)


class ViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="x", role="owner")
        self.tech = User.objects.create_user("tech", password="x", role="technician")
        self.member = User.objects.create_user("mem", password="x", role="user")
        self.part = Part.objects.create(sku="P1", name="จอ", sell_price=200)
        receive_stock(self.part, 3)
        self.ticket = RepairTicket.objects.create(customer_name="a", customer_phone="0812345678", device_model="x", symptom="y")

    def test_member_forbidden_anon_redirected(self):
        self.assertEqual(self.client.get(reverse("inventory:list")).status_code, 302)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("inventory:list")).status_code, 403)

    def test_tech_can_view_but_not_manage(self):
        self.client.force_login(self.tech)
        self.assertEqual(self.client.get(reverse("inventory:list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:detail", args=[self.part.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:create")).status_code, 403)
        r = self.client.post(reverse("inventory:receive", args=[self.part.pk]), {"quantity": 5})
        self.assertEqual(r.status_code, 403)
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity, 3)

    def test_tech_uses_part_via_ticket_page(self):
        self.client.force_login(self.tech)
        r = self.client.post(
            reverse("inventory:ticket_add_part", args=[self.ticket.pk]), {"part": self.part.pk, "quantity": 2}
        )
        self.assertRedirects(r, reverse("tech:detail", args=[self.ticket.pk]))
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity, 1)
        page = self.client.get(reverse("tech:detail", args=[self.ticket.pk]))
        self.assertContains(page, "อะไหล่ที่ใช้ในงานนี้")
        self.assertContains(page, "จอ")

    def test_owner_create_with_initial_stock(self):
        self.client.force_login(self.owner)
        r = self.client.post(
            reverse("inventory:create"),
            {"sku": "b-1", "name": "แบต", "category": "battery", "cost_price": "10", "sell_price": "20",
             "min_quantity": 1, "initial_quantity": 4},
        )
        part = Part.objects.get(sku="B-1")
        self.assertRedirects(r, reverse("inventory:detail", args=[part.pk]))
        self.assertEqual(part.quantity, 4)
        self.assertEqual(StockMovement.objects.filter(part=part).count(), 1)

    def test_owner_receive_and_filters(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("inventory:receive", args=[self.part.pk]), {"quantity": 2, "note": "n"})
        self.part.refresh_from_db()
        self.assertEqual(self.part.quantity, 5)
        self.assertEqual(self.client.get(reverse("inventory:list") + "?low=1&q=จอ&cat=other").status_code, 200)
