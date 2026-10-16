from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounting.models import Transaction
from accounts.decorators import role_required
from repairs.models import RepairTicket
from repairs.services import MANAGER_ROLES, STAFF_ROLES

from .forms import AddPartForm, AdjustForm, PartForm, ReceiveForm
from .models import Part, TicketPart
from .services import StockError, adjust_stock, receive_stock, remove_part, use_part

# ช่าง/เจ้าของ/แอดมิน ดูสต็อกและใช้อะไหล่ได้ — แต่เพิ่ม/แก้/รับเข้า/ปรับยอด เฉพาะเจ้าของร้านและแอดมิน
staff_required = role_required(*STAFF_ROLES, login_url="accounts:tech_login")
manager_required = role_required(*MANAGER_ROLES, login_url="accounts:admin_login")


@staff_required
def part_list(request):
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("cat", "")
    low = request.GET.get("low") == "1"
    archived = request.GET.get("archived") == "1"

    parts = Part.objects.filter(is_active=not archived)
    if q:
        parts = parts.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(compatible_models__icontains=q))
    if cat in Part.Category.values:
        parts = parts.filter(category=cat)
    else:
        cat = ""
    if low:
        parts = parts.filter(quantity__lte=F("min_quantity")).order_by("quantity", "name")

    stats = Part.objects.filter(is_active=True).aggregate(
        total=Count("id"),
        out=Count("id", filter=Q(quantity=0)),
        low=Count("id", filter=Q(quantity__gt=0, quantity__lte=F("min_quantity"))),
        value=Sum(
            ExpressionWrapper(F("cost_price") * F("quantity"), output_field=DecimalField(max_digits=14, decimal_places=2))
        ),
    )

    page = Paginator(parts, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "inventory/part_list.html",
        {
            "page": page,
            "stats": stats,
            "q": q,
            "cat": cat,
            "low": low,
            "archived": archived,
            "categories": Part.Category.choices,
            "qs": params.urlencode(),
            "is_manager": request.user.role in MANAGER_ROLES,
        },
    )


@manager_required
def part_create(request):
    form = PartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            part = form.save(commit=False)
            part.quantity = 0
            part.save()
            initial = form.cleaned_data.get("initial_quantity") or 0
            if initial > 0:
                receive_stock(part, initial, request.user, "ยอดยกมา")
        messages.success(request, f"เพิ่มอะไหล่ {part.name} เรียบร้อย")
        return redirect("inventory:detail", pk=part.pk)
    return render(request, "inventory/part_form.html", {"form": form, "title": "เพิ่มอะไหล่ใหม่"})


@manager_required
def part_edit(request, pk):
    part = get_object_or_404(Part, pk=pk)
    form = PartForm(request.POST or None, instance=part, editing=True)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "บันทึกการแก้ไขเรียบร้อย")
        return redirect("inventory:detail", pk=pk)
    return render(
        request, "inventory/part_form.html", {"form": form, "title": f"แก้ไข {part.name}", "part": part}
    )


@staff_required
def part_detail(request, pk):
    part = get_object_or_404(Part, pk=pk)
    return render(
        request,
        "inventory/part_detail.html",
        {
            "part": part,
            "movements": part.movements.select_related("created_by", "ticket")[:50],
            "receive_form": ReceiveForm(),
            "adjust_form": AdjustForm(initial={"new_quantity": part.quantity}),
            "is_manager": request.user.role in MANAGER_ROLES,
        },
    )


@manager_required
@require_POST
def part_receive(request, pk):
    part = get_object_or_404(Part, pk=pk)
    form = ReceiveForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        unit_cost = d["cost_price"] if d["cost_price"] is not None else part.cost_price
        with transaction.atomic():
            receive_stock(part, d["quantity"], request.user, d["note"], d["cost_price"])
            total = unit_cost * d["quantity"]
            if d["record_expense"] and total > 0:
                Transaction.objects.create(
                    type=Transaction.Type.EXPENSE,
                    category=Transaction.Category.PARTS,
                    amount=total,
                    date=timezone.localdate(),
                    description=f"ซื้ออะไหล่ {part.name} × {d['quantity']}"[:200],
                    source=Transaction.Source.STOCK,
                    created_by=request.user,
                )
        messages.success(request, f"รับ {part.name} เข้าสต็อก {d['quantity']} ชิ้นแล้ว")
    else:
        messages.error(request, "ข้อมูลไม่ถูกต้อง: กรุณากรอกจำนวนที่รับเข้าให้ถูกต้อง")
    return redirect("inventory:detail", pk=pk)


@manager_required
@require_POST
def part_adjust(request, pk):
    part = get_object_or_404(Part, pk=pk)
    form = AdjustForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        if adjust_stock(part, d["new_quantity"], request.user, d["note"]):
            messages.success(request, "ปรับยอดสต็อกเรียบร้อย")
        else:
            messages.info(request, "ยอดตรงกับในระบบอยู่แล้ว ไม่มีการเปลี่ยนแปลง")
    else:
        messages.error(request, "ข้อมูลไม่ถูกต้อง: กรุณากรอกจำนวนและเหตุผลให้ครบ")
    return redirect("inventory:detail", pk=pk)


@manager_required
@require_POST
def part_toggle(request, pk):
    part = get_object_or_404(Part, pk=pk)
    part.is_active = not part.is_active
    part.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"{'เปิด' if part.is_active else 'ปิด'}ใช้งาน {part.name} แล้ว")
    return redirect("inventory:detail", pk=pk)


@staff_required
@require_POST
def ticket_add_part(request, ticket_pk):
    ticket = get_object_or_404(RepairTicket, pk=ticket_pk)
    form = AddPartForm(request.POST)
    if form.is_valid():
        try:
            use_part(ticket, form.cleaned_data["part"], form.cleaned_data["quantity"], request.user)
            messages.success(request, "เพิ่มอะไหล่ในงานและตัดสต็อกแล้ว")
        except StockError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "กรุณาเลือกอะไหล่และจำนวนให้ถูกต้อง")
    return redirect("tech:detail", pk=ticket_pk)


@staff_required
@require_POST
def ticket_remove_part(request, ticket_pk, pk):
    usage = get_object_or_404(TicketPart, pk=pk, ticket_id=ticket_pk)
    remove_part(usage, request.user)
    messages.success(request, "เอาอะไหล่ออกจากงานและคืนเข้าสต็อกแล้ว")
    return redirect("tech:detail", pk=ticket_pk)
