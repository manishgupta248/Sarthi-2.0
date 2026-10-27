from django.core.management.base import BaseCommand, CommandError

from apps.core.backup import restore_backup
from apps.core.exceptions import SarthiError


class Command(BaseCommand):
    help = "Replace the database with a backup. Stop the Sarthi server first."

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("--yes", action="store_true", help="Skip the confirmation question")

    def handle(self, *args, **options):
        if not options["yes"]:
            self.stdout.write(self.style.WARNING(
                "This REPLACES the current database with the backup. "
                "A safety backup of the current database is made first."
            ))
            answer = input("Type RESTORE to continue: ")
            if answer.strip() != "RESTORE":
                self.stdout.write("Cancelled. Nothing was changed.")
                return
        try:
            result = restore_backup(options["filename"])
        except SarthiError as exc:
            raise CommandError(exc.message)
        self.stdout.write(self.style.SUCCESS(f"Restored from {result['restored_from']}"))
        if result["safety_backup"]:
            self.stdout.write(f"Safety backup of the previous database: {result['safety_backup']}")
        self.stdout.write("Restart the Sarthi server and sign in again.")
