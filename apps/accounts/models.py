from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Sarthi's own user model. Always use this, never Django's default."""

    phone = models.CharField(max_length=20, blank=True)
    # Used in the Telegram phase so the bot answers only the owner.
    telegram_user_id = models.BigIntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.get_full_name() or self.username
