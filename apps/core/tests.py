from django.test import TestCase

from apps.core.exceptions import RecordNotFound, api_exception_handler


class HealthTests(TestCase):
    def test_health_page_reports_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "ok")

    def test_every_response_has_a_request_id(self):
        response = self.client.get("/health/")
        self.assertTrue(response["X-Request-ID"])


class ExceptionHandlerTests(TestCase):
    def test_expected_error_becomes_clean_message(self):
        response = api_exception_handler(RecordNotFound("No such record"), {})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["message"], "No such record")

    def test_unknown_error_hides_details(self):
        response = api_exception_handler(RuntimeError("secret detail"), {})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret detail", str(response.data))
