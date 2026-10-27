from decimal import Decimal

from django.test import SimpleTestCase

from apps.core.templatetags.sarthi_extras import inr, mask_last4


class MoneyFormatTests(SimpleTestCase):
    def test_indian_grouping(self):
        self.assertEqual(inr(Decimal("12345678.5")), "\u20b91,23,45,678.50")
        self.assertEqual(inr(Decimal("100000")), "\u20b91,00,000.00")
        self.assertEqual(inr(Decimal("999")), "\u20b9999.00")

    def test_negative_amounts(self):
        self.assertEqual(inr(Decimal("-1234.5")), "-\u20b91,234.50")

    def test_empty_values(self):
        self.assertEqual(inr(None), "-")
        self.assertEqual(mask_last4(""), "-")
        self.assertEqual(mask_last4("6789"), "XXXXXX6789")
