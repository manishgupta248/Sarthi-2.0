"""Wealth calculations. Amounts are Decimal; floats are used only for charts."""
from bisect import bisect_right
from datetime import date, timedelta
from decimal import Decimal

from .models import Account, BalanceSnapshot

ZERO = Decimal("0.00")
STALE_DAYS = 90


def latest_snapshot_map():
    """account id -> its newest balance snapshot."""
    latest = {}
    for snapshot in BalanceSnapshot.objects.order_by("account_id", "-as_of", "-id"):
        latest.setdefault(snapshot.account_id, snapshot)
    return latest


def _shares(values, total):
    items = []
    for name, amount in sorted(values.items(), key=lambda item: item[1], reverse=True):
        share = round(float(amount / total * 100), 1) if total else 0
        items.append({"name": name, "amount": amount, "share": share})
    return items


def wealth_summary(today=None):
    """Totals over OPEN accounts, using each account's latest balance.

    A joint account is counted once, under its main holder.
    """
    today = today or date.today()
    accounts = list(
        Account.objects.filter(is_closed=False).select_related("holder", "account_type", "institution")
    )
    latest = latest_snapshot_map()
    total = ZERO
    people, kinds = {}, {}
    rows, attention = [], []
    for account in accounts:
        snapshot = latest.get(account.pk)
        amount = snapshot.amount if snapshot else ZERO
        total += amount
        holder_name = account.holder.full_name
        people[holder_name] = people.get(holder_name, ZERO) + amount
        type_name = account.account_type.name
        kinds[type_name] = kinds.get(type_name, ZERO) + amount
        status = ""
        if snapshot is None:
            status = "missing"
            attention.append({"account": account, "reason": "No balance recorded yet"})
        else:
            age = (today - snapshot.as_of).days
            if age > STALE_DAYS:
                status = "stale"
                attention.append({"account": account, "reason": f"Last balance is {age} days old"})
        rows.append({
            "account": account,
            "amount": amount,
            "as_of": snapshot.as_of if snapshot else None,
            "status": status,
        })
    return {
        "total": total,
        "rows": rows,
        "attention": attention,
        "by_person": _shares(people, total),
        "by_type": _shares(kinds, total),
    }


def _month_end_points(today, months):
    points = set()
    for offset in range(months):
        year, month = today.year, today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        points.add(min(date(next_year, next_month, 1) - timedelta(days=1), today))
    return sorted(points)


def monthly_trend(months=12, today=None):
    """Total of all accounts at each month end (the latest balance on or before that day)."""
    today = today or date.today()
    accounts = list(Account.objects.all())
    history = {}
    for snapshot in BalanceSnapshot.objects.order_by("as_of", "id"):
        history.setdefault(snapshot.account_id, []).append(snapshot)
    dates = {account_id: [item.as_of for item in items] for account_id, items in history.items()}

    labels, values = [], []
    for point in _month_end_points(today, months):
        total = ZERO
        for account in accounts:
            if account.is_closed and not (account.closed_on and point <= account.closed_on):
                continue
            items = history.get(account.pk, [])
            index = bisect_right(dates.get(account.pk, []), point)
            if index:
                total += items[index - 1].amount
        labels.append(point.strftime("%b %Y"))
        values.append(float(total))
    return {"labels": labels, "values": values}
