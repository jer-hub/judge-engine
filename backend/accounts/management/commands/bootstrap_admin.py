from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
import os

WEAK_PASSWORDS = frozenset({"admin123", "password", "admin", "demo123"})


class Command(BaseCommand):
    help = "Create the initial admin user if it does not exist (admin-created accounts only)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument(
            "--password",
            default=None,
            help="Required. Prefer BOOTSTRAP_ADMIN_PASSWORD env var in compose.",
        )
        parser.add_argument("--email", default="admin@school.local")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"] or os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
        if not password:
            raise CommandError("Provide --password or BOOTSTRAP_ADMIN_PASSWORD")
        if password in WEAK_PASSWORDS:
            raise CommandError(
                "Refusing weak bootstrap password. Choose a stronger BOOTSTRAP_ADMIN_PASSWORD."
            )
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists"))
            return
        user = User.objects.create_superuser(
            username=username,
            email=options["email"],
            password=password,
            role=User.Role.ADMIN,
        )
        self.stdout.write(self.style.SUCCESS(f"Created admin user '{user.username}'"))
