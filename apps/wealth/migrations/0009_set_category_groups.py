from django.db import migrations

GROUPS = {
    "Salary": "income", "Interest": "income", "Dividend": "income",
    "Refund": "expense", "Insurance": "expense", "Tax": "expense", "Household": "expense",
    "Medical": "expense", "Education": "expense", "Gift": "expense", "Cash": "expense",
    "Investment": "investment", "Transfer": "transfer", "Loan": "loan", "Other": "other",
}


def set_groups(apps, schema_editor):
    Category = apps.get_model("wealth", "TransactionCategory")
    for name, group in GROUPS.items():
        Category.objects.filter(name=name, group="other").update(group=group)


class Migration(migrations.Migration):
    dependencies = [("wealth", "0008_transactioncategory_group_and_more")]
    operations = [migrations.RunPython(set_groups, migrations.RunPython.noop)]
