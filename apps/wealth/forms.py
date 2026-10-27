import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from apps.core.forms import BootstrapFormMixin

from .models import Account, BalanceSnapshot, Institution

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
    # The stored number is never shown again here. Leave blank to keep it.
    new_account_number = forms.CharField(
        required=False, label="Account number",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    new_customer_id = forms.CharField(
        required=False, label="Customer ID",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    field_order = [
        "holder", "joint_holders", "nominee", "account_type", "institution", "nickname",
        "new_account_number", "ifsc_code", "new_customer_id", "branch",
        "opening_date", "is_closed", "closed_on", "remarks", "documents",
    ]

    class Meta:
        model = Account
        fields = [
            "holder", "joint_holders", "nominee", "account_type", "institution", "nickname",
            "ifsc_code", "branch", "opening_date", "is_closed", "closed_on", "remarks", "documents",
        ]
        widgets = {
            "joint_holders": forms.SelectMultiple(attrs={"size": 4}),
            "documents": forms.SelectMultiple(attrs={"size": 5}),
            "opening_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "closed_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "nickname": "Optional, for example: SBI salary account. Never put account numbers here.",
            "joint_holders": "Hold Ctrl to select several. Leave empty if none.",
            "documents": "Documents from the vault. Hold Ctrl to select several.",
            "remarks": "Stored encrypted.",
            "ifsc_code": "11 characters, for example SBIN0001234.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            keep = "Leave blank to keep the current value"
            self.fields["new_account_number"].widget.attrs["placeholder"] = keep
            self.fields["new_customer_id"].widget.attrs["placeholder"] = keep

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
        if holder and holder in data.get("joint_holders", []):
            self.add_error("joint_holders", "The main holder should not be listed again as a joint holder.")
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
        if commit:
            account.save()
            self.save_m2m()
        return account


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
