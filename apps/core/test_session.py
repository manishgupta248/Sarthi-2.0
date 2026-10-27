from django.conf import settings
from django.test import SimpleTestCase


class SessionTests(SimpleTestCase):
    def test_idle_signout_is_configured(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, settings.SESSION_IDLE_MINUTES * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
