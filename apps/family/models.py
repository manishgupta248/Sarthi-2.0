from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Person(BaseModel):
    """A family member. Not a login user: you enter their records yourself."""

    class Relationship(models.TextChoices):
        SELF = "self", "Self"
        SPOUSE = "spouse", "Spouse"
        SON = "son", "Son"
        DAUGHTER = "daughter", "Daughter"
        FATHER = "father", "Father"
        MOTHER = "mother", "Mother"
        BROTHER = "brother", "Brother"
        SISTER = "sister", "Sister"
        OTHER = "other", "Other"

    full_name = models.CharField(max_length=150)
    relationship = models.CharField(
        max_length=20, choices=Relationship.choices, default=Relationship.OTHER
    )
    date_of_birth = models.DateField(null=True, blank=True)
    notes = EncryptedTextField(blank=True)

    class Meta:
        ordering = ["full_name"]
        verbose_name_plural = "people"

    def __str__(self):
        return self.full_name
