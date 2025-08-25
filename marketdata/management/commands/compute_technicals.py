from django.core.management.base import BaseCommand
from companies.models import Company
from marketdata.models import PriceBar
from fundamentals.models import Metric
import pandas as pd

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / roll_down
    return 100 - (100 / (1 + rs))

class Command(BaseCommand):
    help = "Compute basic technicals (SMA50/200, RSI14, 52w distances, 30d volatility)"

    def handle(self, *args, **kwargs):
        n = 0
        for c in Company.objects.all():
            qs = PriceBar.objects.filter(company=c).order_by("date").values("date","close")
            if not qs.exists():
                continue
            df = pd.DataFrame(qs)
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df.dropna(subset=["close"], inplace=True)
            if df.empty:
                continue

            df["SMA_50"] = df["close"].rolling(50).mean()
            df["SMA_200"] = df["close"].rolling(200).mean()
            df["RSI_14"] = rsi(df["close"], 14)

            # 52w window ~ 252 trading days
            df["52w_high"] = df["close"].rolling(252).max()
            df["52w_low"] = df["close"].rolling(252).min()
            df["DistTo52wHigh"] = df["close"]/df["52w_high"] - 1.0
            df["DistTo52wLow"] = df["close"]/df["52w_low"] - 1.0

            # 30d realized vol (annualized)
            ret = df["close"].pct_change()
            df["Vol_30d"] = ret.rolling(30).std() * (252**0.5)

            last = df.tail(1).iloc[0]
            pe = last["date"]

            def write(key, val):
                if pd.notna(val):
                    Metric.objects.update_or_create(
                        company=c, key=key, period_end=pe, period_type="Q",
                        defaults={"value": float(val)}
                    )

            for k in ["SMA_50","SMA_200","RSI_14","DistTo52wHigh","DistTo52wLow","Vol_30d","close"]:
                write(k, last.get(k))
            # also store Close as Price (consistency with fundamentals)
            write("Price", last["close"])
            n += 1

        self.stdout.write(self.style.SUCCESS(f"Technicals computed for {n} companies"))
