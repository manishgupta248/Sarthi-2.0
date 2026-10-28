from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from apps.core.forms import BootstrapFormMixin

from .models import LIABILITY_KINDS, Holding, HoldingValuation

COMMON = {"holder", "joint_holder", "nickname", "remarks"}

KIND_FIELDS = {
    "fixed_deposit": ["institution", "nominee", "new_identifier", "principal", "interest_rate",
                      "compounding", "interest_payout", "start_date", "end_date", "maturity_value"],
    "recurring_deposit": ["institution", "nominee", "new_identifier", "installment_amount",
                          "next_due_date", "interest_rate", "start_date", "end_date", "maturity_value"],
    "bond": ["institution", "nominee", "new_identifier", "principal", "interest_rate",
             "start_date", "end_date", "maturity_value"],
    "insurance": ["institution", "nominee", "new_identifier", "sum_assured", "installment_amount",
                  "installment_frequency", "next_due_date", "start_date", "end_date", "maturity_value"],
    "loan_given": ["counterparty", "principal", "interest_rate", "start_date", "end_date"],
    "gold": ["nominee", "principal", "start_date"],
    "property": ["nominee", "principal", "start_date"],
    "other_asset": ["nominee", "principal", "start_date"],
}
LOAN_FIELDS = ["institution", "counterparty", "new_identifier", "principal", "interest_rate",
               "installment_amount", "next_due_date", "start_date", "end_date"]
for _kind in LIABILITY_KINDS:
    KIND_FIELDS[_kind] = LOAN_FIELDS

REQUIRED = {
    "fixed_deposit": ["principal", "interest_rate", "start_date", "end_date"],
    "recurring_deposit": ["installment_amount", "interest_rate", "start_date", "end_date"],
    "bond": ["principal"],
    "loan_given": ["counterparty", "principal"],
    "gold": ["nickname"], "property": ["nickname"], "other_asset": ["nickname"],
}
for _kind in LIABILITY_KINDS:
    REQUIRED[_kind] = ["principal"]

DEFAULT_LABELS = {
    "holder": "Holder", "joint_holder": "Joint holder", "nominee": "Nominee",
    "institution": "Institution", "counterparty": "Other party",
    "nickname": "Name", "new_identifier": "Number",
    "principal": "Amount", "installment_amount": "Instalment amount",
    "installment_frequency": "Payment frequency", "next_due_date": "Next due date",
    "sum_assured": "Sum assured", "interest_rate": "Interest rate (% per year)",
    "compounding": "Interest compounding", "interest_payout": "Interest payout",
    "start_date": "Start date", "end_date": "End date",
    "maturity_value": "Expected maturity amount", "status": "Status",
    "closed_on": "Closed on", "remarks": "Remarks",
}
KIND_LABELS = {
    "fixed_deposit": {"principal": "Deposit amount", "end_date": "Maturity date",
                      "new_identifier": "FD / receipt number", "institution": "Bank"},
    "recurring_deposit": {"installment_amount": "Monthly instalment", "next_due_date": "Next instalment due",
                          "end_date": "Maturity date", "new_identifier": "RD account number",
                          "institution": "Bank"},
    "bond": {"principal": "Purchase amount", "interest_rate": "Coupon rate (% per year)",
             "end_date": "Maturity date", "new_identifier": "ISIN / certificate number",
             "institution": "Issuer or broker"},
    "insurance": {"new_identifier": "Policy number", "installment_amount": "Premium amount",
                  "installment_frequency": "Premium frequency", "next_due_date": "Next premium due",
                  "start_date": "Policy start date", "end_date": "Maturity or end date",
                  "maturity_value": "Expected maturity benefit", "institution": "Insurer"},
    "loan_given": {"counterparty": "Borrower (name)", "principal": "Amount lent",
                   "interest_rate": "Interest rate (% per year, if any)", "start_date": "Date lent",
                   "end_date": "Repayment due date"},
    "gold": {"principal": "Purchase cost", "start_date": "Purchase date", "nickname": "What is it?"},
    "property": {"principal": "Purchase cost", "start_date": "Purchase date", "nickname": "What is it?"},
    "other_asset": {"principal": "Purchase cost", "start_date": "Purchase date", "nickname": "What is it?"},
}
for _kind in LIABILITY_KINDS:
    KIND_LABELS[_kind] = {
        "institution": "Lender", "counterparty": "Lender (if not in the list)",
        "new_identifier": "Loan or card number",
        "principal": "Credit limit" if _kind == "credit_card" else "Original loan amount",
        "installment_amount": "EMI or minimum payment", "next_due_date": "Next payment due",
        "start_date": "Loan start date", "end_date": "Loan end date",
    }

ORDER = [
    "holder", "joint_holder", "nominee", "institution", "counterparty", "nickname", "new_identifier",
    "principal", "sum_assured", "installment_amount", "installment_frequency", "next_due_date",
    "interest_rate", "compounding", "interest_payout", "start_date", "end_date", "maturity_value",
    "status", "closed_on", "remarks",
]


def field_labels(kind):
    labels = dict(DEFAULT_LABELS)
    labels.update(KIND_LABELS.get(kind, {}))
    return labels


class HoldingForm(BootstrapFormMixin, forms.ModelForm):
    # The stored number is never shown again here. Leave blank to keep it.
    new_identifier = forms.CharField(required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))

    class Meta:
        model = Holding
        fields = [
            "holder", "joint_holder", "nominee", "institution", "counterparty", "nickname",
            "principal", "installment_amount", "installment_frequency", "next_due_date",
            "sum_assured", "interest_rate", "compounding", "interest_payout",
            "start_date", "end_date", "maturity_value", "status", "closed_on", "remarks",
        ]
        widgets = {
            "next_due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "closed_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "principal": forms.NumberInput(attrs={"step": "0.01"}),
            "installment_amount": forms.NumberInput(attrs={"step": "0.01"}),
            "sum_assured": forms.NumberInput(attrs={"step": "0.01"}),
            "maturity_value": forms.NumberInput(attrs={"step": "0.01"}),
            "interest_rate": forms.NumberInput(attrs={"step": "0.001"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "nickname": "Shown in lists. Never put policy, loan or account numbers here.",
            "remarks": "Stored encrypted.",
        }

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind = kind
        wanted = set(COMMON) | set(KIND_FIELDS[kind])
        if self.instance.pk:
            wanted |= {"status", "closed_on"}
        for name in list(self.fields):
            if name not in wanted:
                del self.fields[name]
        labels = field_labels(kind)
        for name, field in self.fields.items():
            field.label = labels.get(name, field.label)
        for name in REQUIRED.get(kind, []):
            self.fields[name].required = True
        if "new_identifier" in self.fields and self.instance.pk:
            self.fields["new_identifier"].widget.attrs["placeholder"] = "Leave blank to keep the current value"
        self.order_fields(ORDER)

    def clean_start_date(self):
        value = self.cleaned_data["start_date"]
        if value and value > date.today():
            raise ValidationError("This date cannot be in the future.")
        return value

    def clean(self):
        data = super().clean()
        holder, joint = data.get("holder"), data.get("joint_holder")
        if holder and joint and holder == joint:
            self.add_error("joint_holder", "The main holder cannot also be the joint holder.")
        start, end = data.get("start_date"), data.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "This date cannot be before the start date.")
        if data.get("closed_on") and data.get("status") != "closed":
            self.add_error("closed_on", "Set Status to Closed if you enter a closing date.")
        return data

    def save(self, commit=True):
        holding = super().save(commit=False)
        holding.kind = self.kind
        identifier = self.cleaned_data.get("new_identifier", "").strip()
        if identifier:
            holding.identifier = identifier
        if commit:
            holding.save()
            self.save_m2m()
        return holding


class ValuationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = HoldingValuation
        fields = ["as_of", "amount", "note"]
        widgets = {
            "as_of": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "amount": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {"as_of": "Value as of", "amount": "Value, or amount still owed (rupees)"}

    def __init__(self, holding, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.holding = holding

    def clean_as_of(self):
        value = self.cleaned_data["as_of"]
        if value > date.today():
            raise ValidationError("The date cannot be in the future.")
        return value

    def clean(self):
        data = super().clean()
        as_of = data.get("as_of")
        if as_of:
            existing = HoldingValuation.objects.filter(holding=self.holding, as_of=as_of)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                self.add_error("as_of", "A value for this date already exists. Edit that one instead.")
        return data
