from datetime import date
from decimal import Decimal

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings

from apps.family.models import Person
from apps.wealth.models import (
    Account, AccountType, BalanceSnapshot, Institution, Transaction, TransactionCategory,
)
from apps.wealth.reconciliation import account_reconciliation
from apps.wealth.services import wealth_summary

KEY = Fernet.generate_key().decode()
IN, OUT = Transaction.Direction.IN, Transaction.Direction.OUT


@override_settings(FIELD_ENCRYPTION_KEY=KEY)
class TransactionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(username="boss", password="Test-pass-12345", is_staff=True)
        User.objects.create_user(username="normal", password="Test-pass-12345")
        self.client.login(username="boss", password="Test-pass-12345")
        self.person = Person.objects.create(full_name="Asha Holder")
        self.kind = AccountType.objects.get_or_create(name="Savings")[0]
        self.bank = Institution.objects.create(name="Test Bank")
        self.account = Account.objects.create(
            holder=self.person, account_type=self.kind, institution=self.bank, nickname="Main",
        )
        self.second = Account.objects.create(
            holder=self.person, account_type=self.kind, institution=self.bank, nickname="Second",
        )

    def _balance(self, as_of, amount, account=None):
        return BalanceSnapshot.objects.create(
            account=account or self.account, as_of=as_of, amount=Decimal(amount)
        )

    def _txn(self, when, direction, amount, account=None):
        return Transaction.objects.create(
            account=account or self.account, date=when, direction=direction, amount=Decimal(amount)
        )

    # ----- balance check -----
    def test_periods_that_add_up_match(self):
        self._balance(date(2026, 1, 1), "1000.00")
        self._txn(date(2026, 1, 10), IN, "500.00")
        self._txn(date(2026, 1, 20), OUT, "100.00")
        self._balance(date(2026, 2, 1), "1400.00")
        period = account_reconciliation(self.account)["periods"][0]
        self.assertTrue(period["matches"])
        self.assertEqual(period["expected"], Decimal("1400.00"))

    def test_a_missing_transaction_shows_as_a_difference(self):
        self._balance(date(2026, 1, 1), "1000.00")
        self._txn(date(2026, 1, 10), IN, "500.00")
        self._balance(date(2026, 2, 1), "1400.00")
        period = account_reconciliation(self.account)["periods"][0]
        self.assertFalse(period["matches"])
        self.assertEqual(period["difference"], Decimal("-100.00"))

    def test_checkpoint_day_boundaries(self):
        self._balance(date(2026, 1, 1), "1000.00")
        self._txn(date(2026, 1, 1), IN, "999.00")   # on the first checkpoint day: already in that balance
        self._txn(date(2026, 2, 1), IN, "50.00")    # on the second checkpoint day: belongs to the period
        self._balance(date(2026, 2, 1), "1050.00")
        result = account_reconciliation(self.account)
        self.assertTrue(result["periods"][0]["matches"])
        self.assertEqual(result["before_first_count"], 1)

    def test_estimated_balance_adds_transactions_after_the_last_balance(self):
        self._balance(date(2026, 1, 1), "1000.00")
        self._txn(date(2026, 1, 5), IN, "200.00")
        self._txn(date(2026, 1, 6), OUT, "50.00")
        result = account_reconciliation(self.account)
        self.assertEqual(result["estimated"], Decimal("1150.00"))
        self.assertEqual(result["since_count"], 2)

    def test_dashboard_warns_only_for_accounts_that_record_every_transaction(self):
        for account in (self.account, self.second):
            self._balance(date(2026, 5, 1), "1000.00", account)
            self._txn(date(2026, 5, 10), IN, "500.00", account)
            self._balance(date(2026, 5, 20), "1000.00", account)   # does not add up
        reasons = lambda: [item["account"].nickname for item in wealth_summary(today=date(2026, 5, 21))["attention"]]
        self.assertEqual(reasons(), [])
        self.second.full_tracking = True
        self.second.save()
        self.assertEqual(reasons(), ["Second"])

    # ----- entering transactions -----
    def test_add_transaction_through_the_page(self):
        response = self.client.post("/wealth/transactions/add/", {
            "account": self.account.pk, "date": "2026-05-01", "direction": "in",
            "amount": "2500.50", "category": "", "description": "Salary", "counterparty": "Employer",
            "reference": "UTR123456",
        })
        self.assertEqual(response.status_code, 302)
        saved = Transaction.objects.get()
        self.assertEqual(saved.amount, Decimal("2500.50"))
        self.assertEqual(saved.signed_amount, Decimal("2500.50"))

    def test_zero_and_negative_amounts_are_rejected(self):
        for bad in ("0", "-5"):
            response = self.client.post("/wealth/transactions/add/", {
                "account": self.account.pk, "date": "2026-05-01", "direction": "out", "amount": bad,
            })
            self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_reference_is_encrypted_in_the_database(self):
        item = Transaction.objects.create(
            account=self.account, date=date(2026, 5, 1), direction=IN,
            amount=Decimal("10.00"), reference="UTR998877665",
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT reference FROM wealth_transaction WHERE id = %s", [item.pk])
            raw = cursor.fetchone()[0]
        self.assertNotIn("UTR", raw)

    def test_archived_transaction_disappears_but_is_kept(self):
        item = self._txn(date(2026, 5, 1), IN, "10.00")
        self.client.post(f"/wealth/transactions/{item.pk}/delete/")
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertTrue(Transaction.all_objects.filter(pk=item.pk, is_deleted=True).exists())

    def test_transfer_creates_matching_entries(self):
        response = self.client.post("/wealth/transactions/transfer/", {
            "from_account": self.account.pk, "to_account": self.second.pk,
            "date": "2026-05-01", "amount": "300.00", "description": "",
        })
        self.assertEqual(response.status_code, 302)
        out = Transaction.objects.get(account=self.account)
        into = Transaction.objects.get(account=self.second)
        self.assertEqual((out.direction, into.direction), ("out", "in"))
        self.assertEqual(out.amount, into.amount)
        self.assertEqual(out.category.name, "Transfer")

    def test_transfer_to_the_same_account_is_rejected(self):
        response = self.client.post("/wealth/transactions/transfer/", {
            "from_account": self.account.pk, "to_account": self.account.pk,
            "date": "2026-05-01", "amount": "300.00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)

    # ----- pages -----
    def test_list_filters_and_totals(self):
        self._txn(date(2026, 5, 1), IN, "1500.00")
        self._txn(date(2026, 5, 2), OUT, "400.00")
        self._txn(date(2026, 5, 3), OUT, "100.00", self.second)
        response = self.client.get(f"/wealth/transactions/?account={self.account.pk}&period=all")
        self.assertContains(response, "1,500.00")
        self.assertContains(response, "400.00")
        self.assertNotContains(response, "100.00</td>")
        only_in = self.client.get("/wealth/transactions/?direction=in&period=all")
        self.assertEqual(only_in.context["money_out"], Decimal("0.00"))

    def test_default_categories_are_loaded(self):
        names = set(TransactionCategory.objects.values_list("name", flat=True))
        for expected in ("Salary", "Interest", "Transfer", "Other"):
            self.assertIn(expected, names)

    def test_account_page_shows_estimate_and_balance_check_page_loads(self):
        self._balance(date(2026, 1, 1), "1000.00")
        self._txn(date(2026, 1, 5), IN, "200.00")
        page = self.client.get(f"/wealth/accounts/{self.account.pk}/")
        self.assertContains(page, "1,200.00")
        self.assertEqual(self.client.get(f"/wealth/accounts/{self.account.pk}/reconciliation/").status_code, 200)

    def test_normal_user_cannot_open_transaction_pages(self):
        self.client.logout()
        self.client.login(username="normal", password="Test-pass-12345")
        self.assertEqual(self.client.get("/wealth/transactions/").status_code, 403)
        self.assertEqual(self.client.get(f"/wealth/accounts/{self.account.pk}/reconciliation/").status_code, 403)

