from django import forms

from apps.core.forms import BootstrapFormMixin
from apps.family.models import Person

from .models import Document


class UploadForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(
        help_text="PDF, JPG, PNG, Word (.docx) or Excel (.xlsx). Maximum 10 MB. Macros are not allowed."
    )
    title = forms.CharField(
        max_length=200, required=False,
        help_text="Example: SBI passbook first page. Never type account numbers here.",
    )
    doc_type = forms.ChoiceField(choices=Document.DocType.choices, label="Type")
    person = forms.ModelChoiceField(
        queryset=Person.objects.all(), required=False, empty_label="- Not linked to a person -"
    )
    notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Stored encrypted. Private details may go here.",
    )
    expiry_date = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Optional. Use for documents that expire.",
    )


class DocumentEditForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "doc_type", "person", "notes", "expiry_date"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        help_texts = {
            "title": "Never put account numbers in the title.",
            "notes": "Stored encrypted. Private details may go here.",
        }
