from datetime import date

from django import forms

from apps.core.forms import BootstrapFormMixin

from .models import Person


class PersonForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Person
        fields = ["full_name", "relationship", "date_of_birth", "notes"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {"notes": "Stored encrypted. Private details may go here."}

    def clean_date_of_birth(self):
        value = self.cleaned_data["date_of_birth"]
        if value and value > date.today():
            raise forms.ValidationError("The date of birth cannot be in the future.")
        return value
