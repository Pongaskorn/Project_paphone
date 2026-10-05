"""ตรรกะตัด/เพิ่มสต็อก ทุกการเปลี่ยนยอดต้องผ่านไฟล์นี้เพื่อให้มี movement log เสมอ"""
from django.db import transaction

from repairs.services import MANAGER_ROLES, notify

from .models import Part, StockMovement, TicketPart


class StockError(Exception):
    """ทำรายการไม่ได้ (เช่น สต็อกไม่พอ) ข้อความใช้แสดงให้ผู้ใช้ได้เลย"""


def _apply(part_id, delta, movement_type, actor=None, note="", ticket=None):
    """ล็อกแถวอะไหล่ -> ปรับยอด -> บันทึก movement (ต้องเรียกภายใน transaction)"""
    part = Part.objects.select_for_update().get(pk=part_id)
    new_qty = part.quantity + delta
    if new_qty < 0:
        raise StockError(f"สต็อก {part.name} ไม่พอ (เหลือ {part.quantity} ชิ้น)")
    part.quantity = new_qty
    part.save(update_fields=["quantity", "updated_at"])
    StockMovement.objects.create(
        part=part,
        movement_type=movement_type,
        change=delta,
        balance_after=new_qty,
        ticket=ticket,
        note=note[:200],
        created_by=actor,
    )
    return part


@transaction.atomic
def receive_stock(part, quantity, actor=None, note="", cost_price=None):
    """รับอะไหล่เข้าสต็อก (ถ้าใส่ราคาทุนใหม่ จะอัปเดตราคาทุนของอะไหล่ด้วย)"""
    if quantity <= 0:
        raise StockError("จำนวนต้องมากกว่า 0")
    part = _apply(part.pk, quantity, StockMovement.Type.IN, actor, note)
    if cost_price is not None:
        part.cost_price = cost_price
        part.save(update_fields=["cost_price", "updated_at"])
    return part


@transaction.atomic
def adjust_stock(part, new_quantity, actor=None, note=""):
    """ปรับยอดให้ตรงกับของจริงที่นับได้ (เช่น ตรวจนับสต็อก)"""
    current = Part.objects.select_for_update().get(pk=part.pk).quantity
    delta = new_quantity - current
    if delta == 0:
        return None
    return _apply(part.pk, delta, StockMovement.Type.ADJUST, actor, note or "ปรับยอดตามการตรวจนับ")


@transaction.atomic
def use_part(ticket, part, quantity, actor=None):
    """ใช้อะไหล่ในงานซ่อม: ตัดสต็อก + บันทึกว่างานนี้ใช้อะไร"""
    if quantity <= 0:
        raise StockError("จำนวนต้องมากกว่า 0")
    if not Part.objects.filter(pk=part.pk, is_active=True).exists():
        raise StockError("อะไหล่นี้ปิดใช้งานแล้ว")
    part = _apply(
        part.pk, -quantity, StockMovement.Type.OUT, actor, f"ใช้ในงาน {ticket.ticket_code}", ticket=ticket
    )
    usage, created = TicketPart.objects.get_or_create(
        ticket=ticket, part=part, defaults={"quantity": quantity, "unit_price": part.sell_price}
    )
    if not created:
        usage.quantity += quantity
        usage.save(update_fields=["quantity"])
    # สต็อกใกล้หมด/หมด -> แจ้งเตือนเจ้าของร้านและผู้ดูแล
    if part.quantity <= part.min_quantity:
        state = "หมดแล้ว" if part.quantity == 0 else f"เหลือ {part.quantity} ชิ้น"
        notify(MANAGER_ROLES, ticket, f"อะไหล่ {part.name} ({part.sku}) {state} ควรสั่งซื้อเพิ่ม", exclude=actor)
    return usage


@transaction.atomic
def remove_part(usage, actor=None):
    """เอาอะไหล่ออกจากงาน (เช่น ใส่ผิดรุ่น) แล้วคืนเข้าสต็อก"""
    ticket = usage.ticket
    _apply(
        usage.part_id,
        usage.quantity,
        StockMovement.Type.RETURN,
        actor,
        f"คืนจากงาน {ticket.ticket_code}",
        ticket=ticket,
    )
    usage.delete()


@transaction.atomic
def return_ticket_parts(ticket):
    """ใช้ตอนลบงานซ่อม: คืนอะไหล่ทั้งหมดของงานนั้นเข้าสต็อก
    (ไม่ผูก movement กับ ticket เพราะ ticket กำลังจะถูกลบ)"""
    for usage in ticket.parts_used.all():
        _apply(
            usage.part_id,
            usage.quantity,
            StockMovement.Type.RETURN,
            None,
            f"คืนจากงาน {ticket.ticket_code} ที่ถูกลบ",
        )
