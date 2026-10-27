from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings

from apps.core.exceptions import ConfigurationError
from apps.core.fields import decrypt_bytes, decrypt_text, encrypt_bytes, encrypt_text

KEY_A = Fernet.generate_key().decode()
KEY_B = Fernet.generate_key().decode()


@override_settings(FIELD_ENCRYPTION_KEY=KEY_A, FIELD_ENCRYPTION_OLD_KEYS=[])
class EncryptionTests(SimpleTestCase):
    def test_text_round_trip_hides_the_text(self):
        token = encrypt_text("PAN ABCDE1234F")
        self.assertNotIn("ABCDE", token)
        self.assertEqual(decrypt_text(token), "PAN ABCDE1234F")

    def test_bytes_round_trip(self):
        token = encrypt_bytes(b"file contents")
        self.assertNotIn(b"file contents", token)
        self.assertEqual(decrypt_bytes(token), b"file contents")

    def test_wrong_key_is_refused(self):
        token = encrypt_text("secret")
        with override_settings(FIELD_ENCRYPTION_KEY=KEY_B):
            with self.assertRaises(ConfigurationError):
                decrypt_text(token)

    def test_old_key_still_opens_old_data(self):
        token = encrypt_text("secret")
        with override_settings(FIELD_ENCRYPTION_KEY=KEY_B, FIELD_ENCRYPTION_OLD_KEYS=[KEY_A]):
            self.assertEqual(decrypt_text(token), "secret")

    def test_missing_key_gives_a_clear_error(self):
        with override_settings(FIELD_ENCRYPTION_KEY=""):
            with self.assertRaises(ConfigurationError):
                encrypt_text("x")
