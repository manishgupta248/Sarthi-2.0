from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.views import staff_required

from .forms import PersonForm
from .models import Person


@staff_required
def person_list(request):
    return render(request, "family/person_list.html", {"people": Person.objects.all()})


@staff_required
def person_edit(request, pk=None):
    person = get_object_or_404(Person, pk=pk) if pk else None
    form = PersonForm(request.POST or None, instance=person)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"Saved {saved.full_name}.")
        return redirect("family_list")
    return render(request, "family/person_form.html", {"form": form, "person": person})


@staff_required
@require_POST
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk)
    person.delete()
    messages.success(
        request, f"{person.full_name} was archived. An administrator can restore the record."
    )
    return redirect("family_list")
