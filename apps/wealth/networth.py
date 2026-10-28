"""Net worth: bank balances + investments and other assets - liabilities.

How a holding is valued on a date (first match wins):
  1. the latest value you recorded on or before that date          -> "recorded"
  2. fixed and recurring deposits: an estimate from rate and dates -> "estimated"
  3. bonds, loans given, gold, property, liabilities: original amount -> "cost"
  4. otherwise (for example insurance) no value                    -> "none"
"""
import calendar
from bisect import bisect_right
from collections import namedtuple
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from .models import Holding, HoldingValuation, LIABILITY_KINDS
from .services import _month_end_points, monthly_trend, wealth_summary

ZERO = Decimal("0.00")
FREQUENCY_MONTHS = {"monthly": 1, "quarterly": 3, "half_yearly": 6, "yearly": 12}
COMPOUNDING_PERIODS = {"monthly": 12, "quarterly": 4, "half_yearly": 2, "yearly": 1}
DEPOSIT_KINDS = ("fixed_deposit", "recurring_deposit")
COST_FALLBACK_KINDS = {"bond", "loan_given", "gold", "property", "other_asset"} | LIABILITY_KINDS
STALE_VALUE_DAYS = 180
MATURITY_WARNING_DAYS = 60
DUE_WARNING_DAYS = 30
KIND_LABEL = dict(Holding.Kind.choices)

Value = namedtuple("Value", "amount source as_of")


# ---------- dates ----------

def months_between(start, end):
    """Whole months from start to end."""
    return (end.year - start.year) * 12 + (end.month - start.month) - (1 if end.day < start.day else 0)


def add_months(day, months):
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


# ---------- values ----------

def _money(number):
    return Decimal(str(number)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def estimated_value(holding, on):
    """Estimated value of a fixed or recurring deposit on a date, or None."""
    start = holding.start_date
    if start is None or on < start:
        return None
    end = holding.end_date
    effective = min(on, end) if end else on
    rate = float(holding.interest_rate or 0) / 100

    if holding.kind == "fixed_deposit":
        if not holding.principal:
            return None
        if holding.interest_payout == "periodic":
            return holding.principal
        years = max((effective - start).days, 0) / 365
        principal = float(holding.principal)
        if holding.compounding == "simple":
            return _money(principal * (1 + rate * years))
        periods = COMPOUNDING_PERIODS.get(holding.compounding, 4)
        return _money(principal * (1 + rate / periods) ** (periods * years))

    if holding.kind == "recurring_deposit":
        if not holding.installment_amount:
            return None
        installment = float(holding.installment_amount)
        elapsed = months_between(start, effective)
        paid = elapsed + 1
        if end:
            paid = min(paid, months_between(start, end))
        total = 0.0
        for number in range(max(paid, 0)):
            total += installment * (1 + rate / 4) ** ((elapsed - number) / 3)
        return _money(total)
    return None


def is_active_on(holding, on):
    if holding.start_date and on < holding.start_date:
        return False
    if holding.status == "closed":
        return bool(holding.closed_on and on <= holding.closed_on)
    return True


def holding_value(holding, valuations, on):
    """Value of a holding on a date. valuations: its recorded values, oldest first."""
    index = bisect_right([item.as_of for item in valuations], on)
    if index:
        latest = valuations[index - 1]
        return Value(latest.amount, "recorded", latest.as_of)
    if holding.kind in DEPOSIT_KINDS:
        estimate = estimated_value(holding, on)
        if estimate is not None:
            return Value(estimate, "estimated", None)
        return Value(ZERO, "none", None)
    if holding.kind in COST_FALLBACK_KINDS and holding.principal is not None:
        return Value(holding.principal, "cost", None)
    return Value(ZERO, "none", None)


def valuation_map():
    """holding id -> its recorded values, oldest first."""
    result = {}
    for valuation in HoldingValuation.objects.order_by("as_of", "id"):
        result.setdefault(valuation.holding_id, []).append(valuation)
    return result


# ---------- net worth ----------

def _parts(pairs, total):
    return [
        {"label": label, "amount": amount,
         "share": round(float(amount / total * 100), 1) if total > 0 else 0}
        for label, amount in pairs
    ]


def net_worth_summary(today=None):
    today = today or date.today()
    bank = wealth_summary(today)
    valuations = valuation_map()
    assets = {"Bank accounts": bank["total"]}
    liabilities = {}
    people = {item["name"]: item["amount"] for item in bank["by_person"]}
    rows = []
    for holding in Holding.objects.select_related("holder", "institution"):
        if not is_active_on(holding, today):
            continue
        value = holding_value(holding, valuations.get(holding.pk, []), today)
        label, name = KIND_LABEL[holding.kind], holding.holder.full_name
        if holding.is_liability:
            liabilities[label] = liabilities.get(label, ZERO) + value.amount
            people[name] = people.get(name, ZERO) - value.amount
        else:
            assets[label] = assets.get(label, ZERO) + value.amount
            people[name] = people.get(name, ZERO) + value.amount
        rows.append({"holding": holding, "value": value.amount, "source": value.source, "as_of": value.as_of})

    asset_total = sum(assets.values(), ZERO)
    liability_total = sum(liabilities.values(), ZERO)
    ordered = lambda mapping: sorted(mapping.items(), key=lambda item: item[1], reverse=True)
    return {
        "assets_total": asset_total,
        "liabilities_total": liability_total,
        "net_worth": asset_total - liability_total,
        "asset_parts": _parts(ordered(assets), asset_total),
        "liability_parts": _parts(ordered(liabilities), liability_total),
        "people": [{"name": name, "amount": amount} for name, amount in ordered(people)],
        "rows": rows,
        "bank": bank,
    }


def net_worth_trend(months=12, today=None):
    """Net worth at each month end: bank balances + holdings - liabilities."""
    today = today or date.today()
    bank = monthly_trend(months, today)
    points = _month_end_points(today, months)
    holdings = list(Holding.objects.all())
    valuations = valuation_map()
    values = []
    for point, bank_value in zip(points, bank["values"]):
        total = Decimal(str(bank_value))
        for holding in holdings:
            if not is_active_on(holding, point):
                continue
            amount = holding_value(holding, valuations.get(holding.pk, []), point).amount
            total += -amount if holding.is_liability else amount
        values.append(float(total))
    return {"labels": bank["labels"], "values": values}


# ---------- upcoming dates and attention ----------

def _due_label(holding):
    if holding.kind == "insurance":
        return "Premium due"
    if holding.kind == "recurring_deposit":
        return "Instalment due"
    return "Payment (EMI) due"


def _end_label(holding):
    return {
        "fixed_deposit": "Matures", "recurring_deposit": "Matures", "bond": "Matures",
        "insurance": "Policy matures", "loan_given": "Repayment due",
    }.get(holding.kind, "Loan ends" if holding.is_liability else "Ends")


def upcoming_events(today=None):
    """Due dates and maturities coming up (or overdue) for active holdings, soonest first."""
    today = today or date.today()
    events = []
    for holding in Holding.objects.filter(status="active").select_related("holder", "institution"):
        if holding.next_due_date and holding.next_due_date <= today + timedelta(days=DUE_WARNING_DAYS):
            events.append(_event(holding, holding.next_due_date, _due_label(holding), today))
        if holding.end_date and holding.end_date <= today + timedelta(days=MATURITY_WARNING_DAYS):
            events.append(_event(holding, holding.end_date, _end_label(holding), today))
    events.sort(key=lambda item: item["date"])
    return events


def _event(holding, day, label, today):
    days = (day - today).days
    return {"holding": holding, "date": day, "days": days, "label": label, "overdue": days < 0}


def holding_attention(rows, today=None):
    """Holdings that need a value or an update."""
    today = today or date.today()
    items = []
    for row in rows:
        holding = row["holding"]
        if row["source"] == "none" and holding.kind != "insurance":
            items.append({"holding": holding, "reason": "No value recorded"})
        elif row["source"] == "recorded" and row["as_of"] and (today - row["as_of"]).days > STALE_VALUE_DAYS:
            items.append({
                "holding": holding,
                "reason": f"Value last updated {(today - row['as_of']).days} days ago",
            })
    return items
