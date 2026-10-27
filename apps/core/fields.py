"""Encryption for sensitive text and files (key: FIELD_ENCRYPTION_KEY in .env).

Encrypted fields cannot be searched or filtered in the database. That is the price of privacy.
"""
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.db import models

from .exceptions import ConfigurationError


def _cipher():
    keys = [settings.FIELD_ENCRYPTION_KEY, *settings.FIELD_ENCRYPTION_OLD_KEYS]
    keys = [key.strip() for key in keys if key and key.strip()]
    if not keys:
        raise ConfigurationError("FIELD_ENCRYPTION_KEY is missing in .env.")
    try:
        return MultiFernet([Fernet(key.encode()) for key in keys])
    except ValueError as exc:
        raise ConfigurationError("A field encryption key in .env is not valid.") from exc


def encrypt_bytes(data):
    return _cipher().encrypt(data)


def decrypt_bytes(token):
    try:
        return _cipher().decrypt(token)
    except InvalidToken as exc:
        raise ConfigurationError(
            "Could not decrypt stored data. The encryption key is wrong or the data is damaged."
        ) from exc


def encrypt_text(text):
    return encrypt_bytes(text.encode("utf-8")).decode("ascii")


def decrypt_text(token):
    return decrypt_bytes(token.encode("ascii")).decode("utf-8")


class EncryptedTextField(models.TextField):
    """Text that is stored encrypted in the database and readable in the app."""

    description = "Text stored encrypted"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt_text(value)

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return decrypt_text(value)
