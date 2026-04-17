from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from personaggi.campaigns import ensure_user_in_base_campaign


class Command(BaseCommand):
    help = "Assicura che tutti gli utenti siano associati alla campagna base Kor35."

    def handle(self, *args, **options):
        total = 0
        for user in User.objects.all().iterator():
            ensure_user_in_base_campaign(user)
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Backfill completato. Utenti verificati: {total}"))
