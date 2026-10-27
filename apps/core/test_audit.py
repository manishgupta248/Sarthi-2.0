from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.models import AuditLog


class AuditTrailTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username="audit_user", password="Test-pass-12345")

    def test_creating_a_user_is_recorded(self):
        entry = AuditLog.objects.filter(action="create", model_label="accounts.User").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.object_repr, "audit_user")

    def test_update_records_field_names_but_not_values(self):
        self.user.first_name = "Secretname"
        self.user.save()
        entry = AuditLog.objects.filter(action="update").first()
        self.assertEqual(entry.changed_fields, ["first_name"])
        self.assertNotIn("Secretname", str(entry.changed_fields))

    def test_login_and_failed_login_are_recorded(self):
        self.client.login(username="audit_user", password="Test-pass-12345")
        self.assertTrue(AuditLog.objects.filter(action="login").exists())
        self.assertEqual(AuditLog.objects.filter(action="update").count(), 0)
        self.client.login(username="audit_user", password="wrong-password")
        self.assertTrue(AuditLog.objects.filter(action="login_failed").exists())

    def test_audit_entries_cannot_be_edited(self):
        entry = AuditLog.objects.first()
        entry.note = "changed"
        with self.assertRaises(PermissionError):
            entry.save()
