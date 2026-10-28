import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.core.audit import log_event
from apps.core.models import AuditLog
from apps.core.views import staff_required
from apps.family.models import Person

from .export import build_accounts_workbook
from .forms import AccountDocumentForm, AccountForm, InstitutionForm, RemarkForm, SnapshotForm
from .models import Account, AccountType, BalanceSnapshot, Institution, Transaction
from .services import latest_snapshot_map, monthly_trend, wealth_summary
from .reconciliation import account_reconciliation

logger = logging.getLogger(__name__)
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_AMOUNT = Decimal("10") ** 13


def _safe_next(request, fallback_url_name):
    target = request.GET.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return reverse(fallback_url_name)


# ---------- Wealth dashboard ----------

@staff_required
def wealth_dashboard(request):
    summary = wealth_summary()
    positive_types = [item for item in summary["by_type"] if item["amount"] > 0]
    chart = {
        "types": {
            "labels": [item["name"] for item in positive_types],
            "values": [float(item["amount"]) for item in positive_types],
        },
        "people": {
            "labels": [item["name"] for item in summary["by_person"]],
            "values": [float(item["amount"]) for item in summary["by_person"]],
        },
        "trend": monthly_trend(),
    }
    return render(request, "wealth/dashboard.html", {"summary": summary, "chart": chart})


# ---------- Accounts ----------

@staff_required
def account_list(request):
    accounts = Account.objects.select_related("holder", "account_type", "institution")
    person_id = request.GET.get("person", "")
    type_id = request.GET.get("type", "")
    status = request.GET.get("status", "open")
    query = request.GET.get("q", "").strip()
    if person_id.isdigit():
        accounts = accounts.filter(holder_id=int(person_id))
    else:
        person_id = ""
    if type_id.isdigit():
        accounts = accounts.filter(account_type_id=int(type_id))
    else:
        type_id = ""
    if status == "open":
        accounts = accounts.filter(is_closed=False)
    elif status == "closed":
        accounts = accounts.filter(is_closed=True)
    else:
        status = "all"
    if query:
        accounts = accounts.filter(
            Q(nickname__icontains=query) | Q(institution__name__icontains=query)
            | Q(holder__full_name__icontains=query) | Q(account_number_last4__iexact=query)
        )
    latest = latest_snapshot_map()
    rows = [{"account": account, "latest": latest.get(account.pk)} for account in accounts]
    return render(request, "wealth/account_list.html", {
        "rows": rows,
        "people": Person.objects.all(),
        "types": AccountType.objects.all(),
        "selected_person": person_id,
        "selected_type": type_id,
        "selected_status": status,
        "query": query,
    })


@staff_required
def account_detail(request, pk):
    account = get_object_or_404(
        Account.objects.select_related("holder", "nominee", "account_type", "institution"), pk=pk
    )
    return render(request, "wealth/account_detail.html", {
        "account": account,
        "snapshots": BalanceSnapshot.objects.filter(account=account),
        "snapshot_form": SnapshotForm(account, initial={"as_of": date.today()}),
        "joint_holders": account.joint_holders.all(),
        "documents": account.documents.all(),
        "remarks": account.remark_entries.all(),
        "remark_form": RemarkForm(),
        "document_form": AccountDocumentForm(),
        "recent_transactions": Transaction.objects.filter(account=account).select_related("category")[:8],
        "estimate": account_reconciliation(account),
    })


@staff_required
def account_edit(request, pk=None):
    account = get_object_or_404(Account, pk=pk) if pk else None
    form = AccountForm(request.POST or None, instance=account)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Saved {saved.display_name}.")
        return redirect("account_detail", pk=saved.pk)
    add_institution = reverse("institution_add") + "?next=" + quote(request.get_full_path())
    return render(request, "wealth/simple_form.html", {
        "heading": f"Edit {account.display_name}" if account else "Add an account",
        "form": form,
        "back_url": reverse("account_detail", args=[account.pk]) if account else reverse("account_list"),
        "help_url": add_institution,
        "help_text": "Institution not in the list? Add it first.",
    })


@staff_required
@require_POST
def account_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    account.delete()
    messages.success(request, f"{account.display_name} was archived. An administrator can restore it.")
    return redirect("account_list")


@staff_required
@require_POST
def account_reveal(request, pk):
    """Shows the full number for a short time. Every reveal is audited."""
    account = get_object_or_404(Account, pk=pk)
    log_event(
        AuditLog.Action.REVEAL,
        model_label="wealth.Account",
        object_id=account.pk,
        object_repr=str(account),
        note="Account number and customer ID revealed",
    )
    response = JsonResponse({
        "account_number": account.account_number,
        "customer_id": account.customer_id,
    })
    response["Cache-Control"] = "private, no-store"
    return response


# ---------- Balance snapshots ----------

@staff_required
@require_POST
def snapshot_add(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = SnapshotForm(account, request.POST)
    if form.is_valid():
        snapshot = form.save(commit=False)
        snapshot.account = account
        snapshot.save()
        messages.success(request, "Balance saved.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect("account_detail", pk=account.pk)


@staff_required
def snapshot_edit(request, pk):
    snapshot = get_object_or_404(BalanceSnapshot, pk=pk)
    form = SnapshotForm(snapshot.account, request.POST or None, instance=snapshot)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Balance updated.")
        return redirect("account_detail", pk=snapshot.account_id)
    return render(request, "wealth/simple_form.html", {
        "heading": f"Edit balance for {snapshot.account.display_name}",
        "form": form,
        "back_url": reverse("account_detail", args=[snapshot.account_id]),
    })


@staff_required
@require_POST
def snapshot_delete(request, pk):
    snapshot = get_object_or_404(BalanceSnapshot, pk=pk)
    account_id = snapshot.account_id
    snapshot.delete()
    messages.success(request, "Balance entry archived.")
    return redirect("account_detail", pk=account_id)


@staff_required
def update_balances(request):
    """One page to record today's balance for every open account."""
    accounts = list(
        Account.objects.filter(is_closed=False).select_related("holder", "institution", "account_type")
    )
    latest = latest_snapshot_map()
    rows = [{"account": account, "latest": latest.get(account.pk), "entered": ""} for account in accounts]
    as_of_text = request.POST.get("as_of") or date.today().isoformat()

    if request.method == "POST":
        errors, entries = [], []
        as_of = None
        try:
            as_of = date.fromisoformat(as_of_text)
            if as_of > date.today():
                errors.append("The date cannot be in the future.")
        except ValueError:
            errors.append("Enter a valid date.")
        for row in rows:
            raw = request.POST.get(f"amount_{row['account'].pk}", "").strip()
            row["entered"] = raw
            if not raw:
                continue
            try:
                amount = Decimal(raw.replace(",", "")).quantize(Decimal("0.01"))
            except InvalidOperation:
                errors.append(f"{row['account'].display_name}: '{raw}' is not a valid amount.")
                continue
            if abs(amount) >= MAX_AMOUNT:
                errors.append(f"{row['account'].display_name}: the amount is too large.")
                continue
            entries.append((row["account"], amount))
        if not errors and not entries:
            errors.append("Enter at least one balance.")
        if not errors:
            with transaction.atomic():
                for account, amount in entries:
                    snapshot = BalanceSnapshot.objects.filter(account=account, as_of=as_of).first()
                    if snapshot:
                        snapshot.amount = amount
                        snapshot.save()
                    else:
                        BalanceSnapshot.objects.create(account=account, as_of=as_of, amount=amount)
            messages.success(request, f"Saved {len(entries)} balance(s) as of {as_of:%d-%m-%Y}.")
            return redirect("wealth_dashboard")
        for error in errors:
            messages.error(request, error)
    return render(request, "wealth/update_balances.html", {"rows": rows, "as_of": as_of_text})


# ---------- Institutions ----------

@staff_required
def institution_list(request):
    return render(request, "wealth/institution_list.html", {
        "institutions": Institution.objects.all(),
    })


@staff_required
def institution_edit(request, pk=None):
    institution = get_object_or_404(Institution, pk=pk) if pk else None
    form = InstitutionForm(request.POST or None, instance=institution)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Saved {saved.name}.")
        return redirect(_safe_next(request, "institution_list"))
    return render(request, "wealth/simple_form.html", {
        "heading": f"Edit {institution.name}" if institution else "Add an institution",
        "form": form,
        "back_url": _safe_next(request, "institution_list"),
    })


@staff_required
@require_POST
def institution_delete(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    if Account.objects.filter(institution=institution).exists():
        messages.error(request, "This institution is used by accounts, so it cannot be archived.")
    else:
        institution.delete()
        messages.success(request, f"{institution.name} was archived.")
    return redirect("institution_list")


# ---------- Excel export ----------

@staff_required
def export_accounts(request):
    if request.method == "POST":
        full = request.POST.get("full") == "1"
        data = build_accounts_workbook(include_sensitive=full)
        log_event(
            AuditLog.Action.EXPORT,
            note="Accounts export: " + ("FULL details" if full else "masked"),
        )
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        response = HttpResponse(data, content_type=XLSX_TYPE)
        response["Content-Disposition"] = f'attachment; filename="sarthi_accounts_{stamp}.xlsx"'
        response["Cache-Control"] = "private, no-store"
        return response
    return render(request, "wealth/export.html")


