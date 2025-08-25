from django.core.management.base import BaseCommand
from companies.models import Company
from fundamentals.models import Statement
import requests, os, time
from datetime import datetime
from collections import defaultdict

# Each (statement_type, normalized_key) → list of GAAP tag fallbacks
GROUPS = {
    # Income Statement
    ("IS","Revenue"): [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
    ],
    ("IS","COGS"): ["CostOfRevenue"],
    ("IS","GrossProfit"): ["GrossProfit"],
    ("IS","OperatingIncome"): ["OperatingIncomeLoss"],
    ("IS","NetIncome"): ["NetIncomeLoss", "ProfitLoss"],
    ("IS","EPS_Diluted"): ["EarningsPerShareDiluted"],
    ("IS","DilutedShares"): ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    ("IS","DA"): ["DepreciationAndAmortization", "DepreciationDepletionAndAmortization"],
    ("IS","SGA"): ["SellingGeneralAndAdministrativeExpense"],
    ("IS","RnD"): ["ResearchAndDevelopmentExpense"],

    # Cash Flow
    ("CF","CFO"): [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    ("CF","CapEx"): [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpendituresIncurredButNotYetPaid",
    ],

    # Balance Sheet
    ("BS","TotalAssets"): ["Assets"],
    ("BS","CurrentAssets"): ["AssetsCurrent"],
    ("BS","TotalLiabilities"): ["Liabilities"],
    ("BS","CurrentLiabilities"): ["LiabilitiesCurrent"],
    ("BS","Cash"): ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"],
    ("BS","ShortDebt"): ["DebtCurrent", "ShortTermBorrowings"],
    ("BS","LongDebt"): ["LongTermDebtNoncurrent", "LongTermDebt"],
    ("BS","CommonShares"): ["CommonStockSharesOutstanding"],
}

def quarterly_series_for_tag(facts, tag):
    obj = (facts or {}).get(tag)
    if not obj: return {}
    units = obj.get("units", {})
    series = units.get("USD") or next(iter(units.values()), [])
    out = {}
    for r in series:
        fp = (r.get("fp") or "").upper()
        form = (r.get("form") or "").upper()
        qtrs = r.get("qtrs")
        if (fp.startswith("Q") or form == "10-Q" or qtrs == 1) and r.get("end") and r.get("val") is not None:
            out[r["end"]] = r["val"]
    return out

class Command(BaseCommand):
    help = "Ingest recent quarterly fundamentals from SEC EDGAR Company Facts"

    def add_arguments(self, parser):
        parser.add_argument("--quarters", type=int, default=20)
        parser.add_argument("--ticker", type=str, default=None)

    def handle(self, *args, **opts):
        ua = os.getenv("SEC_USER_AGENT", "someone@example.com")
        qn = max(1, int(opts["quarters"]))
        qs = Company.objects.exclude(cik__isnull=True).exclude(cik__exact="")
        if opts["ticker"]:
            qs = qs.filter(ticker=opts["ticker"].upper())

        for c in qs:
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c.cik.zfill(10)}.json"

            # polite retry/backoff
            resp = None
            for attempt in range(5):
                try:
                    r = requests.get(url, headers={"User-Agent": ua}, timeout=30)
                    if r.status_code == 429:
                        time.sleep(1.0 * (attempt + 1)); continue
                    r.raise_for_status(); resp = r; break
                except Exception:
                    if attempt == 4: self.stdout.write(self.style.WARNING(f"{c.ticker}: request failed"))
                    time.sleep(1.0 * (attempt + 1))
            if not resp: continue

            facts = (resp.json().get("facts") or {}).get("us-gaap", {})
            by_period = defaultdict(dict)  # {(st_type, date): {norm_key: val}}

            for (st_type, norm_key), candidates in GROUPS.items():
                combined = {}
                for tag in candidates:
                    ser = quarterly_series_for_tag(facts, tag)
                    # first-seen wins for each end date
                    for end_str, val in ser.items():
                        combined.setdefault(end_str, val)
                for end_str, val in sorted(combined.items(), key=lambda kv: kv[0], reverse=True)[:qn]:
                    pe = datetime.fromisoformat(end_str).date()
                    by_period[(st_type, pe)][norm_key] = val

            total = 0
            for (st_type, pe), payload in by_period.items():
                if not payload: continue
                Statement.objects.update_or_create(
                    company=c, statement_type=st_type, period_type="Q", period_end=pe,
                    defaults={"json_payload": payload}
                )
                total += 1

            self.stdout.write(self.style.SUCCESS(f"{c.ticker}: {total} quarterly statements upserted"))
            time.sleep(0.25)
