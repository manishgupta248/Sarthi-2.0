from django.db import migrations

CATEGORIES = [
    "Salary", "Interest", "Dividend", "Refund", "Transfer", "Investment", "Loan",
    "Insurance", "Tax", "Household", "Medical", "Education", "Gift", "Cash", "Other",
]


def load_categories(apps, schema_editor):
    TransactionCategory = apps.get_model("wealth", "TransactionCategory")
    for order, name in enumerate(CATEGORIES, start=1):
        TransactionCategory.objects.get_or_create(name=name, defaults={"sort_order": order * 10})


class Migration(migrations.Migration):
    dependencies = [("wealth", "0006_transactioncategory_account_full_tracking_and_more")]
    operations = [migrations.RunPython(load_categories, migrations.RunPython.noop)]
