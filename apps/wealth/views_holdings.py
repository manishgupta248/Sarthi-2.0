from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction as db_transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.audit import log_event
from apps.core.exceptions import SarthiError
from apps.core.models import AuditLog
from apps.core.views import staff_required
from apps.family.models import Person
from apps.vault.models import Document
from apps.vault.services import store_document

from .forms import AccountDocumentForm
from .forms_holdings import HoldingForm, ValuationForm, field_labels
from .holding_export import build_holdings_workbook
from .models import LIABILITY_KINDS, Holding, HoldingValuation
from .networth import (
    FREQUENCY_MONTHS, ZERO, add_months, holding_attention, holding_value,
    net_worth_summary, net_worth_trend, upcoming_events, valuation_map,
)

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_AMOUNT = Decimal("10") ** 13


def _show_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


# ---------- net worth ----------

@staff_required
def networth_page(request):
    summary = net_worth_summary()
    positive = [part for part in summary["asset_parts"] if part["amount"] > 0]
    chart = {
        "trend": net_worth_trend(),
        "assets": {"labels": [p["label"] for p in positive], "values": [float(p["amount"]) for p in positive]},
    }
    return render(request, "wealth/networth.html", {
        "summary": summary,
        "chart": chart,
        "events": upcoming_events(),
        "attention": summary["bank"]["attention"] + holding_attention(summary["rows"]),
    })


# ---------- lists, details, editing ----------

@staff_required
def holding_list(request, liabilities=False):
    kinds = [value for value, _ in Holding.Kind.choices if (value in LIABILITY_KINDS) == liabilities]
    items = Holding.objects.filter(kind__in=kinds).select_related("holder", "institution")
    params = request.GET
    person, kind, status = params.get("person", ""), params.get("kind", ""), params.get("status", "active")
    if person.isdigit():
        items = items.filter(holder_id=int(person))
    else:
        person = ""
    if kind in kinds:
        items = items.filter(kind=kind)
    else:
        kind = ""
    if status == "closed":
        items = items.filter(status="closed")
    elif status == "all":
        pass
    else:
        status = "active"
        items = items.filter(status="active")

    today = date.today()
    valuations = valuation_map()
    rows, total = [], ZERO
    for holding in items:
        value = holding_value(holding, valuations.get(holding.pk, []), today)
        rows.append({"holding": holding, "value": value})
        if holding.status == "active":
            total += value.amount
    kind_choices = [(value, label) for value, label in Holding.Kind.choices if value in kinds]
    return render(request, "wealth/holding_list.html", {
        "rows": rows, "total": total, "liabilities": liabilities,
        "title": "Liabilities" if liabilities else "Investments and other assets",
        "kinds": kind_choices,
        "people": Person.objects.all(),
        "selected_person": person, "selected_kind": kind, "selected_status": status,
    })


@staff_required
def holding_detail(request, pk):
    holding = get_object_or_404(
        Holding.objects.select_related("holder", "joint_holder", "nominee", "institution"), pk=pk
    )
    valuations = list(HoldingValuation.objects.filter(holding=holding))
    oldest_first = sorted(valuations, key=lambda item: (item.as_of, item.pk))
    months = FREQUENCY_MONTHS.get(holding.installment_frequency or "monthly")
    return render(request, "wealth/holding_detail.html", {
        "holding": holding,
        "value": holding_value(holding, oldest_first, date.today()),
        "valuations": valuations,
        "valuation_form": ValuationForm(holding, initial={"as_of": date.today()}),
        "documents": holding.documents.all(),
        "document_form": AccountDocumentForm(),
        "labels": field_labels(holding.kind),
        "can_advance": bool(holding.next_due_date and months and holding.status == "active"),
    })


@staff_required
def holding_edit(request, kind=None, pk=None):
    if pk:
        holding = get_object_or_404(Holding, pk=pk)
        kind = holding.kind
    else:
        if kind not in Holding.Kind.values:
            raise Http404("Unknown type")
        holding = None
    form = HoldingForm(request.POST or None, instance=holding, kind=kind)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Saved {saved.display_name}.")
        return redirect("holding_detail", pk=saved.pk)
    label = dict(Holding.Kind.choices)[kind]
    back = f"/wealth/holdings/{holding.pk}/" if holding else (
        "/wealth/liabilities/" if kind in LIABILITY_KINDS else "/wealth/investments/"
    )
    return render(request, "wealth/simple_form.html", {
        "heading": f"Edit {holding.display_name}" if holding else f"Add: {label}",
        "form": form,
        "back_url": back,
    })


@staff_required
@require_POST
def holding_delete(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    holding.delete()
    messages.success(request, f"{holding.display_name} was archived. An administrator can restore it.")
    return redirect("liability_list" if holding.is_liability else "investment_list")


@staff_required
@require_POST
def holding_reveal(request, pk):
    """Shows the stored number for a short time. Every reveal is audited."""
    holding = get_object_or_404(Holding, pk=pk)
    log_event(
        AuditLog.Action.REVEAL,
        model_label="wealth.Holding",
        object_id=holding.pk,
        object_repr=str(holding),
        note="Policy, deposit or loan number revealed",
    )
    response = JsonResponse({"account_number": holding.identifier, "customer_id": ""})
    response["Cache-Control"] = "private, no-store"
    return response


@staff_required
@require_POST
def holding_advance_due(request, pk):
    """Moves the next due date forward by one payment period (after you pay)."""
    holding = get_object_or_404(Holding, pk=pk)
    months = FREQUENCY_MONTHS.get(holding.installment_frequency or "monthly")
    if not holding.next_due_date or not months:
        messages.error(request, "There is no repeating due date to move forward.")
    else:
        holding.next_due_date = add_months(holding.next_due_date, months)
        holding.save()
        messages.success(request, f"Next due date moved to {holding.next_due_date:%d-%m-%Y}.")
    return redirect("holding_detail", pk=holding.pk)


# ---------- recorded values ----------

@staff_required
@require_POST
def valuation_add(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    form = ValuationForm(holding, request.POST)
    if form.is_valid():
        valuation = form.save(commit=False)
        valuation.holding = holding
        valuation.save()
        messages.success(request, "Value saved.")
    else:
        _show_errors(request, form)
    return redirect("holding_detail", pk=holding.pk)


@staff_required
def valuation_edit(request, pk):
    valuation = get_object_or_404(HoldingValuation, pk=pk)
    form = ValuationForm(valuation.holding, request.POST or None, instance=valuation)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Value updated.")
        return redirect("holding_detail", pk=valuation.holding_id)
    return render(request, "wealth/simple_form.html", {
        "heading": f"Edit value for {valuation.holding.display_name}",
        "form": form,
        "back_url": f"/wealth/holdings/{valuation.holding_id}/",
    })


@staff_required
@require_POST
def valuation_delete(request, pk):
    valuation = get_object_or_404(HoldingValuation, pk=pk)
    holding_id = valuation.holding_id
    valuation.delete()
    messages.success(request, "Value entry archived.")
    return redirect("holding_detail", pk=holding_id)


@staff_required
def update_values(request):
    """One page to record today's value (or amount owed) for every active holding."""
    holdings = list(Holding.objects.filter(status="active").select_related("holder", "institution"))
    valuations = valuation_map()
    today = date.today()
    rows = [{
        "holding": holding,
        "latest": holding_value(holding, valuations.get(holding.pk, []), today),
        "entered": "",
    } for holding in holdings]
    as_of_text = request.POST.get("as_of") or today.isoformat()

    if request.method == "POST":
        errors, entries = [], []
        as_of = None
        try:
            as_of = date.fromisoformat(as_of_text)
            if as_of > today:
                errors.append("The date cannot be in the future.")
        except ValueError:
            errors.append("Enter a valid date.")
        for row in rows:
            raw = request.POST.get(f"amount_{row['holding'].pk}", "").strip()
            row["entered"] = raw
            if not raw:
                continue
            try:
                amount = Decimal(raw.replace(",", "")).quantize(Decimal("0.01"))
            except InvalidOperation:
                errors.append(f"{row['holding'].display_name}: '{raw}' is not a valid amount.")
                continue
            if abs(amount) >= MAX_AMOUNT:
                errors.append(f"{row['holding'].display_name}: the amount is too large.")
                continue
            entries.append((row["holding"], amount))
        if not errors and not entries:
            errors.append("Enter at least one value.")
        if not errors:
            with db_transaction.atomic():
                for holding, amount in entries:
                    existing = HoldingValuation.objects.filter(holding=holding, as_of=as_of).first()
                    if existing:
                        existing.amount = amount
                        existing.save()
                    else:
                        HoldingValuation.objects.create(holding=holding, as_of=as_of, amount=amount)
            messages.success(request, f"Saved {len(entries)} value(s) as of {as_of:%d-%m-%Y}.")
            return redirect("networth_page")
        for error in errors:
            messages.error(request, error)
    return render(request, "wealth/update_values.html", {"rows": rows, "as_of": as_of_text})


# ---------- documents ----------

@staff_required
@require_POST
def holding_document_upload(request, pk):
    holding = get_object_or_404(Holding, pk=pk)
    form = AccountDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            document = store_document(
                form.cleaned_data["file"],
                title=form.cleaned_data["title"],
                doc_type=form.cleaned_data["doc_type"],
                person=holding.holder,
                expiry_date=form.cleaned_data["expiry_date"],
                user=request.user,
            )
        except SarthiError as exc:
            messages.error(request, exc.message)
        else:
            holding.documents.add(document)
            messages.success(request, f"Stored, encrypted and linked: {document.title}")
    else:
        _show_errors(request, form)
    return redirect("holding_detail", pk=holding.pk)


@staff_required
@require_POST
def holding_document_unlink(request, pk, doc_pk):
    holding = get_object_or_404(Holding, pk=pk)
    document = get_object_or_404(Document, pk=doc_pk)
    holding.documents.remove(document)
    messages.success(request, f"{document.title} was unlinked. It is still in the Document vault.")
    return redirect("holding_detail", pk=holding.pk)


# ---------- Excel export ----------

@staff_required
def export_holdings(request):
    if request.method == "POST":
        full = request.POST.get("full") == "1"
        data = build_holdings_workbook(include_sensitive=full)
        log_event(
            AuditLog.Action.EXPORT,
            note="Investments export: " + ("FULL details" if full else "masked"),
        )
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
        response = HttpResponse(data, content_type=XLSX_TYPE)
        response["Content-Disposition"] = f'attachment; filename="sarthi_investments_{stamp}.xlsx"'
        response["Cache-Control"] = "private, no-store"
        return response
    return render(request, "wealth/export_holdings.html")
