from django.core.management.base import BaseCommand
from companies.models import Company
from fundamentals.services import compute_metrics_for_company

class Command(BaseCommand):
    help = "Compute QoQ, YoY, and TTM metrics for all companies."

    def handle(self, *args, **kwargs):
        n = 0
        for c in Company.objects.all():
            compute_metrics_for_company(c)
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Metrics computed for {n} companies"))
