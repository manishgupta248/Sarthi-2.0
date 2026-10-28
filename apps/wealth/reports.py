"""Income, expense and investment reports built from transactions.

Category groups decide where a transaction counts:
  income      -> Income (money in minus money out)
  expense     -> Expenses (money out minus money in, so refunds reduce expenses)
  investment  -> Invested (money out minus money in)
  transfer    -> left out (money moving between your own accounts)
  loan, other and uncategorised -> shown separately so nothing is hidden

basis "fy" = Indian financial year (April to March); a year value means the year it STARTS in.
basis "calendar" = January to December.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth, ExtractYear

from .models import Transaction

ZERO = Decimal("0.00")
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
GROUP_CHOICES = ["income", "expense", "investment", "loan", "other", "transfer", "uncategorised"]


# ---------- periods ----------

def current_fy_start(today=None):
    today = today or date.today()
    return today.year if today.month >= 4 else today.year - 1


def default_year(basis, today=None):
    today = today or date.today()
    return current_fy_start(today) if basis == "fy" else today.year


def year_label(year, basis):
    return f"FY {year}-{str(year + 1)[-2:]}" if basis == "fy" else str(year)


def year_months(year, basis):
    if basis == "fy":
        return [(year, month) for month in range(4, 13)] + [(year + 1, month) for month in range(1, 4)]
    return [(year, month) for month in range(1, 13)]


def month_bounds(year, month):
    start = date(year, month, 1)
    following = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, following - timedelta(days=1)


def year_bounds(year, basis):
    months = year_months(year, basis)
    return month_bounds(*months[0])[0], month_bounds(*months[-1])[1]


def calendar_year_for(year, month, basis):
    """In a financial year, January to March fall in the following calendar year."""
    return year + 1 if (basis == "fy" and month < 4) else year


def month_label(year, month):
    return f"{MONTH_NAMES[month - 1]} {str(year)[-2:]}"


# ---------- building blocks ----------

def amount_sum(direction, **condition):
    return Sum("amount", filter=Q(direction=direction, **condition))


def base_queryset(person_id=None, account_id=None):
    queryset = Transaction.objects.all()
    if person_id:
        queryset = queryset.filter(account__holder_id=person_id)
    if account_id:
        queryset = queryset.filter(account_id=account_id)
    return queryset


def _in_range(queryset, start, end):
    return queryset.filter(date__gte=start, date__lte=end)


def _group_filter(queryset, group):
    if group == "uncategorised":
        return queryset.filter(category__isnull=True)
    return queryset.filter(category__group=group)


def _net(group, money_in, money_out):
    return (money_in - money_out) if group == "income" else (money_out - money_in)


# ---------- headline numbers ----------

def headline(queryset):
    data = queryset.aggregate(
        income_in=amount_sum("in", category__group="income"),
        income_out=amount_sum("out", category__group="income"),
        expense_in=amount_sum("in", category__group="expense"),
        expense_out=amount_sum("out", category__group="expense"),
        invest_in=amount_sum("in", category__group="investment"),
        invest_out=amount_sum("out", category__group="investment"),
        loan_in=amount_sum("in", category__group="loan"),
        loan_out=amount_sum("out", category__group="loan"),
        other_in=amount_sum("in", category__group="other"),
        other_out=amount_sum("out", category__group="other"),
        uncat_in=amount_sum("in", category__isnull=True),
        uncat_out=amount_sum("out", category__isnull=True),
        uncat_count=Count("id", filter=Q(category__isnull=True)),
        total_count=Count("id"),
    )
    value = {key: (amount or ZERO) for key, amount in data.items() if not key.endswith("_count")}
    income = value["income_in"] - value["income_out"]
    expenses = value["expense_out"] - value["expense_in"]
    invested = value["invest_out"] - value["invest_in"]
    leftover = income - expenses - invested
    return {
        "income": income,
        "expenses": expenses,
        "invested": invested,
        "leftover": leftover,
        "savings_rate": round(float(leftover / income * 100), 1) if income > 0 else None,
        "loans": value["loan_out"] - value["loan_in"],
        "unclassified": (value["other_out"] - value["other_in"]) + (value["uncat_out"] - value["uncat_in"]),
        "uncategorised_count": data["uncat_count"] or 0,
        "count": data["total_count"] or 0,
    }


def monthly_summary(year, basis, person_id=None, account_id=None):
    """One row per month of the year, plus the year's totals."""
    base = base_queryset(person_id, account_id)
    rows = []
    for calendar_year, month in year_months(year, basis):
        start, end = month_bounds(calendar_year, month)
        row = headline(_in_range(base, start, end))
        row.update({
            "year": year, "month": month,
            "label": f"{MONTH_NAMES[month - 1]} {calendar_year}",
            "chart_label": month_label(calendar_year, month),
        })
        rows.append(row)
    start, end = year_bounds(year, basis)
    return rows, headline(_in_range(base, start, end))


def available_years(basis, person_id=None, account_id=None):
    base = base_queryset(person_id, account_id)
    first = base.order_by("date").values_list("date", flat=True).first()
    last = base.order_by("-date").values_list("date", flat=True).first()
    if first is None:
        return []

    def start_year(day):
        if basis == "fy":
            return day.year if day.month >= 4 else day.year - 1
        return day.year

    return list(range(start_year(first), start_year(last) + 1))


def yearly_summary(basis, person_id=None, account_id=None):
    base = base_queryset(person_id, account_id)
    rows = []
    for year in available_years(basis, person_id, account_id):
        start, end = year_bounds(year, basis)
        row = headline(_in_range(base, start, end))
        row.update({"year": year, "label": year_label(year, basis)})
        rows.append(row)
    return rows


# ---------- category reports ----------

def category_breakdown(group, start, end, person_id=None, account_id=None):
    """Totals per category within a group for the period. Returns (rows, total)."""
    queryset = _group_filter(_in_range(base_queryset(person_id, account_id), start, end), group)
    grouped = (
        queryset.values("category__name")
        .annotate(money_in=amount_sum("in"), money_out=amount_sum("out"), count=Count("id"))
        .order_by()
    )
    items = []
    for row in grouped:
        money_in, money_out = row["money_in"] or ZERO, row["money_out"] or ZERO
        items.append({
            "name": row["category__name"] or "(Uncategorised)",
            "money_in": money_in,
            "money_out": money_out,
            "net": _net(group, money_in, money_out),
            "count": row["count"],
        })
    items.sort(key=lambda item: item["net"], reverse=True)
    total = sum((item["net"] for item in items), ZERO)
    for item in items:
        item["share"] = round(float(item["net"] / total * 100), 1) if total > 0 else 0
    return items, total


def with_comparison(items, previous_items):
    previous = {item["name"]: item["net"] for item in previous_items}
    for item in items:
        before = previous.get(item["name"], ZERO)
        item["previous"] = before
        item["change"] = item["net"] - before
        item["change_pct"] = round(float((item["net"] - before) / before * 100), 1) if before else None
    return items


def category_matrix(group, year, basis, person_id=None, account_id=None):
    """Categories down the side, the months of the year across the top."""
    months = year_months(year, basis)
    start, end = year_bounds(year, basis)
    queryset = _group_filter(_in_range(base_queryset(person_id, account_id), start, end), group)
    grouped = (
        queryset.annotate(y=ExtractYear("date"), m=ExtractMonth("date"))
        .values("category__name", "y", "m")
        .annotate(money_in=amount_sum("in"), money_out=amount_sum("out"))
        .order_by()
    )
    table = {}
    for row in grouped:
        name = row["category__name"] or "(Uncategorised)"
        net = _net(group, row["money_in"] or ZERO, row["money_out"] or ZERO)
        table.setdefault(name, {})[(row["y"], row["m"])] = net
    rows = []
    for name, cells in table.items():
        values = [cells.get(key, ZERO) for key in months]
        rows.append({"name": name, "values": values, "total": sum(values, ZERO)})
    rows.sort(key=lambda row: row["total"], reverse=True)
    totals = [sum((row["values"][index] for row in rows), ZERO) for index in range(len(months))]
    return {
        "columns": [month_label(y, m) for y, m in months],
        "rows": rows,
        "totals": totals,
        "grand_total": sum(totals, ZERO),
    }


def top_transactions(group, start, end, person_id=None, account_id=None, limit=10):
    """The largest individual items of the group in the period."""
    direction = "in" if group == "income" else "out"
    queryset = _group_filter(_in_range(base_queryset(person_id, account_id), start, end), group)
    return list(
        queryset.filter(direction=direction)
        .select_related("account", "account__holder", "category")
        .order_by("-amount", "-date")[:limit]
    )
