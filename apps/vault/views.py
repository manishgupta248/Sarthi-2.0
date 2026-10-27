import hashlib
import io
from datetime import date, timedelta
from pathlib import Path

from django.contrib import messages
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import get_valid_filename
from django.views.decorators.http import require_POST

from apps.core.audit import log_event
from apps.core.exceptions import SarthiError
from apps.core.models import AuditLog
from apps.core.views import staff_required
from apps.family.models import Person

from .forms import DocumentEditForm, UploadForm
from .models import Document
from .storage import VaultError, read_decrypted, save_encrypted
from .validators import check_upload

INLINE_TYPES = {"application/pdf", "image/jpeg", "image/png"}
EXPIRY_WARNING_DAYS = 60


def _clean_name(raw):
    try:
        return get_valid_filename(Path(raw).name)[:200]
    except SuspiciousFileOperation:
        return "document"


@staff_required
def document_list(request):
    documents = Document.objects.select_related("person")
    person_id = request.GET.get("person", "")
    doc_type = request.GET.get("type", "")
    if person_id.isdigit():
        documents = documents.filter(person_id=int(person_id))
    else:
        person_id = ""
    if doc_type in Document.DocType.values:
        documents = documents.filter(doc_type=doc_type)
    else:
        doc_type = ""

    today = date.today()
    rows = list(documents)
    for row in rows:
        row.expiry_status = ""
        if row.expiry_date:
            if row.expiry_date < today:
                row.expiry_status = "expired"
            elif row.expiry_date <= today + timedelta(days=EXPIRY_WARNING_DAYS):
                row.expiry_status = "soon"
            else:
                row.expiry_status = "ok"
    return render(request, "vault/document_list.html", {
        "documents": rows,
        "people": Person.objects.all(),
        "types": Document.DocType.choices,
        "selected_person": person_id,
        "selected_type": doc_type,
    })


@staff_required
def document_upload(request):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["file"]
        try:
            data = upload.read()
            content_type = check_upload(upload.name, data)
            stored_path = save_encrypted(data)
        except SarthiError as exc:
            form.add_error("file", exc.message)
        else:
            original = _clean_name(upload.name) or "document"
            document = Document.objects.create(
                title=form.cleaned_data["title"] or Path(original).stem[:200] or "Document",
                doc_type=form.cleaned_data["doc_type"],
                person=form.cleaned_data["person"],
                notes=form.cleaned_data["notes"],
                expiry_date=form.cleaned_data["expiry_date"],
                original_name=original,
                content_type=content_type,
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                stored_path=stored_path,
                uploaded_by=request.user,
            )
            messages.success(request, f"Stored and encrypted: {document.title}")
            return redirect("vault_list")
    return render(request, "vault/document_form.html", {"form": form, "is_upload": True})


@staff_required
def document_edit(request, pk):
    document = get_object_or_404(Document, pk=pk)
    form = DocumentEditForm(request.POST or None, instance=document)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Saved {document.title}.")
        return redirect("vault_list")
    return render(request, "vault/document_form.html", {
        "form": form, "is_upload": False, "document": document,
    })


@staff_required
def document_download(request, pk):
    document = get_object_or_404(Document, pk=pk)
    data = read_decrypted(document.stored_path)
    if hashlib.sha256(data).hexdigest() != document.sha256:
        raise VaultError("The stored file failed its integrity check. It may be damaged.")
    log_event(
        AuditLog.Action.DOWNLOAD,
        model_label="vault.Document",
        object_id=document.pk,
        object_repr=document.title,
    )
    inline = document.content_type in INLINE_TYPES and not request.GET.get("save")
    response = FileResponse(
        io.BytesIO(data),
        content_type=document.content_type,
        as_attachment=not inline,
        filename=document.original_name,
    )
    response["Cache-Control"] = "private, no-store"
    return response


@staff_required
@require_POST
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)
    document.delete()
    messages.success(request, f"{document.title} was archived. The encrypted file is kept.")
    return redirect("vault_list")
