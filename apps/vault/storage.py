"""Encrypted file storage for the vault (data/vault/<xx>/<random>.bin)."""
import re
import uuid
from pathlib import Path

from django.conf import settings

from apps.core.exceptions import RecordNotFound, SarthiError
from apps.core.fields import decrypt_bytes, encrypt_bytes

STORED_PATH_RE = re.compile(r"^[0-9a-f]{2}/[0-9a-f]{32}\.bin$")


class VaultError(SarthiError):
    default_message = "The document vault reported a problem."
    status_code = 500


def vault_dir():
    folder = Path(settings.VAULT_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_encrypted(data):
    """Encrypt and store bytes under a random name. Returns the stored path."""
    token = uuid.uuid4().hex
    relative = f"{token[:2]}/{token}.bin"
    path = vault_dir() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(encrypt_bytes(data))
    partial.replace(path)
    return relative


def read_decrypted(relative):
    if not STORED_PATH_RE.match(relative):
        raise VaultError("The stored file reference is invalid.")
    path = vault_dir() / relative
    if not path.is_file():
        raise RecordNotFound("The stored file is missing from the vault.")
    return decrypt_bytes(path.read_bytes())
