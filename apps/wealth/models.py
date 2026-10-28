import re

from django.db import models
from django.db.models import Q

from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Institution(BaseModel):
    """A bank, post office, broker or scheme provider. Added once, reused by accounts."""

    class Kind(models.TextChoices):
        BANK = "bank", "Bank"
        POST_OFFICE = "post_office", "Post Office"
        BROKER = "broker", "Broker or Depository"
        GOVERNMENT = "government", "Government scheme"
        EMPLOYER = "employer", "Employer or EPFO"
        OTHER = "other", "Other"

    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.BANK)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AccountType(BaseModel):
    """Editable list (Savings, PPF, NPS, ...). Add more from the admin site."""

    name = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Account(BaseModel):
    holder = models.ForeignKey(
        "family.Person", on_delete=models.PROTECT, related_name="accounts"
    )
    joint_holders = models.ManyToManyField(
        "family.Person", blank=True, related_name="joint_accounts"
    )
    nominee = models.ForeignKey(
        "family.Person", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="nominee_accounts",
    )
    account_type = models.ForeignKey(AccountType, on_delete=models.PROTECT, related_name="accounts")
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="accounts")

    # Shown in lists and the audit log, so it must never contain account numbers.
    nickname = models.CharField(max_length=120, blank=True)
    account_number = EncryptedTextField(blank=True)
    account_number_last4 = models.CharField(max_length=4, blank=True, editable=False)
    ifsc_code = models.CharField(max_length=11, blank=True)
    customer_id = EncryptedTextField(blank=True)
    branch = models.CharField(max_length=120, blank=True)
    opening_date = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    full_tracking = models.BooleanField(
        "Record every transaction", default=False,
        help_text="Tick if you record every transaction of this account (useful for PPF, NPS, Sukanya). Sarthi then warns when the balance does not add up.",
    )
    closed_on = models.DateField(null=True, blank=True)
    # remarks now live in AccountRemark (one entry per remark)
    documents = models.ManyToManyField("vault.Document", blank=True, related_name="accounts")

    class Meta:
        ordering = ["holder__full_name", "institution__name", "id"]

    @property
    def display_name(self):
        return self.nickname or f"{self.institution.name} {self.account_type.name}"

    def __str__(self):
        return f"{self.display_name} ({self.holder.full_name})"

    def save(self, *args, **kwargs):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", self.account_number or "")
        self.account_number_last4 = cleaned[-4:]
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "account_number" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["account_number_last4"]
        super().save(*args, **kwargs)


class BalanceSnapshot(BaseModel):
    """'On this date, this account held this amount' (rupees)."""

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="snapshots")
    as_of = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-as_of", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "as_of"],
                condition=Q(is_deleted=False),
                name="one_active_snapshot_per_account_per_day",
            )
        ]

    def __str__(self):
        return f"{self.account.display_name} on {self.as_of}"


class AccountRemark(BaseModel):
    """One remark about an account. Add as many as needed; each is stored encrypted."""

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="remark_entries")
    text = EncryptedTextField()

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Remark on {self.account.display_name}"




from decimal import Decimal  # noqa: E402

from django.core.validators import MinValueValidator  # noqa: E402


class TransactionCategory(BaseModel):
    """Editable list (Salary, Interest, ...). Add more from the admin site."""

    class Group(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        INVESTMENT = "investment", "Investment"
        TRANSFER = "transfer", "Transfer between own accounts"
        LOAN = "loan", "Loan (lent or borrowed)"
        OTHER = "other", "Other / not classified"

    group = models.CharField(max_length=12, choices=Group.choices, default=Group.OTHER)

    name = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "transaction categories"

    def __str__(self):
        return self.name


class Transaction(BaseModel):
    """One money movement on an account. Amounts are always positive; direction says in or out."""

    class Direction(models.TextChoices):
        IN = "in", "Money in"
        OUT = "out", "Money out"

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="transactions")
    date = models.DateField()
    direction = models.CharField(max_length=3, choices=Direction.choices)
    amount = models.DecimalField(
        max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    category = models.ForeignKey(
        TransactionCategory, null=True, blank=True,
        on_delete=models.PROTECT, related_name="transactions",
    )
    # Plain text: never put account numbers here.
    description = models.CharField(max_length=200, blank=True)
    counterparty = models.CharField(max_length=150, blank=True)
    reference = EncryptedTextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["account", "date"]), models.Index(fields=["date"])]

    @property
    def signed_amount(self):
        return self.amount if self.direction == self.Direction.IN else -self.amount

    def __str__(self):
        return f"{self.get_direction_display()} - {self.account.display_name} - {self.date}"



LIABILITY_KINDS = {
    "home_loan", "car_loan", "personal_loan", "education_loan", "credit_card", "other_liability",
}


class Holding(BaseModel):
    """An investment, loan given, other asset, or a liability (a loan or card dues taken)."""

    class Kind(models.TextChoices):
        FIXED_DEPOSIT = "fixed_deposit", "Fixed deposit"
        RECURRING_DEPOSIT = "recurring_deposit", "Recurring deposit"
        BOND = "bond", "Bond"
        INSURANCE = "insurance", "Insurance policy"
        LOAN_GIVEN = "loan_given", "Loan given to someone"
        GOLD = "gold", "Gold"
        PROPERTY = "property", "Property"
        OTHER_ASSET = "other_asset", "Other asset"
        HOME_LOAN = "home_loan", "Home loan"
        CAR_LOAN = "car_loan", "Car loan"
        PERSONAL_LOAN = "personal_loan", "Personal loan"
        EDUCATION_LOAN = "education_loan", "Education loan"
        CREDIT_CARD = "credit_card", "Credit card dues"
        OTHER_LIABILITY = "other_liability", "Other liability"

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        HALF_YEARLY = "half_yearly", "Half-yearly"
        YEARLY = "yearly", "Yearly"
        SINGLE = "single", "Single payment"

    class Compounding(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        HALF_YEARLY = "half_yearly", "Half-yearly"
        YEARLY = "yearly", "Yearly"
        SIMPLE = "simple", "Simple interest (paid at maturity)"

    class Payout(models.TextChoices):
        CUMULATIVE = "cumulative", "Cumulative (interest added to the deposit)"
        PERIODIC = "periodic", "Interest paid out regularly"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed (matured, repaid or surrendered)"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    holder = models.ForeignKey("family.Person", on_delete=models.PROTECT, related_name="holdings")
    joint_holder = models.ForeignKey(
        "family.Person", null=True, blank=True, on_delete=models.SET_NULL, related_name="joint_holdings"
    )
    nominee = models.ForeignKey(
        "family.Person", null=True, blank=True, on_delete=models.SET_NULL, related_name="nominee_holdings"
    )
    institution = models.ForeignKey(
        Institution, null=True, blank=True, on_delete=models.PROTECT, related_name="holdings"
    )
    # Borrower (loans given) or lender when it is not in the institution list.
    counterparty = models.CharField(max_length=150, blank=True)
    # Shown in lists and the audit log, so it must never contain policy or account numbers.
    nickname = models.CharField(max_length=120, blank=True)
    identifier = EncryptedTextField(blank=True)
    identifier_last4 = models.CharField(max_length=4, blank=True, editable=False)

    principal = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    installment_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    installment_frequency = models.CharField(max_length=12, choices=Frequency.choices, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    sum_assured = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    compounding = models.CharField(
        max_length=12, choices=Compounding.choices, default=Compounding.QUARTERLY, blank=True
    )
    interest_payout = models.CharField(
        max_length=12, choices=Payout.choices, default=Payout.CUMULATIVE, blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    maturity_value = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    closed_on = models.DateField(null=True, blank=True)
    remarks = EncryptedTextField(blank=True)
    documents = models.ManyToManyField("vault.Document", blank=True, related_name="holdings")

    class Meta:
        ordering = ["holder__full_name", "kind", "id"]

    @property
    def is_liability(self):
        return self.kind in LIABILITY_KINDS

    @property
    def display_name(self):
        if self.nickname:
            return self.nickname
        source = self.institution.name if self.institution_id else self.counterparty
        label = self.get_kind_display()
        return f"{label} - {source}" if source else label

    def __str__(self):
        return f"{self.display_name} ({self.holder.full_name})"

    def save(self, *args, **kwargs):
        cleaned = re.sub(r"[^A-Za-z0-9]", "", self.identifier or "")
        self.identifier_last4 = cleaned[-4:]
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "identifier" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["identifier_last4"]
        super().save(*args, **kwargs)


class HoldingValuation(BaseModel):
    """'On this date this holding was worth (or still owed) this amount.'"""

    holding = models.ForeignKey(Holding, on_delete=models.PROTECT, related_name="valuations")
    as_of = models.DateField()
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-as_of", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["holding", "as_of"],
                condition=Q(is_deleted=False),
                name="one_active_valuation_per_holding_per_day",
            )
        ]

    def __str__(self):
        return f"{self.holding.display_name} on {self.as_of}"
