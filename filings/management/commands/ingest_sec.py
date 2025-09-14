# filings/management/commands/ingest_sec.py
import os
import time
import json
import math
import datetime as dt
from collections import defaultdict

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import make_aware

from companies.models import Company
from fundamentals.models import Statement

# --------------------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------------------
SEC_TICKERMAP_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL_TMPL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"

# tags que intentaremos para cada campo de nuestro payload
USGAAP = "us-gaap"
TAGS = {
    # Income Statement (durations)
    "Revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenue",
        "Revenues",
        "SalesRevenueGoodsNet",
    ],
    "NetIncome": [
        "NetIncomeLoss",
        "ProfitLoss",
    ],
    "EPS": [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasicAndDiluted",
        "EarningsPerShareBasic",
    ],
    "EBITDA": [
        "EarningsBeforeInterestTaxesDepreciationAndAmortization",
        # Si no existe, podríamos aproximar en otra versión sumando OperatingIncome + D&A
    ],

    # Balance Sheet (instants)
    "CashAndCashEquivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ],
    "ShortTermDebt": [
        "DebtCurrent",
        "ShortTermBorrowings",
    ],
    "LongTermDebt": [
        "LongTermDebtNoncurrent",
        "LongTermBorrowings",
        "LongTermDebt",
    ],
    "CommonStockSharesOutstanding": [
        "CommonStockSharesOutstanding",
    ],

    # Shares promedio (durations) — útil para métricas
    "WeightedAverageShsOutDil": [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingDiluted",
    ],
    # Income Statement (durations) – para derivar EBITDA si falta
"OperatingIncome": [
    "OperatingIncomeLoss",
],
"DepreciationAndAmortization": [
    "DepreciationAndAmortization",
    "DepreciationDepletionAndAmortization",
    "DepreciationAmortizationAndAccretionNet",
],
}

# unidades preferidas por campo
PREFERRED_UNITS = {
    "Revenue": {"USD"},
    "NetIncome": {"USD"},
    "EPS": {"USD/shares"},
    "EBITDA": {"USD"},
    "CashAndCashEquivalents": {"USD"},
    "ShortTermDebt": {"USD"},
    "LongTermDebt": {"USD"},
    "CommonStockSharesOutstanding": {"shares"},
    "WeightedAverageShsOutDil": {"shares"},
}

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def _ua():
    ua = os.getenv("SEC_USER_AGENT")
    if not ua:
        raise CommandError(
            "Define la variable de entorno SEC_USER_AGENT (ej: "
            "'Finboard/1.0 (Contact: tu_email@example.com)')"
        )
    return {"User-Agent": ua}

def _pad_cik(cik: str) -> str:
    cik = (cik or "").strip()
    return cik.zfill(10) if cik else ""

def _to_date(s):
    # SEC usa 'end' como 'YYYY-MM-DD'
    try:
        y, m, d = map(int, s.split("-"))
        return dt.date(y, m, d)
    except Exception:
        return None

def _is_quarter_point(p):
    # Preferimos puntos de trimestre (10-Q) o Q4 (a veces en 10-K)
    form = (p.get("form") or "").upper()
    fp = (p.get("fp") or "").upper()  # Q1/Q2/Q3/Q4/FY
    if form in {"10-Q"}:
        return True
    if form in {"10-K"} and fp in {"Q4", "FY"}:
        return True
    # Si no viene el form, usar pista por 'fp'
    return fp in {"Q1", "Q2", "Q3", "Q4"}

def _best_unit(units_dict, preferred: set[str]):
    """Devuelve el nombre de unidad preferida si existe, sino la primera disponible."""
    if not isinstance(units_dict, dict):
        return None
    if preferred:
        for u in preferred:
            if u in units_dict:
                return u
    # fallback: primera clave
    return next(iter(units_dict.keys()), None)

def _select_points(units_dict, preferred_units):
    """Filtra a quarterly points y devuelve lista [(end_date, value), ...]"""
    unit_name = _best_unit(units_dict, preferred_units)
    if not unit_name:
        return []
    out = []
    for p in units_dict[unit_name]:
        if not _is_quarter_point(p):
            continue
        end = _to_date(p.get("end") or "")
        if not end:
            continue
        v = p.get("val")
        try:
            fv = float(v)
        except Exception:
            continue
        # descarte NaN/inf
        if fv is None or math.isnan(fv) or math.isinf(fv):
            continue
        out.append((end, fv))
    # dedupe por end date (nos quedamos con el último por si se repite)
    dd = {}
    for d, v in out:
        dd[d] = v
    return sorted(dd.items(), key=lambda t: t[0])

def _pull_tag_points(facts, tag_name, preferred_units):
    """Extrae puntos de un tag us-gaap:tag_name"""
    try:
        tag_obj = facts[USGAAP][tag_name]
    except Exception:
        return []
    units = tag_obj.get("units") or {}
    return _select_points(units, preferred_units)

def _attach(packed, end_date, key, value):
    d = packed.setdefault(end_date, {})
    d[key] = value

# --------------------------------------------------------------------------------------
# Core ingest
# --------------------------------------------------------------------------------------
def ingest_company(company: Company, years: int = 10, sleep: float = 0.25, logger=print):
    # 1) Resolver CIK (lo persistimos si falta)
    cik = (company.cik or "").strip()
    if not cik:
        r = requests.get(SEC_TICKERMAP_URL, headers=_ua(), timeout=30)
        r.raise_for_status()
        mp = r.json()
        # estructura: {"0":{"cik_str":320193,"ticker":"AAPL","title":"Apple Inc."}, ...}
        target = None
        for obj in mp.values():
            if (obj.get("ticker") or "").upper() == company.ticker.upper():
                target = obj
                break
        if not target:
            raise CommandError(f"No encontré CIK para {company.ticker}")
        cik = str(target["cik_str"])
        company.cik = cik
        company.save(update_fields=["cik"])
        logger(f"  CIK guardado: {cik}")
        time.sleep(sleep)

    cik10 = _pad_cik(cik)
    url = SEC_FACTS_URL_TMPL.format(cik10=cik10)
    r = requests.get(url, headers=_ua(), timeout=60)
    r.raise_for_status()
    facts = r.json().get("facts") or {}

    cutoff = dt.date.today() - dt.timedelta(days=int(years) * 365)

    # Packed por fecha de fin: para IS y BS
    packed_is = {}  # end_date -> payload dict
    packed_bs = {}

    for mykey, tag_list in TAGS.items():
        preferred = PREFERRED_UNITS.get(mykey, set())
        points = []
        # buscamos el primer tag que tenga datos
        for tag in tag_list:
            pts = _pull_tag_points(facts, tag, preferred)
            if pts:
                points = pts
                break
        if not points:
            continue

        for end, val in points:
            if end < cutoff:
                continue
            # decidir si es IS (duration) o BS (instant)
            # Heurística: acciones y deudas son típicamente instantes (BS),
            # EPS/Revenue/NetIncome/EBITDA durations (IS)
            if mykey in {"CashAndCashEquivalents", "ShortTermDebt", "LongTermDebt", "CommonStockSharesOutstanding"}:
                _attach(packed_bs, end, mykey, val)
            else:
                _attach(packed_is, end, mykey, val)

    created, updated = 0, 0
    # Guardar IS trimestral
    with transaction.atomic():
        for end, payload in packed_is.items():
            obj, was_created = Statement.objects.update_or_create(
                company=company,
                statement_type="IS",
                period_type="Q",
                period_end=end,
                defaults={"json_payload": payload},
            )
            if not was_created:
                # merge: conservar campos previos si existen y agregar nuevos
                data = obj.json_payload or {}
                data.update(payload)
                obj.json_payload = data
                obj.save(update_fields=["json_payload"])
                updated += 1
            else:
                created += 1

        # Guardar BS trimestral (instant)
        for end, payload in packed_bs.items():
            obj, was_created = Statement.objects.update_or_create(
                company=company,
                statement_type="BS",
                period_type="Q",
                period_end=end,
                defaults={"json_payload": payload},
            )
            if not was_created:
                data = obj.json_payload or {}
                data.update(payload)
                obj.json_payload = data
                obj.save(update_fields=["json_payload"])
                updated += 1
            else:
                created += 1

    logger(f"  IS/BS guardados — nuevos: {created}, actualizados: {updated}")


# --------------------------------------------------------------------------------------
# Django command
# --------------------------------------------------------------------------------------
class Command(BaseCommand):
    help = "Ingiere estados financieros trimestrales (IS/BS) desde SEC CompanyFacts a 'Statement.json_payload'."

    def add_arguments(self, parser):
        parser.add_argument("--tickers", nargs="*", help="Limitar a ciertos tickers (AAPL MSFT ...)")
        parser.add_argument("--years", type=int, default=10, help="Años hacia atrás (default 10)")
        parser.add_argument("--sleep", type=float, default=0.25, help="Pausa entre requests (seg)")

    def handle(self, *args, **opts):
        tickers = [t.upper() for t in (opts.get("tickers") or [])]
        years = int(opts.get("years") or 10)
        sleep = float(opts.get("sleep") or 0.25)

        qs = Company.objects.all()
        if tickers:
            qs = qs.filter(ticker__in=tickers)

        if not qs.exists():
            raise CommandError("No hay compañías que procesar. Crea Company o usa --tickers.")

        self.stdout.write(self.style.NOTICE(f"Procesando {qs.count()} compañías (últimos {years} años)"))
        for c in qs:
            self.stdout.write(f"[{c.ticker}]")
            try:
                ingest_company(c, years=years, sleep=sleep, logger=self.stdout.write)
            except Exception as e:
                self.stderr.write(f"  error: {e}")
            time.sleep(sleep)  # cortesía
        self.stdout.write(self.style.SUCCESS("Ingesta completada."))
