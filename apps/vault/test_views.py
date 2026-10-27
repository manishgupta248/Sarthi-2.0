import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.core.models import AuditLog
from apps.vault.models import Document

CONTENT = b"%PDF-1.7 hello secret"


class VaultTests(TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.vault_dir = Path(tmp.name) / "vault"
        override = override_settings(
            VAULT_DIR=self.vault_dir, FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode()
        )
        override.enable()
        self.addCleanup(override.disable)
        User = get_user_model()
        User.objects.create_user(username="boss", password="Test-pass-12345", is_staff=True)
        User.objects.create_user(username="normal", password="Test-pass-12345")
        self.client.login(username="boss", password="Test-pass-12345")

    def _upload(self, content=CONTENT, name="statement.pdf"):
        return self.client.post("/vault/upload/", {
            "file": SimpleUploadedFile(name, content),
            "title": "Bank statement", "doc_type": "bank",
            "person": "", "notes": "", "expiry_date": "",
        })

    def test_upload_encrypts_the_file_on_disk(self):
        self.assertEqual(self._upload().status_code, 302)
        document = Document.objects.get()
        stored = (self.vault_dir / document.stored_path).read_bytes()
        self.assertNotIn(b"hello secret", stored)

    def test_download_returns_the_original_and_is_audited(self):
        self._upload()
        document = Document.objects.get()
        response = self.client.get(f"/vault/{document.pk}/download/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), CONTENT)
        self.assertTrue(AuditLog.objects.filter(action="download").exists())

    def test_bad_file_is_rejected_and_nothing_is_stored(self):
        response = self._upload(content=b"MZ\x90\x00", name="evil.exe")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Document.objects.count(), 0)

    def test_normal_user_cannot_download(self):
        self._upload()
        document = Document.objects.get()
        self.client.logout()
        self.client.login(username="normal", password="Test-pass-12345")
        self.assertEqual(self.client.get(f"/vault/{document.pk}/download/").status_code, 403)

    def test_archive_hides_document_but_keeps_the_file(self):
        self._upload()
        document = Document.objects.get()
        self.client.post(f"/vault/{document.pk}/delete/")
        self.assertEqual(Document.objects.count(), 0)
        self.assertTrue((self.vault_dir / document.stored_path).exists())
