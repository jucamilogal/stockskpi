from django.core.management.base import BaseCommand
from rankings.engine import run_ranking

class Command(BaseCommand):
    help = "Run the Quality + Value ranking"

    def handle(self, *args, **kwargs):
        r = run_ranking()
        if r:
            self.stdout.write(self.style.SUCCESS(f"Ranking '{r.slug}' created"))
        else:
            self.stdout.write(self.style.WARNING("No data to rank"))
