"""Stores an uploaded file in the vault. Shared by the Vault page and other apps."""
import hashlib
from pathlib import Path

from django.core.exceptions import SuspiciousFileOperation
from django.utils.text import get_valid_filename

from .models import Document
from .storage import save_encrypted
from .validators import check_upload


def clean_filename(raw):
    try:
        return get_valid_filename(Path(raw).name)[:200]
    except SuspiciousFileOperation:
        return "document"


def store_document(upload, *, title="", doc_type=Document.DocType.OTHER, person=None,
                   notes="", expiry_date=None, user=None):
    """Check, encrypt and store an upload.

    Raises a SarthiError with a plain-English message if the file is refused.
    """
    data = upload.read()
    content_type = check_upload(upload.name, data)
    stored_path = save_encrypted(data)
    original = clean_filename(upload.name) or "document"
    return Document.objects.create(
        title=title or Path(original).stem[:200] or "Document",
        doc_type=doc_type,
        person=person,
        notes=notes,
        expiry_date=expiry_date,
        original_name=original,
        content_type=content_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        stored_path=stored_path,
        uploaded_by=user,
    )
