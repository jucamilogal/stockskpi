import pandas as pd
from fundamentals.models import Statement, Metric
from marketdata.models import PriceBar

def _safe_df(qs):
    if not qs.exists(): return None
    df = pd.DataFrame([{"period_end": s.period_end, **s.json_payload} for s in qs])
    if df.empty: return None
    df.set_index("period_end", inplace=True)
    df.sort_index(inplace=True)
    for col in df.columns:  # ensure numeric
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def _last_close(company):
    last = PriceBar.objects.filter(company=company).order_by("-date").first()
    return float(last.close) if last else None, (last.date if last else None)

def _write_metric(company, key, period_end, value, ttm=False):
    if value is None or pd.isna(value): return
    Metric.objects.update_or_create(
        company=company, key=key, period_end=period_end,
        period_type=("TTM" if ttm else "Q"),
        defaults={"value": float(value)}
    )

def compute_metrics_for_company(c):
    # ---------- Income Statement ----------
    is_q = Statement.objects.filter(company=c, statement_type="IS", period_type="Q").order_by("period_end")
    df = _safe_df(is_q)
    if df is not None:
        # core TTMs
        for k in ["Revenue","NetIncome","OperatingIncome","GrossProfit","DA","SGA","RnD"]:
            if k in df: df[f"{k}_TTM"] = df[k].rolling(4, min_periods=4).sum()
        # growth
        if "Revenue" in df:
            df["Revenue_QoQ"] = df["Revenue"].pct_change(1, fill_method=None)
            df["Revenue_YoY"] = df["Revenue"].pct_change(4, fill_method=None)
        # margins (quarterly + TTM)
        def _div(a,b): 
            return (a/b).replace([pd.NaT, pd.NaN, pd.inf, -pd.inf], pd.NA) if (a is not None and b is not None) else None
        if "GrossProfit" in df and "Revenue" in df:
            df["GrossMargin"] = df["GrossProfit"] / df["Revenue"]
        if "OperatingIncome" in df and "Revenue" in df:
            df["OpMargin"] = df["OperatingIncome"] / df["Revenue"]
        if "NetIncome" in df and "Revenue" in df:
            df["NetMargin"] = df["NetIncome"] / df["Revenue"]
        if "GrossProfit_TTM" in df and "Revenue_TTM" in df:
            df["GrossMargin_TTM"] = df["GrossProfit_TTM"] / df["Revenue_TTM"]
        if "OperatingIncome_TTM" in df and "Revenue_TTM" in df:
            df["OpMargin_TTM"] = df["OperatingIncome_TTM"] / df["Revenue_TTM"]
        if "NetIncome_TTM" in df and "Revenue_TTM" in df:
            df["NetMargin_TTM"] = df["NetIncome_TTM"] / df["Revenue_TTM"]
        # EBITDA TTM (approx: OpInc + D&A)
        if "OperatingIncome_TTM" in df and "DA_TTM" in df:
            df["EBITDA_TTM"] = df["OperatingIncome_TTM"] + df["DA_TTM"]

        # ---------- Cash Flow ----------
        cf_q = Statement.objects.filter(company=c, statement_type="CF", period_type="Q").order_by("period_end")
        cdf = _safe_df(cf_q)
        if cdf is not None:
            if "CFO" in cdf: cdf["CFO_TTM"] = cdf["CFO"].rolling(4, min_periods=4).sum()
            if "CapEx" in cdf: cdf["CapEx_TTM"] = cdf["CapEx"].rolling(4, min_periods=4).sum()
            if "CFO_TTM" in cdf and "CapEx_TTM" in cdf:
                cdf["FCF_TTM"] = cdf["CFO_TTM"] - cdf["CapEx_TTM"]

        # ---------- Balance Sheet (latest point-in-time) ----------
        bs_q = Statement.objects.filter(company=c, statement_type="BS", period_type="Q").order_by("period_end")
        bdf = _safe_df(bs_q)
        last_bs = bdf.tail(1) if bdf is not None and not bdf.empty else None

        # ---------- Valuation (point-in-time using last close) ----------
        last_close, last_close_date = _last_close(c)
        shares = None
        if last_bs is not None:
            # prefer CommonShares; else diluted shares from IS last quarter
            if "CommonShares" in last_bs.columns and pd.notna(last_bs.iloc[0]["CommonShares"]):
                shares = float(last_bs.iloc[0]["CommonShares"])
        if shares is None and df is not None and "DilutedShares" in df.columns and not df["DilutedShares"].dropna().empty:
            shares = float(df["DilutedShares"].dropna().iloc[-1])

        market_cap = (last_close * shares) if (last_close and shares) else None
        cash = float(last_bs.iloc[0]["Cash"]) if last_bs is not None and "Cash" in last_bs.columns and pd.notna(last_bs.iloc[0]["Cash"]) else None
        debt = 0.0
        if last_bs is not None:
            for k in ["ShortDebt","LongDebt"]:
                if k in last_bs.columns and pd.notna(last_bs.iloc[0][k]): debt += float(last_bs.iloc[0][k])
        net_debt = (debt - (cash or 0.0)) if (debt is not None) else None
        ev = (market_cap + debt - (cash or 0.0)) if (market_cap is not None and debt is not None) else None

        # ---------- Write back latest metrics ----------
        # Pick a common latest period_end to stamp: prefer latest IS quarter
        pe_is = df.index[-1] if df is not None and not df.empty else None
        pe_cf = cdf.index[-1] if cdf is not None and not cdf.empty else None
        pe_bs = bdf.index[-1] if bdf is not None and not bdf.empty else None
        pe = pe_is or pe_cf or pe_bs

        if df is not None and pe is not None:
            for col in [x for x in ["Revenue_QoQ","Revenue_YoY","Revenue_TTM","NetIncome_TTM","GrossMargin_TTM","OpMargin_TTM","NetMargin_TTM","EBITDA_TTM"] if x in df.columns]:
                _write_metric(c, col, pe, df.iloc[-1][col], ttm=col.endswith("_TTM"))
        if cdf is not None and pe_cf is not None:
            for col in [x for x in ["CFO_TTM","CapEx_TTM","FCF_TTM"] if x in cdf.columns]:
                _write_metric(c, col, pe_cf, cdf.iloc[-1][col], ttm=True)
            # FCF margin (TTM)
            if "FCF_TTM" in cdf.columns and df is not None and "Revenue_TTM" in df.columns:
                fcf_margin = cdf.iloc[-1]["FCF_TTM"] / df.iloc[-1]["Revenue_TTM"] if df.iloc[-1]["Revenue_TTM"] else None
                _write_metric(c, "FCF_Margin_TTM", pe_cf, fcf_margin, ttm=True)

        if last_bs is not None and pe_bs is not None:
            # Leverage / liquidity
            ta = float(last_bs.iloc[0]["TotalAssets"]) if "TotalAssets" in last_bs.columns and pd.notna(last_bs.iloc[0]["TotalAssets"]) else None
            cl = float(last_bs.iloc[0]["CurrentLiabilities"]) if "CurrentLiabilities" in last_bs.columns and pd.notna(last_bs.iloc[0]["CurrentLiabilities"]) else None
            ca = float(last_bs.iloc[0]["CurrentAssets"]) if "CurrentAssets" in last_bs.columns and pd.notna(last_bs.iloc[0]["CurrentAssets"]) else None
            debt_to_assets = (debt/ta) if (ta and debt is not None) else None
            current_ratio = (ca/cl) if (ca and cl) else None
            _write_metric(c, "NetDebt", pe_bs, net_debt)
            _write_metric(c, "DebtToAssets", pe_bs, debt_to_assets)
            _write_metric(c, "CurrentRatio", pe_bs, current_ratio)

        if pe is not None:
            # Valuation metrics (point-in-time, store as 'Q')
            _write_metric(c, "Price", pe, last_close)
            _write_metric(c, "Shares", pe, shares)
            _write_metric(c, "MarketCap", pe, market_cap)
            _write_metric(c, "EnterpriseValue", pe, ev)
            if ev is not None and df is not None and "Revenue_TTM" in df.columns and df.iloc[-1]["Revenue_TTM"]:
                _write_metric(c, "EV_Sales", pe, ev / df.iloc[-1]["Revenue_TTM"])
            if ev is not None and "EBITDA_TTM" in (df.columns if df is not None else []):
                ebitda = df.iloc[-1]["EBITDA_TTM"]
                if ebitda and ebitda > 0:
                    _write_metric(c, "EV_EBITDA", pe, ev / ebitda)
            # P/E (TTM)
            if market_cap and shares and df is not None and "NetIncome_TTM" in df.columns and df.iloc[-1]["NetIncome_TTM"]:
                eps_ttm = df.iloc[-1]["NetIncome_TTM"] / shares
                if eps_ttm and eps_ttm > 0:
                    _write_metric(c, "PE_TTM", pe, (last_close / eps_ttm) if last_close else None)
            # FCF Yield
            if market_cap and cdf is not None and "FCF_TTM" in cdf.columns and cdf.iloc[-1]["FCF_TTM"]:
                _write_metric(c, "FCF_Yield", pe, cdf.iloc[-1]["FCF_TTM"] / market_cap)
