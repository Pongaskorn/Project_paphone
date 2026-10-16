import calendar
import csv
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from repairs.models import RepairTicket

from .forms import TransactionForm
from .models import Transaction

# บัญชีร้าน: เจ้าของร้านเท่านั้น (แอดมิน/ช่าง/ลูกค้า ได้ 403)
manager_required = role_required("owner", login_url="accounts:admin_login")

TYPES = {t.value: t for t in Transaction.Type}
ZERO = Decimal("0")
MONTHS_TH = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def _shift_month(d, delta):
    """เลื่อนวันที่ 1 ของเดือนไปข้างหน้า/ถอยหลัง delta เดือน"""
    idx = d.year * 12 + (d.month - 1) + delta
    return date(idx // 12, idx % 12 + 1, 1)


def _month_label(d):
    return f"{MONTHS_TH[d.month - 1]} {d.year + 543}"


def _period(request):
    """คืน (start, end, key, label)  key = 'YYYY-MM' หรือ 'all'"""
    raw = request.GET.get("month", "")
    if raw == "all":
        return None, None, "all", "ทั้งหมด"
    today = timezone.localdate()
    try:
        y, m = raw.split("-")
        first = date(int(y), int(m), 1)
        if not 2000 <= first.year <= 2100:
            raise ValueError
    except (ValueError, TypeError):
        first = today.replace(day=1)
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    return first, last, first.strftime("%Y-%m"), _month_label(first)


def _totals(qs):
    agg = qs.aggregate(
        income=Sum("amount", filter=Q(type=Transaction.Type.INCOME)),
        expense=Sum("amount", filter=Q(type=Transaction.Type.EXPENSE)),
    )
    income, expense = agg["income"] or ZERO, agg["expense"] or ZERO
    return {"income": income, "expense": expense, "profit": income - expense}


def _filtered(request):
    """รายการตามเดือน + ตัวกรอง (ใช้ร่วมกันระหว่างหน้ารายการกับ export CSV)"""
    start, end, key, label = _period(request)
    in_period = Transaction.objects.all()
    if start:
        in_period = in_period.filter(date__range=(start, end))

    tx_type = request.GET.get("type", "")
    category = request.GET.get("cat", "")
    q = request.GET.get("q", "").strip()
    rows = in_period
    if tx_type in TYPES:
        rows = rows.filter(type=tx_type)
    else:
        tx_type = ""
    if category in Transaction.Category.values:
        rows = rows.filter(category=category)
    else:
        category = ""
    if q:
        rows = rows.filter(Q(description__icontains=q) | Q(ticket__ticket_code__icontains=q))
    return in_period, rows.select_related("ticket", "created_by"), {
        "start": start, "end": end, "key": key, "label": label, "type": tx_type, "cat": category, "q": q,
    }


def _breakdown(in_period, tx_type, total):
    rows = (
        in_period.filter(type=tx_type).order_by().values("category").annotate(total=Sum("amount")).order_by("-total")
    )
    return [
        {
            "label": Transaction.Category(r["category"]).label,
            "total": r["total"],
            "percent": round(r["total"] / total * 100) if total else 0,
        }
        for r in rows
    ]


def _trend(end_month_first):
    """รายรับ/รายจ่ายย้อนหลัง 6 เดือน (นับถึงเดือนที่เลือก)"""
    first = _shift_month(end_month_first, -5)
    last = end_month_first.replace(day=calendar.monthrange(end_month_first.year, end_month_first.month)[1])
    rows = (
        Transaction.objects.filter(date__range=(first, last))
        .annotate(m=TruncMonth("date"))
        .order_by()
        .values("m", "type")
        .annotate(total=Sum("amount"))
    )
    data = {}
    for r in rows:
        m = r["m"]
        m = m.date() if hasattr(m, "date") else m
        data[(m.year, m.month, r["type"])] = r["total"]
    months = []
    for i in range(6):
        d = _shift_month(first, i)
        inc = data.get((d.year, d.month, "income"), ZERO)
        exp = data.get((d.year, d.month, "expense"), ZERO)
        months.append({"label": _month_label(d), "income": inc, "expense": exp, "profit": inc - exp})
    peak = max([m["income"] for m in months] + [m["expense"] for m in months] + [ZERO])
    for m in months:
        m["income_w"] = round(m["income"] / peak * 100) if peak else 0
        m["expense_w"] = round(m["expense"] / peak * 100) if peak else 0
    return months


@manager_required
def ledger(request):
    in_period, rows, f = _filtered(request)
    totals = _totals(in_period)

    today_first = timezone.localdate().replace(day=1)
    anchor = f["start"] or today_first
    page = Paginator(rows, 20).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "accounting/ledger.html",
        {
            "f": f,
            "totals": totals,
            "income_breakdown": _breakdown(in_period, Transaction.Type.INCOME, totals["income"]),
            "expense_breakdown": _breakdown(in_period, Transaction.Type.EXPENSE, totals["expense"]),
            "trend": _trend(anchor),
            "page": page,
            "qs": params.urlencode(),
            "prev_month": _shift_month(anchor, -1).strftime("%Y-%m") if f["start"] else None,
            "next_month": _shift_month(anchor, 1).strftime("%Y-%m")
            if f["start"] and _shift_month(anchor, 1) <= today_first
            else None,
            "this_month": today_first.strftime("%Y-%m"),
            "categories": Transaction.Category.choices,
            "types": Transaction.Type.choices,
            "export_qs": request.GET.urlencode(),
        },
    )


def _safe_cell(text):
    """กัน CSV injection: ข้อความที่ขึ้นต้นด้วย = + - @ จะถูกตีความเป็นสูตรใน Excel"""
    text = text or ""
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


@manager_required
def export_csv(request):
    _, rows, f = _filtered(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ledger-{f["key"]}.csv"'
    response.write("\ufeff")  # BOM ให้ Excel อ่านภาษาไทยถูก
    w = csv.writer(response)
    w.writerow(["วันที่", "ประเภท", "หมวดหมู่", "รายละเอียด", "รหัสงานซ่อม", "รายรับ", "รายจ่าย", "ผู้บันทึก"])
    for t in rows:
        w.writerow([
            t.date.isoformat(),
            t.get_type_display(),
            t.get_category_display(),
            _safe_cell(t.description),
            t.ticket.ticket_code if t.ticket_id else "",
            t.amount if t.is_income else "",
            "" if t.is_income else t.amount,
            _safe_cell(str(t.created_by)) if t.created_by_id else "",
        ])
    return response


def _initial_from_query(request, tx_type):
    """ลิงก์จากหน้างานซ่อมส่งรหัสงาน/ยอดมาเติมให้ล่วงหน้า"""
    initial = {}
    if tx_type == Transaction.Type.INCOME:
        initial["category"] = Transaction.Category.REPAIR
        code = request.GET.get("ticket", "").strip()
        if code:
            initial["ticket_code"] = code
            ticket = RepairTicket.objects.filter(ticket_code__iexact=code).first()
            if ticket:
                initial["description"] = f"ค่าซ่อม {ticket.device_model}"
        try:
            amount = Decimal(request.GET.get("amount", ""))
            if amount > 0:
                initial["amount"] = amount.quantize(Decimal("0.01"))
        except Exception:
            pass
    return initial


@manager_required
def transaction_create(request, kind):
    if kind not in TYPES:
        raise Http404
    tx_type = TYPES[kind]
    form = TransactionForm(
        request.POST or None, tx_type=tx_type, initial={**_initial_from_query(request, tx_type)}
    )
    if request.method == "POST" and form.is_valid():
        tx = form.save(commit=False)
        tx.created_by = request.user
        tx.save()
        messages.success(request, f"บันทึก{tx_type.label} ฿{tx.amount:,.2f} เรียบร้อย")
        return redirect("accounting:ledger")
    return render(
        request,
        "accounting/transaction_form.html",
        {"form": form, "kind": kind, "title": f"บันทึก{tx_type.label}", "is_income": kind == "income"},
    )


@manager_required
def transaction_edit(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    form = TransactionForm(request.POST or None, instance=tx, tx_type=Transaction.Type(tx.type))
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "บันทึกการแก้ไขเรียบร้อย")
        return redirect("accounting:ledger")
    return render(
        request,
        "accounting/transaction_form.html",
        {"form": form, "kind": tx.type, "title": f"แก้ไข{tx.get_type_display()}", "tx": tx, "is_income": tx.is_income},
    )


@manager_required
@require_POST
def transaction_delete(request, pk):
    get_object_or_404(Transaction, pk=pk).delete()
    messages.success(request, "ลบรายการแล้ว")
    return redirect("accounting:ledger")
