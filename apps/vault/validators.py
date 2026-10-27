"""Checks every upload before it is accepted."""
import io
import zipfile
from pathlib import Path

from django.conf import settings

from apps.core.exceptions import ValidationFailed

MB = 1024 * 1024
MAX_UNZIPPED_BYTES = 200 * MB
ALLOWED_TEXT = "PDF, JPG, PNG, Word (.docx) and Excel (.xlsx)"

# extension -> (first bytes of a genuine file, content type we will serve)
SIMPLE_TYPES = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
}
# extension -> (a part every genuine file contains, content type)
OFFICE_TYPES = {
    ".docx": ("word/document.xml",
              "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ".xlsx": ("xl/workbook.xml",
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}


def check_upload(filename, data):
    """Return the content type to use, or raise ValidationFailed with a plain message."""
    limit_mb = settings.VAULT_MAX_UPLOAD_MB
    if not data:
        raise ValidationFailed("The file is empty.")
    if len(data) > limit_mb * MB:
        raise ValidationFailed(f"The file is larger than {limit_mb} MB.")
    extension = Path(filename).suffix.lower()
    if extension in SIMPLE_TYPES:
        magic, content_type = SIMPLE_TYPES[extension]
        if not data.startswith(magic):
            raise ValidationFailed("The file content does not match its file type.")
        return content_type
    if extension in OFFICE_TYPES:
        required_part, content_type = OFFICE_TYPES[extension]
        _check_office_file(data, required_part)
        return content_type
    raise ValidationFailed(f"This file type is not allowed. Allowed: {ALLOWED_TEXT}.")


def _check_office_file(data, required_part):
    if not data.startswith(b"PK\x03\x04"):
        raise ValidationFailed("This is not a real Word or Excel file.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            infos = bundle.infolist()
    except zipfile.BadZipFile:
        raise ValidationFailed("The Word or Excel file is damaged.")
    names = [info.filename for info in infos]
    if "[Content_Types].xml" not in names or required_part not in names:
        raise ValidationFailed("This is not a real Word or Excel file.")
    if any(name.lower().endswith("vbaproject.bin") for name in names):
        raise ValidationFailed("Files that contain macros are not allowed.")
    if sum(info.file_size for info in infos) > MAX_UNZIPPED_BYTES:
        raise ValidationFailed("The file expands to an unsafe size.")
