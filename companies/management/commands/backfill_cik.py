import os, requests, time
from django.core.management.base import BaseCommand
from companies.models import Company

def to_sec_symbol(t: str) -> str:
    return t.replace("-", ".").upper()

class Command(BaseCommand):
    help = "Fill missing Company.cik using SEC ticker map."

    def add_arguments(self, parser):
        parser.add_argument("--tickers", nargs="*", help="Limit to specific tickers")
        parser.add_argument("--sleep", type=float, default=0.0, help="Pause between updates (sec)")

    def handle(self, *args, **opts):
        ua = os.getenv("SEC_USER_AGENT") or "Finboard/1.0 (Contact: you@example.com)"
        r = requests.get("https://www.sec.gov/files/company_tickers.json",
                         headers={"User-Agent": ua}, timeout=30)
        r.raise_for_status()
        data = r.json()
        sec_map = {str(v["ticker"]).upper(): str(v["cik_str"]).zfill(10) for v in data.values()}

        qs = Company.objects.filter(cik__isnull=True)
        if opts.get("tickers"):
            qs = qs.filter(ticker__in=[t.upper() for t in opts["tickers"]])

        updated = 0
        for c in qs:
            cik = sec_map.get(to_sec_symbol(c.ticker)) or sec_map.get(c.ticker.upper())
            if cik:
                c.cik = cik
                c.save(update_fields=["cik"])
                updated += 1
                if opts["sleep"]: time.sleep(opts["sleep"])
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} companies with CIKs."))
