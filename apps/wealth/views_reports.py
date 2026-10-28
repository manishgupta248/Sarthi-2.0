from datetime import date

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.audit import log_event
from apps.core.models import AuditLog
from apps.core.views import staff_required
from apps.family.models import Person

from .report_export import build_report_workbook
from .reports import (
    GROUP_CHOICES, MONTH_NAMES, available_years, calendar_year_for, category_breakdown,
    category_matrix, default_year, month_bounds, monthly_summary, top_transactions,
    with_comparison, year_bounds, year_label, yearly_summary,
)

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GROUP_TITLES = {
    "income": "Income", "expense": "Expenses", "investment": "Investments",
    "loan": "Loans", "other": "Other", "transfer": "Transfers", "uncategorised": "Uncategorised",
}


def _number(value, default=None, low=None, high=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if (low is not None and number < low) or (high is not None and number > high):
        return default
    return number


def _filters(request):
    basis = request.GET.get("basis", request.POST.get("basis", "fy"))
    if basis not in ("fy", "calendar"):
        basis = "fy"
    person = _number(request.GET.get("person", request.POST.get("person")))
    account = _number(request.GET.get("account", request.POST.get("account")))
    return basis, person, account


def _year_choices(basis, person_id, account_id, chosen):
    years = set(available_years(basis, person_id, account_id))
    years.add(default_year(basis))
    years.add(chosen)
    return [{"value": y, "label": year_label(y, basis)} for y in sorted(years, reverse=True)]


@staff_required
def report_summary(request):
    basis, person_id, account_id = _filters(request)
    view = request.GET.get("view", "monthly")
    if view not in ("monthly", "yearly"):
        view = "monthly"
    year = _number(request.GET.get("year"), default_year(basis))

    if view == "monthly":
        rows, totals = monthly_summary(year, basis, person_id, account_id)
        labels = [row["chart_label"] for row in rows]
    else:
        rows, totals = yearly_summary(basis, person_id, account_id), None
        labels = [row["label"] for row in rows]
    chart = {
        "labels": labels,
        "income": [float(row["income"]) for row in rows],
        "expenses": [float(row["expenses"]) for row in rows],
        "invested": [float(row["invested"]) for row in rows],
    }
    uncategorised = totals["uncategorised_count"] if totals else sum(r["uncategorised_count"] for r in rows)
    return render(request, "wealth/report_summary.html", {
        "view": view, "basis": basis, "year": year, "year_label": year_label(year, basis),
        "years": _year_choices(basis, person_id, account_id, year),
        "rows": rows, "totals": totals, "chart": chart, "uncategorised": uncategorised,
        "people": Person.objects.all(), "person_id": person_id or "", "account_id": account_id or "",
    })


@staff_required
def report_categories(request):
    basis, person_id, account_id = _filters(request)
    group = request.GET.get("group", "expense")
    if group not in GROUP_CHOICES:
        group = "expense"
    year = _number(request.GET.get("year"), default_year(basis))
    month = _number(request.GET.get("month"), None, 1, 12)

    if month:
        calendar_year = calendar_year_for(year, month, basis)
        start, end = month_bounds(calendar_year, month)
        previous_year, previous_month = (calendar_year - 1, 12) if month == 1 else (calendar_year, month - 1)
        previous_start, previous_end = month_bounds(previous_year, previous_month)
        period_label = f"{MONTH_NAMES[month - 1]} {calendar_year}"
        compare_label = "previous month"
        matrix = None
    else:
        start, end = year_bounds(year, basis)
        previous_start, previous_end = year_bounds(year - 1, basis)
        period_label = year_label(year, basis)
        compare_label = "previous year"
        matrix = category_matrix(group, year, basis, person_id, account_id)

    items, total = category_breakdown(group, start, end, person_id, account_id)
    previous_items, previous_total = category_breakdown(group, previous_start, previous_end, person_id, account_id)
    items = with_comparison(items, previous_items)
    positive = [item for item in items if item["net"] > 0]
    chart = {
        "labels": [item["name"] for item in positive],
        "values": [float(item["net"]) for item in positive],
    }
    return render(request, "wealth/report_categories.html", {
        "group": group, "group_title": GROUP_TITLES[group],
        "groups": [(value, GROUP_TITLES[value]) for value in GROUP_CHOICES],
        "basis": basis, "year": year, "month": month or "",
        "years": _year_choices(basis, person_id, account_id, year),
        "months": [(index + 1, name) for index, name in enumerate(MONTH_NAMES)],
        "period_label": period_label, "compare_label": compare_label,
        "items": items, "total": total, "previous_total": previous_total,
        "matrix": matrix, "chart": chart,
        "top": top_transactions(group, start, end, person_id, account_id),
        "people": Person.objects.all(), "person_id": person_id or "", "account_id": account_id or "",
        "is_income": group == "income",
    })


@staff_required
@require_POST
def report_export(request):
    basis, person_id, account_id = _filters(request)
    year = _number(request.POST.get("year"), default_year(basis))
    data = build_report_workbook(year, basis, person_id, account_id)
    log_event(AuditLog.Action.EXPORT, note=f"Report export: {year_label(year, basis)}")
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    response = HttpResponse(data, content_type=XLSX_TYPE)
    response["Content-Disposition"] = f'attachment; filename="sarthi_report_{year}_{stamp}.xlsx"'
    response["Cache-Control"] = "private, no-store"
    return response
