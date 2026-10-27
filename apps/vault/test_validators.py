import io
import zipfile

from django.test import SimpleTestCase, override_settings

from apps.core.exceptions import ValidationFailed
from apps.vault.validators import check_upload


def make_zip(names):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as bundle:
        for name in names:
            bundle.writestr(name, "x")
    return buffer.getvalue()


class UploadCheckTests(SimpleTestCase):
    def test_real_pdf_is_accepted(self):
        self.assertEqual(check_upload("a.pdf", b"%PDF-1.7 content"), "application/pdf")

    def test_program_renamed_as_pdf_is_rejected(self):
        with self.assertRaises(ValidationFailed):
            check_upload("a.pdf", b"MZ\x90\x00program")

    def test_program_file_type_is_rejected(self):
        with self.assertRaises(ValidationFailed):
            check_upload("virus.exe", b"MZ\x90\x00program")

    def test_real_docx_is_accepted(self):
        data = make_zip(["[Content_Types].xml", "word/document.xml"])
        self.assertIn("wordprocessingml", check_upload("a.docx", data))

    def test_real_xlsx_is_accepted(self):
        data = make_zip(["[Content_Types].xml", "xl/workbook.xml"])
        self.assertIn("spreadsheetml", check_upload("a.xlsx", data))

    def test_docx_with_macros_is_rejected(self):
        data = make_zip(["[Content_Types].xml", "word/document.xml", "word/vbaProject.bin"])
        with self.assertRaises(ValidationFailed):
            check_upload("a.docx", data)

    def test_random_zip_renamed_as_xlsx_is_rejected(self):
        with self.assertRaises(ValidationFailed):
            check_upload("a.xlsx", make_zip(["hello.txt"]))

    def test_empty_file_is_rejected(self):
        with self.assertRaises(ValidationFailed):
            check_upload("a.pdf", b"")

    @override_settings(VAULT_MAX_UPLOAD_MB=1)
    def test_oversized_file_is_rejected(self):
        with self.assertRaises(ValidationFailed):
            check_upload("a.pdf", b"%PDF-" + b"0" * (1024 * 1024 + 1))
