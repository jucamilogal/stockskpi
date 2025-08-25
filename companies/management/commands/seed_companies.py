# companies/management/commands/seed_companies.py
from django.core.management.base import BaseCommand
from companies.models import Company

# Add or edit rows here. Currency defaults to USD if omitted; CIK is optional.
SEED = [
    # --- Information Technology (5) ---
    {"ticker":"AAPL","name":"Apple Inc.","sector":"Information Technology","currency":"USD"},
    {"ticker":"MSFT","name":"Microsoft Corp.","sector":"Information Technology","currency":"USD"},
    {"ticker":"NVDA","name":"NVIDIA Corporation","sector":"Information Technology","currency":"USD"},
    {"ticker":"ORCL","name":"Oracle Corporation","sector":"Information Technology","currency":"USD"},
    {"ticker":"CRM","name":"Salesforce, Inc.","sector":"Information Technology","currency":"USD"},

    # --- Communication Services (3) ---
    {"ticker":"GOOGL","name":"Alphabet Inc. Class A","sector":"Communication Services","currency":"USD"},
    {"ticker":"META","name":"Meta Platforms, Inc.","sector":"Communication Services","currency":"USD"},
    {"ticker":"NFLX","name":"Netflix, Inc.","sector":"Communication Services","currency":"USD"},

    # --- Consumer Discretionary (3) ---
    {"ticker":"AMZN","name":"Amazon.com, Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"HD","name":"The Home Depot, Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"MCD","name":"McDonald's Corporation","sector":"Consumer Discretionary","currency":"USD"},

    # --- Consumer Staples (3) ---
    {"ticker":"PG","name":"The Procter & Gamble Company","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"KO","name":"The Coca-Cola Company","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"COST","name":"Costco Wholesale Corporation","sector":"Consumer Staples","currency":"USD"},

    # --- Energy (3) ---
    {"ticker":"XOM","name":"Exxon Mobil Corporation","sector":"Energy","currency":"USD"},
    {"ticker":"CVX","name":"Chevron Corporation","sector":"Energy","currency":"USD"},
    {"ticker":"COP","name":"ConocoPhillips","sector":"Energy","currency":"USD"},

    # --- Financials (4) ---
    {"ticker":"JPM","name":"JPMorgan Chase & Co.","sector":"Financials","currency":"USD"},
    {"ticker":"V","name":"Visa Inc. Class A","sector":"Financials","currency":"USD"},
    {"ticker":"MA","name":"Mastercard Incorporated Class A","sector":"Financials","currency":"USD"},
    {"ticker":"BLK","name":"BlackRock, Inc.","sector":"Financials","currency":"USD"},

    # --- Health Care (3) ---
    {"ticker":"UNH","name":"UnitedHealth Group Incorporated","sector":"Health Care","currency":"USD"},
    {"ticker":"JNJ","name":"Johnson & Johnson","sector":"Health Care","currency":"USD"},
    {"ticker":"LLY","name":"Eli Lilly and Company","sector":"Health Care","currency":"USD"},

    # --- Industrials (3) ---
    {"ticker":"CAT","name":"Caterpillar Inc.","sector":"Industrials","currency":"USD"},
    {"ticker":"GE","name":"General Electric Company","sector":"Industrials","currency":"USD"},
    {"ticker":"RTX","name":"RTX Corporation","sector":"Industrials","currency":"USD"},

    # --- Materials (1) ---
    {"ticker":"LIN","name":"Linde plc","sector":"Materials","currency":"USD"},

    # --- Real Estate (1) ---
    {"ticker":"PLD","name":"Prologis, Inc.","sector":"Real Estate","currency":"USD"},

    # --- Utilities (1) ---
    {"ticker":"NEE","name":"NextEra Energy, Inc.","sector":"Utilities","currency":"USD"},
]

class Command(BaseCommand):
    help = "Seed companies from the static SEED list."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Delete companies NOT present in the seed list")

    def handle(self, *args, **opts):
        keep = {row["ticker"].upper() for row in SEED}
        created = updated = 0
        for row in SEED:
            ticker = row["ticker"].upper()
            defaults = {
                "name": row.get("name", ticker)[:255],
                "sector": row.get("sector", "Unspecified"),
                "currency": row.get("currency", "USD"),
                "cik": row.get("cik"),
            }
            obj, was_created = Company.objects.update_or_create(ticker=ticker, defaults=defaults)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        if opts["reset"]:
            qs = Company.objects.exclude(ticker__in=keep)
            removed = qs.count()
            qs.delete()
            self.stdout.write(self.style.WARNING(f"Removed {removed} companies not in SEED."))

        self.stdout.write(self.style.SUCCESS(f"Seeded companies (created={created}, updated={updated})."))
