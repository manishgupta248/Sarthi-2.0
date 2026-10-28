from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.core.exceptions import SarthiError
from apps.core.views import staff_required
from apps.vault.models import Document
from apps.vault.services import store_document

from .forms import AccountDocumentForm, RemarkForm
from .models import Account, AccountRemark


def _show_errors(request, form):
    for errors in form.errors.values():
        for error in errors:
            messages.error(request, error)


@staff_required
@require_POST
def remark_add(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = RemarkForm(request.POST)
    if form.is_valid():
        remark = form.save(commit=False)
        remark.account = account
        remark.save()
        messages.success(request, "Remark added.")
    else:
        _show_errors(request, form)
    return redirect("account_detail", pk=account.pk)


@staff_required
@require_POST
def remark_delete(request, pk):
    remark = get_object_or_404(AccountRemark, pk=pk)
    account_id = remark.account_id
    remark.delete()
    messages.success(request, "Remark archived.")
    return redirect("account_detail", pk=account_id)


@staff_required
@require_POST
def account_document_upload(request, pk):
    """Uploads a file into the vault and links it to this account."""
    account = get_object_or_404(Account, pk=pk)
    form = AccountDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            document = store_document(
                form.cleaned_data["file"],
                title=form.cleaned_data["title"],
                doc_type=form.cleaned_data["doc_type"],
                person=account.holder,
                expiry_date=form.cleaned_data["expiry_date"],
                user=request.user,
            )
        except SarthiError as exc:
            messages.error(request, exc.message)
        else:
            account.documents.add(document)
            messages.success(request, f"Stored, encrypted and linked: {document.title}")
    else:
        _show_errors(request, form)
    return redirect("account_detail", pk=account.pk)


@staff_required
@require_POST
def account_document_unlink(request, pk, doc_pk):
    account = get_object_or_404(Account, pk=pk)
    document = get_object_or_404(Document, pk=doc_pk)
    account.documents.remove(document)
    messages.success(request, f"{document.title} was unlinked. It is still in the Document vault.")
    return redirect("account_detail", pk=account.pk)
