from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from repairs.models import RepairTicket
from repairs.services import change_status

# หน้าจัดการของเจ้าของร้าน / ผู้ดูแลระบบ
manager_required = role_required("owner", "admin", login_url="accounts:admin_login")


def _back(request):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("dashboard:manage")


@manager_required
def manage(request):
    current = request.GET.get("status", "")
    tickets = RepairTicket.objects.prefetch_related("photos")
    if current in RepairTicket.Status.values:
        tickets = tickets.filter(status=current)
    else:
        current = ""
    counts = dict(RepairTicket.objects.order_by().values_list("status").annotate(n=Count("id")))
    stats = [
        {"value": s.value, "label": s.label, "count": counts.get(s.value, 0)}
        for s in RepairTicket.Status
    ]
    return render(
        request,
        "dashboard/manage.html",
        {
            "tickets": tickets,
            "stats": stats,
            "total": sum(counts.values()),
            "current": current,
            "status_choices": RepairTicket.Status.choices,
        },
    )


@manager_required
@require_POST
def update_status(request, pk):
    ticket = get_object_or_404(RepairTicket, pk=pk)
    new_status = request.POST.get("status")
    if new_status in RepairTicket.Status.values:
        change_status(ticket, new_status, request.user)
    return _back(request)


@manager_required
@require_POST
def delete_ticket(request, pk):
    get_object_or_404(RepairTicket, pk=pk).delete()
    return _back(request)
