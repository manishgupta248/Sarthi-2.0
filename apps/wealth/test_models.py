from cryptography.fernet import Fernet
from django.db import connection
from django.test import TestCase, override_settings

from apps.core.models import AuditLog
from apps.family.models import Person
from apps.wealth.models import Account, AccountType, Institution

KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=KEY)
class AccountModelTests(TestCase):
    def setUp(self):
        self.person = Person.objects.create(full_name="Asha Holder")
        self.kind = AccountType.objects.get_or_create(name="Savings")[0]
        self.bank = Institution.objects.create(name="Test Bank")

    def _account(self, number="1234 5678 9012"):
        return Account.objects.create(
            holder=self.person, account_type=self.kind, institution=self.bank,
            account_number=number, customer_id="CUST998877",
        )

    def test_last4_is_kept_and_the_number_is_encrypted_in_the_database(self):
        account = self._account()
        self.assertEqual(account.account_number_last4, "9012")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT account_number, customer_id FROM wealth_account WHERE id = %s", [account.pk]
            )
            raw_number, raw_customer = cursor.fetchone()
        self.assertNotIn("1234", raw_number)
        self.assertNotIn("CUST", raw_customer)

    def test_text_form_never_contains_the_number(self):
        account = self._account()
        self.assertNotIn("9012", str(account))

    def test_audit_log_never_contains_the_number(self):
        self._account()
        entry = AuditLog.objects.filter(action="create", model_label="wealth.Account").first()
        self.assertIsNotNone(entry)
        self.assertNotIn("9012", entry.object_repr)
        self.assertNotIn("account_number", entry.changed_fields)

    def test_default_account_types_are_loaded(self):
        names = set(AccountType.objects.values_list("name", flat=True))
        for expected in ("Savings", "Salary", "PPF", "NPS", "Sukanya Samriddhi", "DMAT", "Cash or Wallet", "Other"):
            self.assertIn(expected, names)
