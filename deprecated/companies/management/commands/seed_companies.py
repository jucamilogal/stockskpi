# companies/management/commands/seed_companies.py
from django.core.management.base import BaseCommand
from companies.models import Company

# Add or edit rows here. Currency defaults to USD if omitted; CIK is optional.
SEED = [
    # -------- Information Technology (10) --------
    {"ticker":"AAPL","name":"Apple Inc.","sector":"Technology","currency":"USD"},
    {"ticker":"MSFT","name":"Microsoft Corp.","sector":"Technology","currency":"USD"},
    {"ticker":"NVDA","name":"NVIDIA Corp.","sector":"Technology","currency":"USD"},
    {"ticker":"AVGO","name":"Broadcom Inc.","sector":"Technology","currency":"USD"},
    {"ticker":"ORCL","name":"Oracle Corp.","sector":"Technology","currency":"USD"},
    {"ticker":"ADBE","name":"Adobe Inc.","sector":"Technology","currency":"USD"},
    {"ticker":"CRM","name":"Salesforce, Inc.","sector":"Technology","currency":"USD"},
    {"ticker":"INTC","name":"Intel Corp.","sector":"Technology","currency":"USD"},
    {"ticker":"AMD","name":"Advanced Micro Devices, Inc.","sector":"Technology","currency":"USD"},
    {"ticker":"TXN","name":"Texas Instruments Inc.","sector":"Technology","currency":"USD"},

    # -------- Communication Services (9) --------
    {"ticker":"GOOGL","name":"Alphabet Inc. Class A","sector":"Communication Services","currency":"USD"},
    {"ticker":"META","name":"Meta Platforms, Inc. Class A","sector":"Communication Services","currency":"USD"},
    {"ticker":"NFLX","name":"Netflix, Inc.","sector":"Communication Services","currency":"USD"},
    {"ticker":"DIS","name":"The Walt Disney Company","sector":"Communication Services","currency":"USD"},
    {"ticker":"T","name":"AT&T Inc.","sector":"Communication Services","currency":"USD"},
    {"ticker":"VZ","name":"Verizon Communications Inc.","sector":"Communication Services","currency":"USD"},
    {"ticker":"TMUS","name":"T-Mobile US, Inc.","sector":"Communication Services","currency":"USD"},
    {"ticker":"CHTR","name":"Charter Communications, Inc. Class A","sector":"Communication Services","currency":"USD"},
    {"ticker":"EA","name":"Electronic Arts Inc.","sector":"Communication Services","currency":"USD"},

    # -------- Consumer Discretionary (9) --------
    {"ticker":"AMZN","name":"Amazon.com, Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"TSLA","name":"Tesla, Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"HD","name":"The Home Depot, Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"MCD","name":"McDonald's Corp.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"NKE","name":"NIKE, Inc. Class B","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"SBUX","name":"Starbucks Corp.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"LOW","name":"Lowe's Companies, Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"BKNG","name":"Booking Holdings Inc.","sector":"Consumer Discretionary","currency":"USD"},
    {"ticker":"TGT","name":"Target Corp.","sector":"Consumer Discretionary","currency":"USD"},

    # -------- Consumer Staples (9) --------
    {"ticker":"PG","name":"Procter & Gamble Company","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"KO","name":"The Coca-Cola Company","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"PEP","name":"PepsiCo, Inc.","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"WMT","name":"Walmart Inc.","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"COST","name":"Costco Wholesale Corp.","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"PM","name":"Philip Morris International Inc.","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"MO","name":"Altria Group, Inc.","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"MDLZ","name":"Mondelez International, Inc. Class A","sector":"Consumer Staples","currency":"USD"},
    {"ticker":"KHC","name":"The Kraft Heinz Company","sector":"Consumer Staples","currency":"USD"},

    # -------- Health Care (9) --------
    {"ticker":"UNH","name":"UnitedHealth Group Incorporated","sector":"Health Care","currency":"USD"},
    {"ticker":"JNJ","name":"Johnson & Johnson","sector":"Health Care","currency":"USD"},
    {"ticker":"PFE","name":"Pfizer Inc.","sector":"Health Care","currency":"USD"},
    {"ticker":"MRK","name":"Merck & Co., Inc.","sector":"Health Care","currency":"USD"},
    {"ticker":"ABBV","name":"AbbVie Inc.","sector":"Health Care","currency":"USD"},
    {"ticker":"TMO","name":"Thermo Fisher Scientific Inc.","sector":"Health Care","currency":"USD"},
    {"ticker":"DHR","name":"Danaher Corp.","sector":"Health Care","currency":"USD"},
    {"ticker":"ABT","name":"Abbott Laboratories","sector":"Health Care","currency":"USD"},
    {"ticker":"BMY","name":"Bristol-Myers Squibb Company","sector":"Health Care","currency":"USD"},

    # -------- Financials (9) --------
    {"ticker":"JPM","name":"JPMorgan Chase & Co.","sector":"Financials","currency":"USD"},
    {"ticker":"BAC","name":"Bank of America Corp.","sector":"Financials","currency":"USD"},
    {"ticker":"WFC","name":"Wells Fargo & Company","sector":"Financials","currency":"USD"},
    {"ticker":"C","name":"Citigroup Inc.","sector":"Financials","currency":"USD"},
    {"ticker":"GS","name":"The Goldman Sachs Group, Inc.","sector":"Financials","currency":"USD"},
    {"ticker":"MS","name":"Morgan Stanley","sector":"Financials","currency":"USD"},
    {"ticker":"BLK","name":"BlackRock, Inc.","sector":"Financials","currency":"USD"},
    {"ticker":"AXP","name":"American Express Company","sector":"Financials","currency":"USD"},
    {"ticker":"PYPL","name":"PayPal Holdings, Inc.","sector":"Financials","currency":"USD"},

    # -------- Industrials (9) --------
    {"ticker":"CAT","name":"Caterpillar Inc.","sector":"Industrials","currency":"USD"},
    {"ticker":"DE","name":"Deere & Company","sector":"Industrials","currency":"USD"},
    {"ticker":"GE","name":"General Electric Company","sector":"Industrials","currency":"USD"},
    {"ticker":"HON","name":"Honeywell International Inc.","sector":"Industrials","currency":"USD"},
    {"ticker":"UPS","name":"United Parcel Service, Inc. Class B","sector":"Industrials","currency":"USD"},
    {"ticker":"BA","name":"The Boeing Company","sector":"Industrials","currency":"USD"},
    {"ticker":"RTX","name":"RTX Corporation","sector":"Industrials","currency":"USD"},
    {"ticker":"LMT","name":"Lockheed Martin Corporation","sector":"Industrials","currency":"USD"},
    {"ticker":"ETN","name":"Eaton Corporation plc","sector":"Industrials","currency":"USD"},

    # -------- Energy (9) --------
    {"ticker":"XOM","name":"Exxon Mobil Corporation","sector":"Energy","currency":"USD"},
    {"ticker":"CVX","name":"Chevron Corporation","sector":"Energy","currency":"USD"},
    {"ticker":"COP","name":"ConocoPhillips","sector":"Energy","currency":"USD"},
    {"ticker":"EOG","name":"EOG Resources, Inc.","sector":"Energy","currency":"USD"},
    {"ticker":"SLB","name":"SLB (Schlumberger)","sector":"Energy","currency":"USD"},
    {"ticker":"HAL","name":"Halliburton Company","sector":"Energy","currency":"USD"},
    {"ticker":"PXD","name":"Pioneer Natural Resources Co.","sector":"Energy","currency":"USD"},
    {"ticker":"PSX","name":"Phillips 66","sector":"Energy","currency":"USD"},
    {"ticker":"MPC","name":"Marathon Petroleum Corp.","sector":"Energy","currency":"USD"},

    # -------- Materials (9) --------
    {"ticker":"LIN","name":"Linde plc","sector":"Materials","currency":"USD"},
    {"ticker":"APD","name":"Air Products and Chemicals, Inc.","sector":"Materials","currency":"USD"},
    {"ticker":"ECL","name":"Ecolab Inc.","sector":"Materials","currency":"USD"},
    {"ticker":"SHW","name":"The Sherwin-Williams Company","sector":"Materials","currency":"USD"},
    {"ticker":"NEM","name":"Newmont Corporation","sector":"Materials","currency":"USD"},
    {"ticker":"FCX","name":"Freeport-McMoRan Inc.","sector":"Materials","currency":"USD"},
    {"ticker":"DOW","name":"Dow Inc.","sector":"Materials","currency":"USD"},
    {"ticker":"LYB","name":"LyondellBasell Industries N.V. Class A","sector":"Materials","currency":"USD"},
    {"ticker":"NUE","name":"Nucor Corporation","sector":"Materials","currency":"USD"},

    # -------- Utilities (9) --------
    {"ticker":"NEE","name":"NextEra Energy, Inc.","sector":"Utilities","currency":"USD"},
    {"ticker":"SO","name":"The Southern Company","sector":"Utilities","currency":"USD"},
    {"ticker":"DUK","name":"Duke Energy Corporation","sector":"Utilities","currency":"USD"},
    {"ticker":"EXC","name":"Exelon Corporation","sector":"Utilities","currency":"USD"},
    {"ticker":"SRE","name":"Sempra","sector":"Utilities","currency":"USD"},
    {"ticker":"AEP","name":"American Electric Power Company, Inc.","sector":"Utilities","currency":"USD"},
    {"ticker":"XEL","name":"Xcel Energy Inc.","sector":"Utilities","currency":"USD"},
    {"ticker":"PEG","name":"Public Service Enterprise Group Inc.","sector":"Utilities","currency":"USD"},
    {"ticker":"ED","name":"Consolidated Edison, Inc.","sector":"Utilities","currency":"USD"},

    # -------- Real Estate (9) --------
    {"ticker":"AMT","name":"American Tower Corp. (REIT)","sector":"Real Estate","currency":"USD"},
    {"ticker":"PLD","name":"Prologis, Inc.","sector":"Real Estate","currency":"USD"},
    {"ticker":"EQIX","name":"Equinix, Inc.","sector":"Real Estate","currency":"USD"},
    {"ticker":"O","name":"Realty Income Corporation","sector":"Real Estate","currency":"USD"},
    {"ticker":"SPG","name":"Simon Property Group, Inc.","sector":"Real Estate","currency":"USD"},
    {"ticker":"CCI","name":"Crown Castle Inc.","sector":"Real Estate","currency":"USD"},
    {"ticker":"PSA","name":"Public Storage","sector":"Real Estate","currency":"USD"},
    {"ticker":"WELL","name":"Welltower Inc.","sector":"Real Estate","currency":"USD"},
    {"ticker":"VTR","name":"Ventas, Inc.","sector":"Real Estate","currency":"USD"},
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
