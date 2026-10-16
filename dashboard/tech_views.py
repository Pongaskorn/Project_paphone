"""หน้าของช่าง (เจ้าของร้าน/ผู้ดูแลก็เปิดดูรายละเอียดงานได้เช่นกัน)"""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from inventory.forms import AddPartForm
from repairs.forms import StaffTicketForm, StatusUpdateForm
from repairs.models import Notification, RepairTicket
from repairs.services import (
    STAFF_ROLES,
    announce_new_ticket,
    change_status,
    record_status_change,
)

staff_required = role_required(*STAFF_ROLES, login_url="accounts:tech_login")


@staff_required
def dashboard(request):
    q = request.GET.get("q", "").strip()
    current = request.GET.get("status", "")
    base = RepairTicket.objects.all()
    if q:
        base = base.filter(
            Q(customer_name__icontains=q)
            | Q(customer_phone__icontains=q)
            | Q(device_model__icontains=q)
            | Q(ticket_code__icontains=q)
        )
    counts = dict(base.order_by().values_list("status").annotate(n=Count("id")))
    stats = [
        {"value": s.value, "label": s.label, "count": counts.get(s.value, 0)}
        for s in RepairTicket.Status
    ]
    tickets = base
    if current in RepairTicket.Status.values:
        tickets = base.filter(status=current)
    else:
        current = ""
    return render(
        request,
        "dashboard/tech_dashboard.html",
        {"tickets": tickets.prefetch_related("photos"), "stats": stats, "total": sum(counts.values()), "current": current, "q": q},
    )


@staff_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(RepairTicket, pk=pk)
    form = StatusUpdateForm(request.POST or None, initial={"status": ticket.status})
    ticket_parts = list(ticket.parts_used.select_related("part"))
    if request.method == "POST" and form.is_valid():
        changed = change_status(
            ticket, form.cleaned_data["status"], request.user, form.cleaned_data["note"]
        )
        if changed:
            messages.success(request, "บันทึกสถานะและแจ้งเจ้าของร้านเรียบร้อย")
        return redirect("tech:detail", pk=pk)
    return render(
        request,
        "dashboard/ticket_detail.html",
        {
            "ticket": ticket,
            "status_form": form,
            "logs": ticket.logs.select_related("changed_by")[:20],
            "ticket_parts": ticket_parts,
            "parts_total": sum(u.total for u in ticket_parts),
            "parts_form": AddPartForm(),
            "history": RepairTicket.objects.filter(customer_phone=ticket.customer_phone).exclude(pk=pk)[:5],
        },
    )


@staff_required
def ticket_create(request):
    form = StaffTicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save()
        announce_new_ticket(ticket, actor=request.user)
        messages.success(request, f"เพิ่มงานซ่อม {ticket.ticket_code} เรียบร้อย")
        return redirect("tech:detail", pk=ticket.pk)
    return render(request, "dashboard/ticket_form.html", {"form": form, "title": "เพิ่มงานซ่อมใหม่"})


@staff_required
def ticket_edit(request, pk):
    ticket = get_object_or_404(RepairTicket, pk=pk)
    old_status = ticket.status  # ต้องเก็บก่อน bind ฟอร์ม
    form = StaffTicketForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        ticket = form.save()
        if ticket.status != old_status:
            record_status_change(ticket, old_status, ticket.status, request.user)
        messages.success(request, "บันทึกการแก้ไขเรียบร้อย")
        return redirect("tech:detail", pk=pk)
    return render(
        request,
        "dashboard/ticket_form.html",
        {"form": form, "title": f"แก้ไขงานซ่อม {ticket.ticket_code}", "ticket": ticket},
    )


@staff_required
@require_POST
def ticket_delete(request, pk):
    ticket = get_object_or_404(RepairTicket, pk=pk)
    code = ticket.ticket_code
    ticket.delete()
    messages.success(request, f"ลบงานซ่อม {code} แล้ว")
    return redirect("tech:dashboard")


@staff_required
def notifications(request):
    if request.method == "POST":
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return redirect("tech:notifications")
    items = Notification.objects.filter(recipient=request.user).select_related("ticket")[:100]
    return render(request, "dashboard/notifications.html", {"items": items})


@staff_required
def notification_open(request, pk):
    item = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not item.is_read:
        item.is_read = True
        item.save(update_fields=["is_read"])
    if item.ticket_id:
        return redirect("tech:detail", pk=item.ticket_id)
    return redirect("tech:notifications")
