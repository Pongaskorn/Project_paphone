from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import role_required

from .forms import BookingForm
from .models import RepairTicket
from .services import announce_new_ticket


@role_required("user")
def booking(request):
    user = request.user
    initial = {
        "customer_name": user.get_full_name() or user.username,
        "customer_phone": user.phone,
    }
    form = BookingForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.customer = user
        ticket.save()
        announce_new_ticket(ticket, actor=user)
        messages.success(
            request,
            f"ส่งข้อมูลแจ้งซ่อมเรียบร้อยแล้ว รหัสติดตามของคุณคือ {ticket.ticket_code} "
            "เจ้าหน้าที่จะติดต่อกลับ",
        )
        return redirect("repairs:status")
    return render(request, "repairs/booking.html", {"form": form})


@role_required("user")
def status(request):
    tickets = RepairTicket.objects.filter(customer=request.user)
    return render(request, "repairs/status.html", {"tickets": tickets})
