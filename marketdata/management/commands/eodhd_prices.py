# marketdata/management/commands/eodhd_prices.py
import os
import time
import datetime as dt
from decimal import Decimal

import requests
from django.core.management.base import BaseCommand, CommandError
from companies.models import Company
from marketdata.models import PriceBar


EODHD_BASE = "https://eodhd.com/api/eod/{symbol}"  # daily candles


def _symbol_for_company(c: Company, suffix: str) -> str:
    """
    Devuelve el símbolo a consultar en EODHD:
    - Si el modelo Company trae un atributo 'eod_symbol', úsalo.
    - Si no, usa 'ticker' + 'suffix' (ej: '.US', '.MX', '.L', '.NS', '.HK').
    """
    sym = getattr(c, "eod_symbol", None) or c.ticker
    sym = sym.strip().upper()
    if suffix and not sym.endswith(suffix.upper()):
        sym = f"{sym}{suffix.upper()}"
    return sym


class Command(BaseCommand):
    help = "Descarga/actualiza precios EOD globales desde EODHD y los guarda en PriceBar."

    def add_arguments(self, parser):
        parser.add_argument("--tickers", nargs="*", help="Limitar a ciertos tickers (ej: AAPL TSCO PYPL)")
        parser.add_argument("--suffix", type=str, default="", help="Sufijo de exchange (ej: .US, .MX, .L, .NS, .HK)")
        parser.add_argument("--years", type=int, default=8, help="Años hacia atrás (default 8)")
        parser.add_argument("--sleep", type=float, default=0.25, help="Pausa entre requests (seg)")

    def handle(self, *args, **opts):
        api_key = os.getenv("EODHD_API_KEY")
        if not api_key:
            raise CommandError("Falta EODHD_API_KEY en el entorno (export EODHD_API_KEY=...)")

        years = int(opts["years"])
        since = dt.date.today() - dt.timedelta(days=years * 365)
        suffix = (opts.get("suffix") or "").strip()
        sleep = float(opts.get("sleep") or 0.25)

        qs = Company.objects.all()
        if opts.get("tickers"):
            qs = qs.filter(ticker__in=[t.upper() for t in opts["tickers"]])

        total = 0
        for c in qs:
            symbol = _symbol_for_company(c, suffix)
            url = EODHD_BASE.format(symbol=symbol)
            params = {
                "api_token": api_key,
                "from": since.isoformat(),
                "period": "d",
                "fmt": "json",
            }
            self.stdout.write(f"[{c.ticker}] {symbol}  →  {since}..today")
            try:
                r = requests.get(url, params=params, timeout=60)
                r.raise_for_status()
                data = r.json()
                if not data:
                    self.stderr.write("  (sin datos)")
                    time.sleep(sleep)
                    continue
            except Exception as e:
                self.stderr.write(f"  error request: {e}")
                time.sleep(sleep)
                continue

            # Esperado: lista de dicts con keys: date, open, high, low, close, volume
            for row in data:
                d = row.get("date")
                if not d:
                    continue
                try:
                    date_obj = dt.date.fromisoformat(d[:10])
                except Exception:
                    continue

                try:
                    PriceBar.objects.update_or_create(
                        company=c,
                        date=date_obj,
                        defaults={
                            "open":   Decimal(str(row.get("open") or 0)),
                            "high":   Decimal(str(row.get("high") or 0)),
                            "low":    Decimal(str(row.get("low") or 0)),
                            "close":  Decimal(str(row.get("close") or 0)),
                            "volume": int(row.get("volume") or 0),
                        },
                    )
                    total += 1
                except Exception as e:
                    self.stderr.write(f"  {c.ticker} {date_obj}: error guardando ({e})")

            time.sleep(sleep)

        self.stdout.write(self.style.SUCCESS(f"Listo. Registros procesados/actualizados: {total}"))
