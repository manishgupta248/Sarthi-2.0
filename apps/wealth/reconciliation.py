"""Checks recorded balances against recorded transactions.

Each recorded balance is a checkpoint, counted as of the END of its day.
Between two checkpoints: earlier balance + money in - money out should equal the later balance.
"""
from decimal import Decimal

from .models import BalanceSnapshot, Transaction

ZERO = Decimal("0.00")
TOLERANCE = Decimal("1.00")


def _totals(transactions):
    money_in = sum((t.amount for t in transactions if t.direction == Transaction.Direction.IN), ZERO)
    money_out = sum((t.amount for t in transactions if t.direction == Transaction.Direction.OUT), ZERO)
    return money_in, money_out


def account_reconciliation(account):
    snapshots = list(BalanceSnapshot.objects.filter(account=account).order_by("as_of", "id"))
    transactions = list(Transaction.objects.filter(account=account).order_by("date", "id"))

    periods = []
    for previous, current in zip(snapshots, snapshots[1:]):
        inside = [t for t in transactions if previous.as_of < t.date <= current.as_of]
        money_in, money_out = _totals(inside)
        expected = previous.amount + money_in - money_out
        difference = current.amount - expected
        periods.append({
            "start": previous,
            "end": current,
            "count": len(inside),
            "money_in": money_in,
            "money_out": money_out,
            "expected": expected,
            "difference": difference,
            "matches": abs(difference) < TOLERANCE,
        })

    latest = snapshots[-1] if snapshots else None
    since = [t for t in transactions if latest and t.date > latest.as_of]
    since_in, since_out = _totals(since)
    return {
        "periods": periods,
        "latest": latest,
        "since_count": len(since),
        "estimated": (latest.amount + since_in - since_out) if latest else None,
        "before_first_count": len([t for t in transactions if snapshots and t.date <= snapshots[0].as_of]),
        "no_balance_count": len(transactions) if not snapshots else 0,
    }


def mismatch_alerts(accounts):
    """Warnings for accounts where every transaction is recorded but the numbers do not add up."""
    alerts = []
    for account in accounts:
        if not account.full_tracking:
            continue
        periods = account_reconciliation(account)["periods"]
        if periods and not periods[-1]["matches"]:
            difference = periods[-1]["difference"]
            alerts.append({
                "account": account,
                "reason": f"Balance does not match the recorded transactions (difference {difference:+,.2f})",
            })
    return alerts
