from django.db import migrations


def copy_remarks(apps, schema_editor):
    Account = apps.get_model("wealth", "Account")
    AccountRemark = apps.get_model("wealth", "AccountRemark")
    for account in Account.objects.all():
        text = (account.remarks or "").strip()
        if text:
            AccountRemark.objects.create(account=account, text=text)


class Migration(migrations.Migration):
    dependencies = [("wealth", "0003_accountremark")]
    operations = [migrations.RunPython(copy_remarks, migrations.RunPython.noop)]
