from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required

from .forms import BookingForm
from .images import optimize_image
from .models import RepairTicket, TicketPhoto
from .services import STAFF_ROLES, announce_new_ticket


@role_required("user")
def booking(request):
    user = request.user
    form = BookingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ticket = form.save(commit=False)
            # ชื่อ/เบอร์มาจากบัญชีที่ login เท่านั้น (ค่าที่ส่งมาจากฟอร์มจะไม่ถูกใช้)
            ticket.customer = user
            ticket.customer_name = user.get_full_name() or user.username
            ticket.customer_phone = user.phone
            ticket.save()
            for f in form.cleaned_data["photos"]:
                TicketPhoto.objects.create(ticket=ticket, image=optimize_image(f))
        announce_new_ticket(ticket, actor=user)
        messages.success(
            request,
            f"ส่งข้อมูลแจ้งซ่อมเรียบร้อยแล้ว รหัสติดตามของคุณคือ {ticket.ticket_code} "
            "เจ้าหน้าที่จะติดต่อกลับ",
        )
        return redirect("repairs:status")
    return render(
        request,
        "repairs/booking.html",
        {
            "form": form,
            "display_name": user.get_full_name() or user.username,
            "display_phone": user.phone,
        },
    )


@role_required("user")
def status(request):
    tickets = RepairTicket.objects.filter(customer=request.user).prefetch_related("photos")
    return render(request, "repairs/status.html", {"tickets": tickets})


@login_required
def photo(request, pk):
    """ส่งรูปให้เฉพาะเจ้าของงานซ่อมและพนักงาน (รูปไม่ได้เปิดเป็นไฟล์สาธารณะ)"""
    item = get_object_or_404(TicketPhoto.objects.select_related("ticket"), pk=pk)
    user = request.user
    if user.role not in STAFF_ROLES and item.ticket.customer_id != user.pk:
        raise PermissionDenied
    try:
        handle = item.image.open("rb")
    except FileNotFoundError:
        raise Http404
    response = FileResponse(handle, content_type="image/jpeg")
    response["Cache-Control"] = "private, max-age=3600"
    return response
