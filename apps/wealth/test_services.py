from datetime import date
from decimal import Decimal

from cryptography.fernet import Fernet
from django.test import TestCase, override_settings

from apps.family.models import Person
from apps.wealth.models import Account, AccountType, BalanceSnapshot, Institution
from apps.wealth.services import monthly_trend, wealth_summary

KEY = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=KEY)
class ServiceTests(TestCase):
    def setUp(self):
        self.asha = Person.objects.create(full_name="Asha Holder")
        self.ravi = Person.objects.create(full_name="Ravi Joint")
        self.kind = AccountType.objects.get_or_create(name="Savings")[0]
        self.bank = Institution.objects.create(name="Test Bank")

    def _account(self, **extra):
        return Account.objects.create(
            holder=self.asha, account_type=self.kind, institution=self.bank, **extra
        )

    def _balance(self, account, as_of, amount):
        return BalanceSnapshot.objects.create(account=account, as_of=as_of, amount=Decimal(amount))

    def test_total_uses_only_the_latest_balance(self):
        account = self._account()
        self._balance(account, date(2026, 1, 1), "100.00")
        self._balance(account, date(2026, 6, 1), "250.00")
        self.assertEqual(wealth_summary(today=date(2026, 6, 2))["total"], Decimal("250.00"))

    def test_joint_account_is_counted_once_under_the_main_holder(self):
        account = self._account()
        account.joint_holders.add(self.ravi)
        self._balance(account, date(2026, 6, 1), "500.00")
        summary = wealth_summary(today=date(2026, 6, 2))
        self.assertEqual([row["name"] for row in summary["by_person"]], ["Asha Holder"])
        self.assertEqual(summary["total"], Decimal("500.00"))

    def test_closed_accounts_are_left_out_of_the_total(self):
        open_account = self._account()
        closed_account = self._account(is_closed=True)
        self._balance(open_account, date(2026, 6, 1), "100.00")
        self._balance(closed_account, date(2026, 6, 1), "900.00")
        self.assertEqual(wealth_summary(today=date(2026, 6, 2))["total"], Decimal("100.00"))

    def test_missing_and_old_balances_need_attention(self):
        missing = self._account(nickname="No balance")
        old = self._account(nickname="Old balance")
        fresh = self._account(nickname="Fresh balance")
        self._balance(old, date(2026, 1, 1), "10.00")
        self._balance(fresh, date(2026, 5, 30), "10.00")
        summary = wealth_summary(today=date(2026, 6, 1))
        flagged = {item["account"].nickname for item in summary["attention"]}
        self.assertEqual(flagged, {"No balance", "Old balance"})

    def test_trend_carries_the_last_balance_forward(self):
        account = self._account()
        self._balance(account, date(2026, 8, 15), "100.00")
        self._balance(account, date(2026, 10, 10), "300.00")
        trend = monthly_trend(months=3, today=date(2026, 10, 27))
        self.assertEqual(trend["values"], [100.0, 100.0, 300.0])
