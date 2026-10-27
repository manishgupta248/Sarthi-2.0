from django.contrib.auth import get_user_model
from django.test import TestCase


class PageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user(username="normal", password="Test-pass-12345")
        User.objects.create_user(username="boss", password="Test-pass-12345", is_staff=True)

    def test_dashboard_needs_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_login_page_loads(self):
        self.assertEqual(self.client.get("/accounts/login/").status_code, 200)

    def test_dashboard_hides_admin_items_from_normal_user(self):
        self.client.login(username="normal", password="Test-pass-12345")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/system/backups/")

    def test_normal_user_cannot_open_backups_page(self):
        self.client.login(username="normal", password="Test-pass-12345")
        self.assertEqual(self.client.get("/system/backups/").status_code, 403)

    def test_staff_can_open_dashboard_and_system_pages(self):
        self.client.login(username="boss", password="Test-pass-12345")
        response = self.client.get("/")
        self.assertContains(response, "/system/backups/")
        self.assertEqual(self.client.get("/system/backups/").status_code, 200)
        self.assertEqual(self.client.get("/system/audit/").status_code, 200)
