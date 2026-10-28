import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from apps.core.forms import BootstrapFormMixin
from apps.family.models import Person
from apps.vault.models import Document

from .models import Account, AccountRemark, BalanceSnapshot, Institution

IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


class InstitutionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Institution
        fields = ["name", "kind"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicates = Institution.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise ValidationError("This institution already exists.")
        return name


class AccountForm(BootstrapFormMixin, forms.ModelForm):
    # One joint holder at most. Choose "- None -" to remove it.
    joint_holder = forms.ModelChoiceField(
        queryset=Person.objects.all(), required=False, empty_label="- None -",
        label="Joint holder",
    )
    # The stored number is never shown again here. Leave blank to keep it.
    new_account_number = forms.CharField(
        required=False, label="Account number",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    new_customer_id = forms.CharField(
        required=False, label="Customer ID",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    first_remark = forms.CharField(
        required=False, label="Remark (optional)",
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="More remarks and documents can be added on the account page after saving.",
    )

    field_order = [
        "holder", "joint_holder", "nominee", "account_type", "institution", "nickname",
        "new_account_number", "ifsc_code", "new_customer_id", "branch",
        "opening_date", "is_closed", "closed_on", "full_tracking", "first_remark",
    ]

    class Meta:
        model = Account
        fields = [
            "holder", "nominee", "account_type", "institution", "nickname",
            "ifsc_code", "branch", "opening_date", "is_closed", "closed_on", "full_tracking",
        ]
        widgets = {
            "opening_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "closed_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        help_texts = {
            "nickname": "Optional, for example: SBI salary account. Never put account numbers here.",
            "ifsc_code": "11 characters, for example SBIN0001234.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            keep = "Leave blank to keep the current value"
            self.fields["new_account_number"].widget.attrs["placeholder"] = keep
            self.fields["new_customer_id"].widget.attrs["placeholder"] = keep
            joint = list(self.instance.joint_holders.all())
            if joint:
                self.initial["joint_holder"] = joint[0].pk
            if len(joint) > 1:
                self.fields["joint_holder"].help_text = (
                    f"This account had {len(joint)} joint holders. "
                    "Saving keeps only the one chosen here."
                )
            del self.fields["first_remark"]

    def clean_ifsc_code(self):
        value = self.cleaned_data["ifsc_code"].strip().upper()
        if value and not IFSC_RE.match(value):
            raise ValidationError("An IFSC code has 4 letters, a zero, then 6 letters or digits.")
        return value

    def clean_opening_date(self):
        value = self.cleaned_data["opening_date"]
        if value and value > date.today():
            raise ValidationError("The opening date cannot be in the future.")
        return value

    def clean(self):
        data = super().clean()
        holder = data.get("holder")
        joint = data.get("joint_holder")
        if holder and joint and holder == joint:
            self.add_error("joint_holder", "The main holder cannot also be the joint holder.")
        if data.get("closed_on") and not data.get("is_closed"):
            self.add_error("closed_on", "Tick Closed if you enter a closing date.")
        return data

    def save(self, commit=True):
        account = super().save(commit=False)
        number = self.cleaned_data.get("new_account_number", "").strip()
        customer = self.cleaned_data.get("new_customer_id", "").strip()
        if number:
            account.account_number = number
        if customer:
            account.customer_id = customer

        original_save_m2m = self.save_m2m

        def save_m2m():
            original_save_m2m()
            joint = self.cleaned_data.get("joint_holder")
            account.joint_holders.set([joint] if joint else [])
            remark = self.cleaned_data.get("first_remark", "").strip()
            if remark:
                AccountRemark.objects.create(account=account, text=remark)

        self.save_m2m = save_m2m
        if commit:
            account.save()
            self.save_m2m()
        return account


class RemarkForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AccountRemark
        fields = ["text"]
        labels = {"text": "New remark"}
        widgets = {"text": forms.Textarea(attrs={"rows": 2})}


class AccountDocumentForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        help_text="PDF, JPG, PNG, Word (.docx) or Excel (.xlsx). Maximum 10 MB. Add documents one by one."
    )
    title = forms.CharField(
        max_length=200, required=False,
        help_text="Optional. Never type account numbers here.",
    )
    doc_type = forms.ChoiceField(
        choices=Document.DocType.choices, initial=Document.DocType.BANK, label="Type"
    )
    expiry_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Optional. Use for documents that expire.",
    )


class SnapshotForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BalanceSnapshot
        fields = ["as_of", "amount", "note"]
        widgets = {
            "as_of": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {"as_of": "Balance as of"}

    def __init__(self, account, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account = account

    def clean_as_of(self):
        value = self.cleaned_data["as_of"]
        if value > date.today():
            raise ValidationError("The date cannot be in the future.")
        return value

    def clean(self):
        data = super().clean()
        as_of = data.get("as_of")
        if as_of:
            existing = BalanceSnapshot.objects.filter(account=self.account, as_of=as_of)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                self.add_error("as_of", "A balance for this date already exists. Edit that one instead.")
        return data



from decimal import Decimal  # noqa: E402

from .models import Transaction  # noqa: E402


class TransactionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "account", "date", "direction", "amount", "category",
            "description", "counterparty", "reference",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "reference": forms.TextInput(attrs={"autocomplete": "off"}),
        }
        help_texts = {
            "amount": "Always a positive number. Choose Money in or Money out above.",
            "description": "Never put account numbers here.",
            "reference": "Cheque or transaction number. Stored encrypted.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = "- Uncategorised -"
        if not self.instance.pk:
            self.fields["account"].queryset = Account.objects.filter(is_closed=False)

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value > date.today():
            raise ValidationError("The date cannot be in the future.")
        return value


class TransferForm(BootstrapFormMixin, forms.Form):
    from_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_closed=False), label="From account"
    )
    to_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_closed=False), label="To account"
    )
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    amount = forms.DecimalField(
        max_digits=16, decimal_places=2, min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )
    description = forms.CharField(
        max_length=200, required=False,
        help_text="Optional. Never put account numbers here.",
    )

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value > date.today():
            raise ValidationError("The date cannot be in the future.")
        return value

    def clean(self):
        data = super().clean()
        if data.get("from_account") and data.get("from_account") == data.get("to_account"):
            self.add_error("to_account", "Choose two different accounts.")
        return data


from .models import TransactionCategory  # noqa: E402


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TransactionCategory
        fields = ["name", "group", "sort_order"]
        help_texts = {
            "group": "Decides where this category counts in reports. Transfers between your own accounts are left out of income and expenses.",
            "sort_order": "Lower numbers appear first in lists.",
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        duplicates = TransactionCategory.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise ValidationError("This category already exists.")
        return name
