from django.core.management.base import BaseCommand
from companies.models import Company
from marketdata.models import PriceBar
import yfinance as yf
from datetime import date, timedelta
import pandas as pd

class Command(BaseCommand):
    help = "Load daily price bars via yfinance"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365*3)
        parser.add_argument("--ticker", type=str, default=None)  # optional: load just one

    def handle(self, *args, **opts):
        end = date.today()
        start = end - timedelta(days=opts["days"])

        qs = Company.objects.all()
        if opts["ticker"]:
            qs = qs.filter(ticker=opts["ticker"].upper())

        for c in qs:
            df = yf.download(
                c.ticker,
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,   # avoid FutureWarning + keep raw OHLCV
                progress=False,
                group_by="ticker",
                threads=False,
            )

            if df is None or df.empty:
                self.stdout.write(self.style.WARNING(f"No data for {c.ticker}"))
                continue

            # If yfinance returns a MultiIndex (e.g., ('AAPL','Open')), flatten to 'Open'
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[-1] for col in df.columns]

            required = {"Open", "High", "Low", "Close"}
            missing = required - set(df.columns)
            if missing:
                self.stdout.write(self.style.WARNING(f"{c.ticker} missing columns {missing}; skipping"))
                continue

            # Drop rows with missing OHLC (volume can be missing)
            df = df.dropna(subset=["Open", "High", "Low", "Close"])

            saved = 0
            for idx, row in df.iterrows():
                # Safe volume handling
                v = row.get("Volume", 0)
                if pd.isna(v):
                    v = 0
                else:
                    try:
                        v = int(v)
                    except Exception:
                        v = 0

                PriceBar.objects.update_or_create(
                    company=c,
                    date=idx.date(),
                    defaults=dict(
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=v,
                    ),
                )
                saved += 1

            self.stdout.write(self.style.SUCCESS(f"Loaded {saved} rows for {c.ticker}"))
