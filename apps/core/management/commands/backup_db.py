from django.core.management.base import BaseCommand, CommandError

from apps.core.backup import create_backup, verify_backup
from apps.core.exceptions import SarthiError


class Command(BaseCommand):
    help = "Create a database backup and check it immediately."

    def add_arguments(self, parser):
        parser.add_argument("--kind", choices=["manual", "auto"], default="manual")

    def handle(self, *args, **options):
        try:
            result = create_backup(kind=options["kind"])
            verify_backup(result["name"])
        except SarthiError as exc:
            raise CommandError(exc.message)
        self.stdout.write(self.style.SUCCESS(f"Backup created and verified: {result['name']}"))
        self.stdout.write(
            f"  Size: {result['size'] // 1024} KB | "
            f"Encrypted: {'yes' if result['encrypted'] else 'NO'} | "
            f"Second copy made: {'yes' if result['copied'] else 'no'}"
        )
