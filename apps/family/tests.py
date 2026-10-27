from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings

from apps.core.models import AuditLog
from apps.family.models import Person

KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=KEY)
class PersonTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(username="boss", password="Test-pass-12345", is_staff=True)
        User.objects.create_user(username="normal", password="Test-pass-12345")
        self.client.login(username="boss", password="Test-pass-12345")

    def test_add_person_through_the_page(self):
        response = self.client.post("/family/add/", {
            "full_name": "Asha Test", "relationship": "spouse",
            "date_of_birth": "1990-05-01", "notes": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Person.objects.filter(full_name="Asha Test").exists())

    def test_soft_delete_hides_person_and_is_audited(self):
        person = Person.objects.create(full_name="Temp Person")
        person.delete()
        self.assertFalse(Person.objects.filter(pk=person.pk).exists())
        self.assertTrue(Person.all_objects.filter(pk=person.pk, is_deleted=True).exists())
        self.assertTrue(AuditLog.objects.filter(action="delete", model_label="family.Person").exists())

    def test_hard_delete_is_audited(self):
        person = Person.objects.create(full_name="Temp Person")
        person.hard_delete()
        self.assertFalse(Person.all_objects.filter(pk=person.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="hard_delete", model_label="family.Person").exists())

    def test_notes_are_stored_encrypted(self):
        person = Person.objects.create(full_name="Secret Keeper", notes="PAN ABCDE1234F")
        self.assertEqual(Person.objects.get(pk=person.pk).notes, "PAN ABCDE1234F")
        with connection.cursor() as cursor:
            cursor.execute("SELECT notes FROM family_person WHERE id = %s", [person.pk])
            raw = cursor.fetchone()[0]
        self.assertNotIn("ABCDE", raw)

    def test_normal_user_cannot_open_family_page(self):
        self.client.logout()
        self.client.login(username="normal", password="Test-pass-12345")
        self.assertEqual(self.client.get("/family/").status_code, 403)
