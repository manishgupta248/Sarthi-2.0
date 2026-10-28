from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth, ExtractYear
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.views import staff_required
from apps.family.models import Person

from .forms import CategoryForm, TransactionForm, TransferForm
from .models import Account, Transaction, TransactionCategory
from .reconciliation import account_reconciliation
from .reports import MONTH_NAMES, amount_sum, year_bounds

ZERO = Decimal("0.00")


# ---------- transaction list with month and year browsing ----------

@staff_required
def transaction_list(request):
    today = date.today()
    params = request.GET
    selected = {key: params.get(key, "") for key in
                ("account", "person", "category", "direction", "date_from", "date_to")}

    items = Transaction.objects.select_related(
        "account", "account__holder", "account__institution", "account__account_type", "category"
    )
    if selected["account"].isdigit():
        items = items.filter(account_id=int(selected["account"]))
    else:
        selected["account"] = ""
    if selected["person"].isdigit():
        items = items.filter(account__holder_id=int(selected["person"]))
    else:
        selected["person"] = ""
    if selected["category"].isdigit():
        items = items.filter(category_id=int(selected["category"]))
    elif selected["category"] == "none":
        items = items.filter(category__isnull=True)
    else:
        selected["category"] = ""
    if selected["direction"] in ("in", "out"):
        items = items.filter(direction=selected["direction"])
    else:
        selected["direction"] = ""
    has_range = False
    for key, lookup in (("date_from", "date__gte"), ("date_to", "date__lte")):
        try:
            items = items.filter(**{lookup: date.fromisoformat(selected[key])})
            has_range = True
        except ValueError:
            selected[key] = ""

    # Period: a custom date range wins; otherwise a year/month; "all" shows everything;
    # with no choice at all the page opens on the current month.
    all_time = params.get("period") == "all" and not has_range
    year = month = None
    if not has_range and not all_time:
        if params.get("year", "").isdigit():
            year = int(params["year"])
            if params.get("month", "").isdigit() and 1 <= int(params["month"]) <= 12:
                month = int(params["month"])
        else:
            year, month = today.year, today.month

    other = params.copy()
    for key in ("year", "month", "period", "page", "date_from", "date_to"):
        other.pop(key, None)

    def link(**extra):
        query = other.copy()
        for key, value in extra.items():
            query[key] = value
        text = query.urlencode()
        return "?" + text if text else "?"

    year_set = {day.year for day in items.dates("date", "year")} | {today.year}
    month_counts = {}
    if year:
        start, end = year_bounds(year, "calendar")
        year_set.add(year)
        month_counts = {
            row["m"]: row["c"]
            for row in items.filter(date__gte=start, date__lte=end)
            .annotate(m=ExtractMonth("date")).values("m").annotate(c=Count("id")).order_by()
        }
    if year and month:
        items = items.filter(date__year=year, date__month=month)
        period_label = f"{MONTH_NAMES[month - 1]} {year}"
    elif year:
        items = items.filter(date__year=year)
        period_label = str(year)
    elif has_range:
        period_label = "Custom date range"
    else:
        period_label = "All time"

    nav = {
        "years": [{"year": y, "url": link(year=y), "active": year == y}
                  for y in sorted(year_set, reverse=True)],
        "all_url": link(period="all"),
        "all_active": all_time,
        "year_url": link(year=year) if year else "",
        "month_active": month,
        "months": [
            {"label": MONTH_NAMES[m - 1], "url": link(year=year, month=m),
             "active": month == m, "count": month_counts.get(m, 0)}
            for m in range(1, 13)
        ] if year else [],
    }

    totals = items.aggregate(money_in=amount_sum("in"), money_out=amount_sum("out"))
    money_in = totals["money_in"] or ZERO
    money_out = totals["money_out"] or ZERO
    page = Paginator(items, 50).get_page(params.get("page"))
    page_query = params.copy()
    page_query.pop("page", None)
    return render(request, "wealth/transaction_list.html", {
        "page": page,
        "selected": selected,
        "nav": nav,
        "period_label": period_label,
        "money_in": money_in,
        "money_out": money_out,
        "net": money_in - money_out,
        "accounts": Account.objects.select_related("holder", "institution", "account_type"),
        "people": Person.objects.all(),
        "categories": TransactionCategory.objects.all(),
        "base_query": (page_query.urlencode() + "&") if page_query else "",
    })


@staff_required
def transaction_archive(request):
    """Every year and month that has transactions, with counts and totals."""
    queryset = Transaction.objects.all()
    person = request.GET.get("person", "")
    suffix = ""
    if person.isdigit():
        queryset = queryset.filter(account__holder_id=int(person))
        suffix = f"&person={int(person)}"
    else:
        person = ""
    grouped = (
        queryset.annotate(y=ExtractYear("date"), m=ExtractMonth("date"))
        .values("y", "m")
        .annotate(money_in=amount_sum("in"), money_out=amount_sum("out"), count=Count("id"))
        .order_by("-y", "-m")
    )
    years = []
    for row in grouped:
        money_in, money_out = row["money_in"] or ZERO, row["money_out"] or ZERO
        if not years or years[-1]["year"] != row["y"]:
            years.append({"year": row["y"], "count": 0, "money_in": ZERO, "money_out": ZERO, "months": []})
        entry = years[-1]
        entry["count"] += row["count"]
        entry["money_in"] += money_in
        entry["money_out"] += money_out
        entry["months"].append({
            "month": row["m"], "label": MONTH_NAMES[row["m"] - 1], "count": row["count"],
            "money_in": money_in, "money_out": money_out, "net": money_in - money_out,
        })
    for entry in years:
        entry["net"] = entry["money_in"] - entry["money_out"]
    return render(request, "wealth/transaction_archive.html", {
        "years": years, "people": Person.objects.all(), "selected_person": person, "suffix": suffix,
    })


# ---------- entering transactions ----------

@staff_required
def transaction_edit(request, pk=None):
    item = get_object_or_404(Transaction, pk=pk) if pk else None
    initial = {}
    if item is None:
        initial["date"] = date.today()
        preselect = request.GET.get("account", "")
        if preselect.isdigit():
            initial["account"] = int(preselect)
    form = TransactionForm(request.POST or None, instance=item, initial=initial)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, "Transaction saved.")
        return redirect("account_detail", pk=saved.account_id)
    back = f"/wealth/accounts/{item.account_id}/" if item else "/wealth/transactions/"
    return render(request, "wealth/simple_form.html", {
        "heading": "Edit transaction" if item else "Add a transaction",
        "form": form,
        "back_url": back,
        "help_url": "/wealth/transactions/transfer/" if not item else "",
        "help_text": "Moving money between your own accounts? Use the Transfer form instead.",
    })


@staff_required
@require_POST
def transaction_delete(request, pk):
    item = get_object_or_404(Transaction, pk=pk)
    account_id = item.account_id
    item.delete()
    messages.success(request, "Transaction archived.")
    return redirect("account_detail", pk=account_id)


@staff_required
def transfer_add(request):
    form = TransferForm(request.POST or None, initial={"date": date.today()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        category = TransactionCategory.objects.get_or_create(
            name="Transfer", defaults={"sort_order": 50, "group": "transfer"}
        )[0]
        text = data["description"] or "Transfer between own accounts"
        source, target = data["from_account"], data["to_account"]
        with db_transaction.atomic():
            Transaction.objects.create(
                account=source, date=data["date"], direction=Transaction.Direction.OUT,
                amount=data["amount"], category=category, description=text,
                counterparty=target.display_name,
            )
            Transaction.objects.create(
                account=target, date=data["date"], direction=Transaction.Direction.IN,
                amount=data["amount"], category=category, description=text,
                counterparty=source.display_name,
            )
        messages.success(request, "Transfer recorded as two entries (money out and money in).")
        return redirect("transaction_list")
    return render(request, "wealth/simple_form.html", {
        "heading": "Transfer between your own accounts",
        "form": form,
        "back_url": "/wealth/transactions/",
    })


@staff_required
def account_reconciliation_page(request, pk):
    account = get_object_or_404(
        Account.objects.select_related("holder", "institution", "account_type"), pk=pk
    )
    result = account_reconciliation(account)
    return render(request, "wealth/reconciliation.html", {
        "account": account,
        "result": result,
        "periods": list(reversed(result["periods"])),
    })


# ---------- categories ----------

@staff_required
def category_list(request):
    return render(request, "wealth/category_list.html", {
        "categories": TransactionCategory.objects.annotate(uses=Count("transactions")),
    })


@staff_required
def category_edit(request, pk=None):
    category = get_object_or_404(TransactionCategory, pk=pk) if pk else None
    form = CategoryForm(request.POST or None, instance=category)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Saved {saved.name}.")
        return redirect("category_list")
    return render(request, "wealth/simple_form.html", {
        "heading": f"Edit {category.name}" if category else "Add a category",
        "form": form,
        "back_url": "/wealth/categories/",
    })


@staff_required
@require_POST
def category_delete(request, pk):
    category = get_object_or_404(TransactionCategory, pk=pk)
    uses = Transaction.objects.filter(category=category).count()
    if uses:
        messages.error(request, f"{category.name} is used by {uses} transaction(s). Edit it instead of archiving.")
    else:
        category.delete()
        messages.success(request, f"{category.name} was archived.")
    return redirect("category_list")
