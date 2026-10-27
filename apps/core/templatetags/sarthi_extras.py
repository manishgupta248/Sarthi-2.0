from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def inr(value):
    """12345678.5 becomes the Indian style amount: rupee sign, 1,23,45,678.50."""
    if value is None or value == "":
        return "-"
    try:
        amount = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = "-" if amount < 0 else ""
    whole, _, fraction = f"{abs(amount):.2f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return f"{sign}\u20b9{whole}.{fraction}"


@register.filter
def mask_last4(value):
    """Shows only the last 4 characters of a number."""
    if not value:
        return "-"
    return "XXXXXX" + str(value)
