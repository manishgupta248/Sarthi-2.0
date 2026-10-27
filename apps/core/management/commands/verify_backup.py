from django.core.management.base import BaseCommand, CommandError

from apps.core.backup import list_backups, verify_backup
from apps.core.exceptions import SarthiError


class Command(BaseCommand):
    help = "Fully check a backup (default: the newest one) without changing anything."

    def add_arguments(self, parser):
        parser.add_argument("filename", nargs="?", default="")

    def handle(self, *args, **options):
        name = options["filename"]
        if not name:
            backups = list_backups()
            if not backups:
                raise CommandError("No backups found.")
            name = backups[0]["name"]
        try:
            info = verify_backup(name)
        except SarthiError as exc:
            raise CommandError(exc.message)
        users = "unknown" if info["users"] is None else info["users"]
        self.stdout.write(self.style.SUCCESS(
            f"Backup {info['name']} is healthy "
            f"({info['tables']} tables, {users} users, "
            f"encrypted: {'yes' if info['encrypted'] else 'no'})"
        ))
