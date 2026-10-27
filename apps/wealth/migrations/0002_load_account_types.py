from django.db import migrations

TYPES = [
    "Savings", "Salary", "PPF", "NPS", "Sukanya Samriddhi",
    "DMAT", "Cash or Wallet", "Other",
]


def load_account_types(apps, schema_editor):
    AccountType = apps.get_model("wealth", "AccountType")
    for order, name in enumerate(TYPES, start=1):
        AccountType.objects.get_or_create(name=name, defaults={"sort_order": order * 10})


class Migration(migrations.Migration):
    dependencies = [("wealth", "0001_initial")]
    operations = [migrations.RunPython(load_account_types, migrations.RunPython.noop)]
