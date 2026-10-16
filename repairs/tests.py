import os
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User

from .models import RepairTicket, TicketPhoto

TMP_MEDIA = tempfile.mkdtemp(prefix="test_media_")


def make_image(name="a.jpg", fmt="JPEG", size=(300, 200), color=(200, 30, 30)):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=f"image/{fmt.lower()}")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class BookingPhotoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.member = User.objects.create_user(
            "member1", password="x", first_name="สมชาย", last_name="ใจดี", phone="0811111111"
        )
        self.other = User.objects.create_user("member2", password="x", phone="0899999999")
        self.tech = User.objects.create_user("tech1", password="x", role="technician")
        self.url = reverse("repairs:new")
        self.client.force_login(self.member)

    def post(self, photos, **extra):
        data = {"device_model": "iPhone 13", "symptom": "จอแตก", "photos": photos, **extra}
        return self.client.post(self.url, data)

    # ---------- ชื่อ/เบอร์จากบัญชี ----------
    def test_form_has_no_name_or_phone_inputs_and_shows_account_info(self):
        r = self.client.get(self.url)
        self.assertNotIn("customer_name", r.context["form"].fields)
        self.assertNotIn("customer_phone", r.context["form"].fields)
        self.assertContains(r, "สมชาย ใจดี")
        self.assertContains(r, "0811111111")

    def test_ticket_uses_account_name_and_phone_even_if_spoofed(self):
        r = self.post([make_image("1.jpg"), make_image("2.jpg")], customer_name="hacker", customer_phone="0000000000")
        self.assertRedirects(r, reverse("repairs:status"))
        t = RepairTicket.objects.get()
        self.assertEqual((t.customer_name, t.customer_phone, t.customer), ("สมชาย ใจดี", "0811111111", self.member))

    def test_username_used_when_no_full_name(self):
        self.client.force_login(self.other)
        self.post([make_image("1.jpg"), make_image("2.jpg")])
        self.assertEqual(RepairTicket.objects.get().customer_name, "member2")

    # ---------- อัปโหลดรูป ----------
    def test_two_or_three_photos_ok(self):
        self.post([make_image("1.jpg"), make_image("2.png", "PNG")])
        self.post([make_image("1.jpg"), make_image("2.jpg"), make_image("3.webp", "WEBP")])
        self.assertEqual([t.photos.count() for t in RepairTicket.objects.order_by("id")], [2, 3])

    def test_wrong_photo_count_rejected(self):
        for photos in ([], [make_image()], [make_image(f"{i}.jpg") for i in range(4)]):
            r = self.post(photos)
            self.assertEqual(r.status_code, 200)
            self.assertIn("photos", r.context["form"].errors)
        self.assertEqual(RepairTicket.objects.count(), 0)
        self.assertEqual(TicketPhoto.objects.count(), 0)

    def test_non_image_and_disallowed_format_rejected(self):
        fake = SimpleUploadedFile("evil.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
        self.assertEqual(self.post([fake, make_image()]).status_code, 200)
        gif = make_image("a.gif", "GIF")
        self.assertEqual(self.post([gif, make_image()]).status_code, 200)
        self.assertEqual(RepairTicket.objects.count(), 0)

    def test_photo_is_resized_to_jpeg_and_exif_stripped(self):
        buf = BytesIO()
        img = Image.new("RGB", (3200, 2400), (10, 10, 200))
        exif = Image.Exif()
        exif[0x010F] = "TestCamera"  # Make
        img.save(buf, "JPEG", exif=exif)
        big = SimpleUploadedFile("big.jpg", buf.getvalue(), content_type="image/jpeg")
        self.post([big, make_image()])
        p = TicketPhoto.objects.first()
        self.assertTrue(p.image.name.endswith(".jpg"))
        self.assertNotIn("big", p.image.name)  # ไม่ใช้ชื่อไฟล์เดิมของลูกค้า
        with Image.open(p.image.path) as saved:
            self.assertLessEqual(max(saved.size), 1600)
            self.assertEqual(saved.format, "JPEG")
            self.assertNotIn(0x010F, saved.getexif())

    # ---------- สิทธิ์ดูรูป ----------
    def test_photo_access_control(self):
        self.post([make_image("1.jpg"), make_image("2.jpg")])
        p = TicketPhoto.objects.first()
        url = reverse("repairs:photo", args=[p.pk])

        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)  # ยังไม่ login

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)  # สมาชิกคนอื่น

        for u in (self.member, self.tech):
            self.client.force_login(u)
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r["Content-Type"], "image/jpeg")
            self.assertTrue(b"".join(r.streaming_content).startswith(b"\xff\xd8"))

    # ---------- แสดงผล ----------
    def test_photos_shown_to_member_and_staff(self):
        self.post([make_image("1.jpg"), make_image("2.jpg")])
        t = RepairTicket.objects.get()
        first = TicketPhoto.objects.first()
        photo_url = reverse("repairs:photo", args=[first.pk])
        self.assertContains(self.client.get(reverse("repairs:status")), photo_url)
        self.client.force_login(self.tech)
        self.assertContains(self.client.get(reverse("tech:detail", args=[t.pk])), photo_url)
        self.assertContains(self.client.get(reverse("tech:dashboard")), 'data-lucide="camera"')

    # ---------- ลบ ----------
    def test_deleting_ticket_removes_files(self):
        self.post([make_image("1.jpg"), make_image("2.jpg")])
        paths = [p.image.path for p in TicketPhoto.objects.all()]
        self.assertTrue(all(os.path.exists(x) for x in paths))
        RepairTicket.objects.get().delete()
        self.assertEqual(TicketPhoto.objects.count(), 0)
        self.assertFalse(any(os.path.exists(x) for x in paths))
