# fundamentals/management/commands/fmp_fundamentals.py
import os
import time
import datetime as dt
import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from companies.models import Company
from fundamentals.models import Statement

BASE = "https://financialmodelingprep.com/api/v3"

def _iso(d: str):
    try:
        return dt.date.fromisoformat(d[:10])
    except Exception:
        return None

def _norm_symbol(c: Company, suffix: str) -> str:
    """
    FMP usa ticker 'puro' para USA (AAPL, MSFT), y sufijo para otros (VOD.L, VALE.SA).
    Si pasas .US lo quitamos automáticamente.
    """
    sym = (getattr(c, "fmp_symbol", None) or c.ticker or "").strip().upper()
    suf = (suffix or "").strip().upper()
    if suf == ".US" or sym.endswith(".US"):
        sym = sym.replace(".US", "")
        suf = ""
    if suf and not sym.endswith(suf):
        sym = f"{sym}{suf}"
    return sym

def _req(url, params, logger):
    try:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 401:
            logger("  401 Unauthorized (API key sin permiso para este endpoint/period).")
            return None, 401
        r.raise_for_status()
        js = r.json() or []
        return js, r.status_code
    except Exception as e:
        logger(f"  error request: {e}")
        return None, None

class Command(BaseCommand):
    help = "Descarga estados trimestrales/anuales desde FMP y los guarda en Statement (IS/BS)."

    def add_arguments(self, parser):
        parser.add_argument("--tickers", nargs="*", help="Limitar a ciertos tickers")
        parser.add_argument("--years", type=int, default=8, help="Años hacia atrás (default 8)")
        parser.add_argument("--suffix", type=str, default="", help="Sufijo de exchange (p.ej. .L .PA .MX .SA .NS .HK)")
        parser.add_argument("--period", type=str, default="quarter", choices=["quarter","annual"],
                            help="Periodo de estados (quarter/annual). En demo/free suele permitirse solo 'annual'.")

        parser.add_argument("--sleep", type=float, default=0.2, help="Pausa entre requests (seg)")

    def handle(self, *args, **opts):
        api_key = os.getenv("FMP_API_KEY")
        if not api_key:
            raise CommandError("Falta FMP_API_KEY en el entorno (setx FMP_API_KEY TU_TOKEN)")

        years  = int(opts["years"])
        limit_q = years * 4 + 4
        limit_a = years + 2
        suffix = (opts.get("suffix") or "").strip()
        period = (opts.get("period") or "quarter").lower()
        sleep  = float(opts.get("sleep") or 0.2)

        # Si estás en demo/free y pides 'quarter', forzamos a 'annual'
        if api_key.lower() == "demo" and period == "quarter":
            self.stdout.write(self.style.NOTICE("API demo detectada → usando 'annual' (quarterly restringido)."))
            period = "annual"

        qs = Company.objects.all()
        if opts.get("tickers"):
            qs = qs.filter(ticker__in=[t.upper() for t in opts["tickers"]])

        for c in qs:
            sym = _norm_symbol(c, suffix)
            lim = limit_q if period == "quarter" else limit_a
            self.stdout.write(f"[{c.ticker}] {sym} (últimos {years} años, period={period})")

            # --- Income Statement ---
            url_is = f"{BASE}/income-statement/{sym}"
            data_is, code_is = _req(url_is, {"period": period, "limit": lim, "apikey": api_key}, self.stderr.write)

            # Fallback: si 401 y estabas pidiendo quarter, reintenta annual
            if code_is == 401 and period == "quarter":
                self.stdout.write(self.style.NOTICE("  Reintentando Income Statement con period=annual ..."))
                data_is, code_is = _req(url_is, {"period": "annual", "limit": limit_a, "apikey": api_key}, self.stderr.write)

            # --- Balance Sheet ---
            url_bs = f"{BASE}/balance-sheet-statement/{sym}"
            data_bs, code_bs = _req(url_bs, {"period": period, "limit": lim, "apikey": api_key}, self.stderr.write)
            if code_bs == 401 and period == "quarter":
                self.stdout.write(self.style.NOTICE("  Reintentando Balance Sheet con period=annual ..."))
                data_bs, code_bs = _req(url_bs, {"period": "annual", "limit": limit_a, "apikey": api_key}, self.stderr.write)

            created, updated = 0, 0
            with transaction.atomic():
                # ----- IS -----
                for row in (data_is or []):
                    d = _iso(row.get("date") or row.get("calendarYear"))
                    if not d:
                        continue
                    payload = {
                        "Revenue": row.get("revenue"),
                        "NetIncome": row.get("netIncome"),
                        "EPS": row.get("eps"),
                        "EBITDA": row.get("ebitda"),
                        "WeightedAverageShsOutDil": row.get("weightedAverageShsOutDil"),
                        # Para derivar EBITDA si falta:
                        "OperatingIncome": row.get("operatingIncome"),
                        "DepreciationAndAmortization": row.get("depreciationAndAmortization"),
                    }
                    obj, was_created = Statement.objects.update_or_create(
                        company=c, statement_type="IS", period_type="Q" if period=="quarter" else "Y",
                        period_end=d, defaults={"json_payload": payload},
                    )
                    if not was_created:
                        data = obj.json_payload or {}
                        data.update({k: v for k, v in payload.items() if v is not None})
                        obj.json_payload = data
                        obj.save(update_fields=["json_payload"])
                        updated += 1
                    else:
                        created += 1

                # ----- BS -----
                for row in (data_bs or []):
                    d = _iso(row.get("date") or row.get("calendarYear"))
                    if not d:
                        continue
                    payload = {
                        "CashAndCashEquivalents": row.get("cashAndCashEquivalents"),
                        "ShortTermDebt": row.get("shortTermDebt"),
                        "LongTermDebt": row.get("longTermDebt"),
                        "CommonStockSharesOutstanding": row.get("commonStockSharesOutstanding"),
                    }
                    obj, was_created = Statement.objects.update_or_create(
                        company=c, statement_type="BS", period_type="Q" if period=="quarter" else "Y",
                        period_end=d, defaults={"json_payload": payload},
                    )
                    if not was_created:
                        data = obj.json_payload or {}
                        data.update({k: v for k, v in payload.items() if v is not None})
                        obj.json_payload = data
                        obj.save(update_fields=["json_payload"])
                        updated += 1
                    else:
                        created += 1

            self.stdout.write(f"  IS/BS: nuevos={created}, actualizados={updated}")
            time.sleep(sleep)

        self.stdout.write(self.style.SUCCESS("FMP fundamentals: ingesta completada"))
