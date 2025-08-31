# charts/views.py
from __future__ import annotations

import csv
from typing import Dict, List

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from companies.models import Company
from fundamentals.models import Metric


# -----------------------------
# Utilidades
# -----------------------------
def _safe_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _latest_metric_map(key: str) -> Dict[int, float]:
    """
    Devuelve {company_id: ultimo_valor} para la métrica 'key'
    tomando el registro más reciente por compañía.
    """
    qs = (
        Metric.objects.filter(key=key)
        .order_by("company_id", "-period_end", "-id")
        .values("company_id", "value")
    )
    out, seen = {}, set()
    for row in qs:
        cid = row["company_id"]
        if cid in seen:
            continue
        out[cid] = _safe_float(row["value"])
        seen.add(cid)
    return out


def _csv_response(filename: str, rows: List[dict], headers: List[str], keys: List[str]) -> HttpResponse:
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    w = csv.writer(resp)
    w.writerow(headers)
    for r in rows:
        w.writerow([r.get(k, "") for k in keys])
    return resp


# -----------------------------
# Screener
# -----------------------------
@cache_page(60)  # 1 minuto de caché (ajusta o elimina durante desarrollo)
def screener_view(request):
    sector_q = (request.GET.get("sector") or "").strip()
    min_mcap_q = _safe_float((request.GET.get("min_mcap") or "").strip())
    order_q = (request.GET.get("order") or "pe_asc").strip()
    limit_q = int(request.GET.get("limit") or 100)
    fmt_q = (request.GET.get("format") or "").lower()

    # Trae mapas de métricas "último valor por compañía"
    maps = {
        "PE_TTM": _latest_metric_map("PE_TTM"),
        "EV_EBITDA": _latest_metric_map("EV_EBITDA"),
        "EV_Sales": _latest_metric_map("EV_Sales"),
        "FCF_Yield": _latest_metric_map("FCF_Yield"),
        "NetMargin_TTM": _latest_metric_map("NetMargin_TTM"),
        "MarketCap": _latest_metric_map("MarketCap"),
        "RSI_14": _latest_metric_map("RSI_14"),
        "Revenue_YoY": _latest_metric_map("Revenue_YoY"),
    }

    # Compañías base (opcionalmente filtradas por sector)
    companies = Company.objects.only("id", "ticker", "name", "sector", "currency")
    if sector_q:
        companies = companies.filter(sector__iexact=sector_q)

    rows = []
    for c in companies:
        mcap = maps["MarketCap"].get(c.id)

        # Filtro de market cap mínimo
        if min_mcap_q is not None and (mcap is None or mcap < min_mcap_q):
            continue

        rows.append(
            {
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "currency": c.currency,
                "marketcap": mcap,
                "pe_ttm": maps["PE_TTM"].get(c.id),
                "ev_sales": maps["EV_Sales"].get(c.id),
                "ev_ebitda": maps["EV_EBITDA"].get(c.id),
                "fcf_yield": maps["FCF_Yield"].get(c.id),
                "rev_yoy": maps["Revenue_YoY"].get(c.id),
                "rsi14": maps["RSI_14"].get(c.id),
            }
        )

    # Ordenamiento
    # order= pe_asc | pe_desc | evs_asc | evs_desc | yoy_desc | yoy_asc | rsi_asc | rsi_desc | mcap_desc | mcap_asc
    order_map = {
        "pe_asc": ("pe_ttm", False),
        "pe_desc": ("pe_ttm", True),
        "evs_asc": ("ev_sales", False),
        "evs_desc": ("ev_sales", True),
        "yoy_desc": ("rev_yoy", True),
        "yoy_asc": ("rev_yoy", False),
        "rsi_asc": ("rsi14", False),
        "rsi_desc": ("rsi14", True),
        "mcap_desc": ("marketcap", True),
        "mcap_asc": ("marketcap", False),
    }
    sort_key, reverse = order_map.get(order_q, ("pe_ttm", False))

    def _key(r):
        v = r.get(sort_key)
        # Forzamos que None quede al final
        return (v is None, v)

    rows.sort(key=_key, reverse=reverse)

    # Límite
    rows = rows[: max(1, min(limit_q, 1000))]

    # CSV si se pide ?format=csv
    if fmt_q == "csv":
        headers = [
            "Ticker",
            "Name",
            "Sector",
            "MarketCap",
            "P/E (TTM)",
            "EV/Sales",
            "EV/EBITDA",
            "FCF Yield",
            "Revenue YoY",
            "RSI 14",
        ]
        keys = ["ticker", "name", "sector", "marketcap", "pe_ttm", "ev_sales", "ev_ebitda", "fcf_yield", "rev_yoy", "rsi14"]
        return _csv_response("screener.csv", rows, headers, keys)

    context = {
        "rows": rows,
        "selected_sector": sector_q,
        "min_mcap": "" if min_mcap_q is None else min_mcap_q,
        "order": order_q,
        "limit": limit_q,
        "sectors": Company.objects.order_by("sector")
        .values_list("sector", flat=True)
        .distinct(),
    }
    return render(request, "screener.html", context)


# -----------------------------
# Ranking P/E
# -----------------------------
@cache_page(60 * 5)  # 5 minutos
def pe_view(request):
    """Ranking por P/E (más bajo primero)."""
    sector_q = (request.GET.get("sector") or "").strip()
    min_mcap_q = _safe_float((request.GET.get("min_mcap") or "").strip())

    pe_map = _latest_metric_map("PE_TTM")
    mcap_map = _latest_metric_map("MarketCap")

    companies = Company.objects.only("id", "ticker", "name", "sector")
    if sector_q:
        companies = companies.filter(sector__iexact=sector_q)

    rows = []
    for c in companies:
        pe = pe_map.get(c.id)
        mcap = mcap_map.get(c.id)

        if min_mcap_q is not None and (mcap is None or mcap < min_mcap_q):
            continue

        rows.append(
            {
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "marketcap": mcap,
                "pe_ttm": pe,
            }
        )

    rows.sort(key=lambda r: (r["pe_ttm"] is None, r["pe_ttm"] if r["pe_ttm"] is not None else float("inf")))
    rows = rows[:200]

    return render(
        request,
        "pe.html",
        {
            "rows": rows,
            "selected_sector": sector_q,
            "min_mcap": "" if min_mcap_q is None else min_mcap_q,
            "sectors": Company.objects.order_by("sector")
            .values_list("sector", flat=True)
            .distinct(),
        },
    )
