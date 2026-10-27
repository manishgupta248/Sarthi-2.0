from django.contrib.auth import get_user_model
from django.test import TestCase


class UserTests(TestCase):
    def test_project_uses_sarthi_user_model(self):
        self.assertEqual(get_user_model()._meta.label, "accounts.User")

    def test_create_normal_and_super_user(self):
        User = get_user_model()
        user = User.objects.create_user(username="test_user", password="Test-pass-12345")
        self.assertTrue(user.check_password("Test-pass-12345"))
        self.assertFalse(user.is_staff)
        boss = User.objects.create_superuser(username="test_boss", password="Test-pass-12345")
        self.assertTrue(boss.is_superuser)
