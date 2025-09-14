# marketdata/management/commands/refresh_prices.py
import datetime as dt
from decimal import Decimal

import pandas as pd
from django.core.management.base import BaseCommand
from companies.models import Company
from marketdata.models import PriceBar


class Command(BaseCommand):
    help = "Descarga/actualiza precios diarios (close) desde yfinance sin duplicar registros."

    def add_arguments(self, parser):
        parser.add_argument("--tickers", nargs="*", help="Limitar a ciertos tickers (por ej. AAPL MSFT)")
        parser.add_argument("--years", type=int, default=5, help="Años hacia atrás (default 5)")

    def handle(self, *args, **opts):
        try:
            import yfinance as yf
        except Exception:
            self.stderr.write("Necesitas yfinance en requirements.txt (pip install yfinance).")
            raise

        since = dt.date.today() - dt.timedelta(days=int(opts["years"]) * 365)

        qs = Company.objects.all()
        if opts.get("tickers"):
            qs = qs.filter(ticker__in=[t.upper() for t in opts["tickers"]])

        total = 0
        for comp in qs:
            self.stdout.write(f"[{comp.ticker}] bajando precios desde {since} ...")
            try:
                df = yf.download(
                    comp.ticker,
                    start=since.isoformat(),
                    progress=False,
                    auto_adjust=False,
                )
            except Exception as e:
                self.stderr.write(f"  error yfinance: {e}")
                continue

            if df is None or df.empty:
                self.stderr.write("  sin datos")
                continue

            # Normaliza dataframe
            df = df.reset_index()  # mueve el índice de fechas a columna
            # Algunas versiones devuelven 'Datetime' o 'index' en lugar de 'Date'
            if "Date" not in df.columns:
                if "Datetime" in df.columns:
                    df = df.rename(columns={"Datetime": "Date"})
                elif "index" in df.columns:
                    df = df.rename(columns={"index": "Date"})
            # Nos quedamos sólo con lo necesario
            wanted = ["Date", "Open", "High", "Low", "Close", "Volume"]
            missing = [c for c in wanted if c not in df.columns]
            if missing:
                self.stderr.write(f"  columnas faltantes en yfinance: {missing}")
                continue

            # Iteración robusta por posiciones (evita problemas de nombre atributo)
            for d_val, o, h, l, c_close, v in df[wanted].itertuples(index=False, name=None):
                try:
                    d = pd.to_datetime(d_val).date()
                except Exception:
                    # último recurso: intenta cast directo
                    d = d_val if isinstance(d_val, dt.date) else None
                if d is None or pd.isna(c_close):
                    continue

                try:
                    obj, _ = PriceBar.objects.update_or_create(
                        company=comp,
                        date=d,
                        defaults={
                            "open": Decimal(str(0 if pd.isna(o) else float(o))),
                            "high": Decimal(str(0 if pd.isna(h) else float(h))),
                            "low":  Decimal(str(0 if pd.isna(l) else float(l))),
                            "close": Decimal(str(float(c_close))),
                            "volume": 0 if pd.isna(v) else int(v),
                        },
                    )
                    total += 1
                except Exception as e:
                    self.stderr.write(f"  {comp.ticker} {d}: error guardando ({e})")
                    continue

        self.stdout.write(self.style.SUCCESS(f"Listo. Registros procesados: {total}"))
