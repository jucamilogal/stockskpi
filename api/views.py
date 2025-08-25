from django.http import HttpResponse
from rest_framework.viewsets import ReadOnlyModelViewSet
from rankings.models import Ranking, RankingResult
from .serializers import RankingResultSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from companies.models import Company
from charts.services import revenue_trend, price_trend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import csv, math

from companies.models import Company
from fundamentals.models import Metric

class LatestRankingViewSet(ReadOnlyModelViewSet):
    serializer_class = RankingResultSerializer

    @method_decorator(cache_page(60 * 5))  # 5 min cache
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        r = Ranking.objects.order_by("-run_at").first()
        qs = RankingResult.objects.filter(ranking=r).select_related("company").order_by("rank")
        p = self.request.query_params

        # Optional filters
        sector = p.get("sector")
        if sector:
            qs = qs.filter(company__sector__iexact=sector)

        # Min market cap (uses Metric table)
        min_mc = p.get("min_marketcap")
        if min_mc:
            try:
                min_mc_val = float(min_mc)
                qs = qs.filter(company__metric__key="MarketCap", company__metric__value__gte=min_mc_val)
            except ValueError:
                pass

        # Restrict to specific tickers: ?tickers=AAPL,MSFT
        tickers = p.get("tickers")
        if tickers:
            tickers_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            qs = qs.filter(company__ticker__in=tickers_list)

        # Limit results
        limit = p.get("limit")
        if limit:
            try:
                qs = qs[: int(limit)]
            except ValueError:
                pass

        return qs

class CompanyRevenueChart(APIView):
    def get(self, request, ticker):
        c = get_object_or_404(Company, ticker=ticker.upper())
        return Response({"figure": revenue_trend(c)})

class CompanyPriceChart(APIView):
    def get(self, request, ticker):
        c = get_object_or_404(Company, ticker=ticker.upper())
        return Response({"figure": price_trend(c)})
    
class MetricsLatestByTicker(APIView):
    """
    Return latest value per metric key for a company.
    Works on SQLite by reducing in Python (no DISTINCT ON required).
    """
    @method_decorator(cache_page(60 * 10))  # 10 min cache
    def get(self, request, ticker):
        c = get_object_or_404(Company, ticker=ticker.upper())
        # Pull all metrics for the company; keep the newest per key
        data = {}
        for m in Metric.objects.filter(company=c).order_by("key", "-period_end"):
            k = m.key
            if k not in data:  # first seen is latest due to ordering desc by period_end
                data[k] = {
                    "value": float(m.value),
                    "period_end": m.period_end,
                    "period_type": m.period_type,
                }
        return Response({"ticker": c.ticker, "metrics": data})

class PERanking(APIView):
    """
    Returns companies ranked by lowest P/E (TTM) first.
    Filters:
      - ?sector=Technology
      - ?min_marketcap=200000000000  (USD)
      - ?tickers=AAPL,MSFT
      - ?limit=50
    """
    @method_decorator(cache_page(60 * 5))  # cache 5 minutes
    def get(self, request):
        p = request.query_params
        sector = p.get("sector")
        min_mc = p.get("min_marketcap")
        tickers = p.get("tickers")
        limit = p.get("limit")

        qs = Company.objects.all()
        if sector:
            qs = qs.filter(sector__iexact=sector)
        if tickers:
            tickers_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            qs = qs.filter(ticker__in=tickers_list)

        rows = []
        for c in qs:
            pe = None
            pe_obj = Metric.objects.filter(company=c, key="PE_TTM").order_by("-period_end").first()
            if pe_obj and pe_obj.value is not None:
                pe = float(pe_obj.value)

            if not pe or pe <= 0:  # ignore missing or negative P/E
                continue

            mc_obj = Metric.objects.filter(company=c, key="MarketCap").order_by("-period_end").first()
            marketcap = float(mc_obj.value) if mc_obj and mc_obj.value is not None else None

            # optional market-cap filter
            if min_mc:
                try:
                    if marketcap is None or marketcap < float(min_mc):
                        continue
                except ValueError:
                    pass

            rows.append({
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "pe_ttm": round(pe, 3),
                "marketcap": marketcap,
            })

        rows.sort(key=lambda r: r["pe_ttm"])  # lowest P/E on top

        if limit:
            try:
                rows = rows[: int(limit)]
            except ValueError:
                pass

        return Response(rows)
    
class Screener(APIView):
    """
    Multi-metric screener with CSV export.
    Filters use the format: <metric_alias>__<op>=<value>
      ops: gte, lte, gt, lt, eq, ne, between (a,b)
    Aliases (case-insensitive) map to Metric.key:
      pe_ttm, ev_sales, ev_ebitda, fcf_margin_ttm, revenue_yoy,
      op_margin_ttm, net_margin_ttm, debttoassets, currentratio,
      rsi_14, sma_50, sma_200, distto52whigh, distto52wlow,
      vol_30d, marketcap, price, revenue_ttm, netincome_ttm

    Extra params:
      sector=Technology
      min_marketcap=200000000000
      tickers=AAPL,MSFT
      order=-pe_ttm   (prefix '-' for descending)
      limit=50
      fields=ticker,name,sector,pe_ttm,marketcap,ev_sales
      format=csv      (CSV instead of JSON)
    """
    # alias -> Metric.key
    ALIASES = {
        "pe_ttm": "PE_TTM",
        "ev_sales": "EV_Sales",
        "ev_ebitda": "EV_EBITDA",
        "fcf_margin_ttm": "FCF_Margin_TTM",
        "revenue_yoy": "Revenue_YoY",
        "op_margin_ttm": "OpMargin_TTM",
        "net_margin_ttm": "NetMargin_TTM",
        "debttoassets": "DebtToAssets",
        "currentratio": "CurrentRatio",
        "rsi_14": "RSI_14",
        "sma_50": "SMA_50",
        "sma_200": "SMA_200",
        "distto52whigh": "DistTo52wHigh",
        "distto52wlow": "DistTo52wLow",
        "vol_30d": "Vol_30d",
        "marketcap": "MarketCap",
        "price": "Price",
        "revenue_ttm": "Revenue_TTM",
        "netincome_ttm": "NetIncome_TTM",
    }
    DEFAULT_FIELDS = ["rank","ticker","name","sector","pe_ttm","marketcap","ev_sales","fcf_margin_ttm","revenue_yoy"]

    @method_decorator(cache_page(60 * 3))  # cache 3 minutes
    def get(self, request):
        p = request.query_params

        # --- Build company candidate list ---
        qs = Company.objects.all()
        sector = p.get("sector")
        if sector:
            qs = qs.filter(sector__iexact=sector)

        tickers = p.get("tickers")
        if tickers:
            tickers_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            qs = qs.filter(ticker__in=tickers_list)

        companies = list(qs.values("id", "ticker", "name", "sector"))
        if not companies:
            return Response([])

        ids = [c["id"] for c in companies]

        # --- Pull latest metric values for *all* companies in one pass ---
        latest = {}  # company_id -> { Metric.key: value }
        mq = Metric.objects.filter(company_id__in=ids).order_by("company_id", "key", "-period_end")
        for m in mq:
            d = latest.setdefault(m.company_id, {})
            if m.key not in d:   # first seen is newest due to -period_end
                try:
                    d[m.key] = float(m.value)
                except (TypeError, ValueError):
                    pass

        # --- Helper to read metric by alias from a row map ---
        def get_alias(dct, alias):
            key = self.ALIASES.get(alias)
            return dct.get(key) if key else None

        # --- Build rows (with alias keys for easy filtering/sorting) ---
        rows = []
        for c in companies:
            m = latest.get(c["id"], {})
            row = {
                "ticker": c["ticker"],
                "name": c["name"],
                "sector": c["sector"],
                # expose convenient alias keys (lowercase)
                "pe_ttm": get_alias(m, "pe_ttm"),
                "ev_sales": get_alias(m, "ev_sales"),
                "ev_ebitda": get_alias(m, "ev_ebitda"),
                "fcf_margin_ttm": get_alias(m, "fcf_margin_ttm"),
                "revenue_yoy": get_alias(m, "revenue_yoy"),
                "op_margin_ttm": get_alias(m, "op_margin_ttm"),
                "net_margin_ttm": get_alias(m, "net_margin_ttm"),
                "debttoassets": get_alias(m, "debttoassets"),
                "currentratio": get_alias(m, "currentratio"),
                "rsi_14": get_alias(m, "rsi_14"),
                "sma_50": get_alias(m, "sma_50"),
                "sma_200": get_alias(m, "sma_200"),
                "distto52whigh": get_alias(m, "distto52whigh"),
                "distto52wlow": get_alias(m, "distto52wlow"),
                "vol_30d": get_alias(m, "vol_30d"),
                "marketcap": get_alias(m, "marketcap"),
                "price": get_alias(m, "price"),
                "revenue_ttm": get_alias(m, "revenue_ttm"),
                "netincome_ttm": get_alias(m, "netincome_ttm"),
            }
            rows.append(row)

        # --- Optional market cap floor BEFORE per-metric filters ---
        min_mc = p.get("min_marketcap")
        if min_mc:
            try:
                mm = float(min_mc)
                rows = [r for r in rows if (r.get("marketcap") is not None and r["marketcap"] >= mm)]
            except ValueError:
                pass

        # --- Apply dynamic metric filters: <alias>__<op>=value ---
        def parse_num_list(val):
            parts = [x for x in (val or "").split(",") if x.strip()]
            return [float(x) for x in parts]

        for qp, val in p.items():
            if "__" not in qp:
                continue
            alias, op = qp.lower().split("__", 1)
            if alias not in self.ALIASES:   # unknown metric alias
                continue
            # compare against alias key already inside row
            def keep(r):
                rv = r.get(alias)
                if rv is None or (isinstance(rv, float) and (math.isnan(rv) or math.isinf(rv))):
                    return False
                try:
                    if op == "gte":   return rv >= float(val)
                    if op == "lte":   return rv <= float(val)
                    if op == "gt":    return rv >  float(val)
                    if op == "lt":    return rv <  float(val)
                    if op == "eq":    return rv == float(val)
                    if op == "ne":    return rv != float(val)
                    if op == "between":
                        a, b = parse_num_list(val)
                        lo, hi = min(a, b), max(a, b)
                        return lo <= rv <= hi
                except Exception:
                    return False
                return True
            rows = [r for r in rows if keep(r)]

        # --- Sorting ---
        order = p.get("order")  # e.g. '-pe_ttm' or 'ev_sales'
        if order:
            desc = order.startswith("-")
            key_alias = order[1:].lower() if desc else order.lower()
            if key_alias in {"ticker","name","sector"}:
                rows.sort(key=lambda r: r.get(key_alias) or "", reverse=desc)
            else:
                rows.sort(key=lambda r: (float("inf") if r.get(key_alias) is None else r[key_alias]), reverse=desc)

        # --- Rank + limit ---
        for i, r in enumerate(rows, start=1):
            r["rank"] = i
        limit = p.get("limit")
        if limit:
            try: rows = rows[: int(limit)]
            except ValueError: pass

        # --- Field selection ---
        fields = self.DEFAULT_FIELDS
        if p.get("fields"):
            fields = [f.strip().lower() for f in p["fields"].split(",") if f.strip()]

        # --- CSV export ---
        if p.get("format") == "csv":
            resp = HttpResponse(content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="screener.csv"'
            writer = csv.DictWriter(resp, fieldnames=fields)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k) for k in fields})
            return resp

        # JSON response
        return Response([{k: r.get(k) for k in fields} for r in rows])