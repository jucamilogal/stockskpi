# fundamentals/management/commands/recompute_metrics.py
"""
Recalcula series TTM HISTÓRICAS por trimestre para cada compañía:

  - Revenue_TTM, NetIncome_TTM, EBITDA_TTM, Revenue_YoY
  - EPS_TTM (si hay acciones), PE_TTM
  - EV_Sales, EV_EBITDA

Usa:
  - IS (Q): Revenue, NetIncome, EBITDA; fallback EBITDA≈OperatingIncome+Dep&Amort.
  - BS (Q): Cash, Short/Long Debt, CommonStockSharesOutstanding.
  - IS (Q): WeightedAverageShsOutDil (acciones promedio diluidas) si existe.
  - PriceBar (D): precio más cercano en o antes de la fecha del trimestre.

Comandos:
  python manage.py recompute_metrics --tickers AAPL MSFT --verbose
"""

from decimal import Decimal
from typing import List, Tuple, Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import Company
from fundamentals.models import Statement, Metric
from marketdata.models import PriceBar


# -----------------------------
# Utilidades
# -----------------------------
def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def _series_is(company: Company, key_candidates, limit: int = 40) -> List[Tuple]:
    """
    Serie IS trimestral ascendente [(period_end, value), ...]
    key_candidates: str o lista de claves posibles dentro de json_payload.
    """
    if isinstance(key_candidates, str):
        key_candidates = [key_candidates]
    qs = (
        Statement.objects.filter(
            company=company, statement_type="IS", period_type="Q"
        )
        .only("period_end", "json_payload")
        .order_by("-period_end")[: max(8, limit)]
    )
    out = []
    for s in qs:
        payload = s.json_payload or {}
        val = None
        for k in key_candidates:
            val = _num(payload.get(k))
            if val is not None:
                break
        if val is not None:
            out.append((s.period_end, val))
    return list(reversed(out))  # asc


def _series_bs(company: Company, key_candidates, limit: int = 40) -> List[Tuple]:
    """
    Serie BS trimestral (instantes) ascendente [(period_end, value), ...]
    """
    if isinstance(key_candidates, str):
        key_candidates = [key_candidates]
    qs = (
        Statement.objects.filter(
            company=company, statement_type="BS", period_type="Q"
        )
        .only("period_end", "json_payload")
        .order_by("-period_end")[: max(8, limit)]
    )
    out = []
    for s in qs:
        payload = s.json_payload or {}
        val = None
        for k in key_candidates:
            val = _num(payload.get(k))
            if val is not None:
                break
        if val is not None:
            out.append((s.period_end, val))
    return list(reversed(out))


def _nearest_prior(series: List[Tuple], when) -> Optional[float]:
    """Último valor con fecha <= when en una serie ascendente."""
    val = None
    for d, v in series:
        if d <= when:
            val = v
        else:
            break
    return val


def _price_on_or_prior(company: Company, when):
    """(date, price) del último PriceBar con fecha <= when."""
    b = (
        PriceBar.objects.filter(company=company, date__lte=when)
        .only("date", "close")
        .order_by("-date")
        .first()
    )
    if not b:
        return None, None
    try:
        return b.date, float(b.close)
    except Exception:
        return None, None


def _ttm_at(series: List[Tuple], idx: int) -> Optional[float]:
    """Suma TTM (últimos 4) en el índice idx de una serie ascendente."""
    if idx < 3:
        return None
    vals = [series[i][1] for i in range(idx - 3, idx + 1)]
    if any(v is None for v in vals):
        return None
    return float(sum(vals))


def _save_upsert(company: Company, key: str, value, period_end, period_type="TTM"):
    """Upsert por (company, key, period_end, period_type)."""
    if value is None or period_end is None:
        return
    Metric.objects.update_or_create(
        company=company,
        key=key,
        period_end=period_end,
        period_type=period_type,
        defaults={"value": Decimal(str(value))},
    )


# -----------------------------
# Cálculo por compañía (histórico)
# -----------------------------
def recompute_historical(company: Company, verbose: bool = False):
    """
    Calcula y PERSISTE series TTM históricas por trimestre:
      Revenue_TTM, NetIncome_TTM, EBITDA_TTM, Revenue_YoY,
      EPS_TTM, PE_TTM, EV_Sales, EV_EBITDA.
    """

    # ----- Income Statement (durations, trimestrales)
    rev_q = _series_is(company, ["Revenue", "TotalRevenue", "Revenues"])
    ni_q = _series_is(company, ["NetIncome", "NetIncomeLoss", "ProfitLoss"])

    # EBITDA directo si existe:
    ebd_q = _series_is(company, ["EBITDA", "Ebitda"])

    # Fallback robusto: EBITDA ≈ OperatingIncome + Depreciation&Amortization
    if not ebd_q or len(ebd_q) < 4:
        op_q = _series_is(company, ["OperatingIncome", "OperatingIncomeLoss"])
        da_q = _series_is(
            company,
            [
                "DepreciationAndAmortization",
                "DepreciationDepletionAndAmortization",
                "DepreciationAmortizationAndAccretionNet",
            ],
        )
        if op_q or da_q:
            op_map = dict(op_q)
            da_map = dict(da_q)
            dates = sorted({d for d, _ in op_q} | {d for d, _ in da_q})
            ebd_q = []
            for d in dates:
                o = op_map.get(d)
                a = da_map.get(d)
                if o is None and a is None:
                    continue
                ebd_q.append((d, (o or 0.0) + (a or 0.0)))

    # Diluted EPS series (opcional; la usamos para EPS_TTM si hay shares)
    eps_q = _series_is(
        company,
        [
            "EPS",
            "DilutedEPS",
            "EPS_Diluted",
            "EarningsPerShareDiluted",
            "EarningsPerShareBasicAndDiluted",
            "BasicEPS",
            "EPS_Basic",
        ],
    )

    # ----- Balance Sheet (instantes, trimestrales)
    cash_q = _series_bs(
        company,
        [
            "CashAndCashEquivalents",
            "CashAndShortTermInvestments",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ],
    )
    debt_s_q = _series_bs(
        company,
        ["ShortTermDebt", "DebtCurrent", "ShortTermBorrowings", "CurrentDebt"],
    )
    debt_l_q = _series_bs(
        company, ["LongTermDebt", "LongTermDebtNoncurrent", "LongTermBorrowings"]
    )
    shrs_q = _series_bs(company, ["CommonStockSharesOutstanding"])
    # (durations) promedio diluido trimestral
    shrs_dil_q = _series_is(
        company,
        [
            "WeightedAverageShsOutDil",
            "WeightedAverageNumberOfDilutedSharesOutstanding",
            "WeightedAverageNumberOfSharesOutstandingDiluted",
        ],
    )

    if not rev_q:
        if verbose:
            print(f"  {company.ticker}: sin Revenue en IS; omito.")
        return

    with transaction.atomic():
        for idx in range(len(rev_q)):
            date_q = rev_q[idx][0]

            # TTM básicos
            rev_ttm = _ttm_at(rev_q, idx)
            ni_ttm = _ttm_at(ni_q, idx) if ni_q else None
            ebd_ttm = _ttm_at(ebd_q, idx) if ebd_q else None

            # YoY TTM (usando Revenue)
            yoy = None
            if idx >= 7:
                curr4 = sum([rev_q[i][1] for i in range(idx - 3, idx + 1)])
                prev4 = sum([rev_q[i][1] for i in range(idx - 7, idx - 3)])
                if prev4:
                    yoy = (curr4 / prev4) - 1.0

            # Precio y Acciones
            _, price = _price_on_or_prior(company, date_q)
            shares = _nearest_prior(shrs_dil_q, date_q) or _nearest_prior(
                shrs_q, date_q
            )

            # EPS TTM (si hay NI_TTM y acciones)
            eps_ttm = None
            if ni_ttm is not None and shares:
                eps_ttm = ni_ttm / shares

            # Market Cap & EV
            mcap = price * shares if (price and shares) else None
            cash = _nearest_prior(cash_q, date_q) or 0.0
            debt = ( _nearest_prior(debt_s_q, date_q) or 0.0 ) + (
                _nearest_prior(debt_l_q, date_q) or 0.0
            )
            ev = (mcap or 0.0) + debt - cash

            # Ratios
            pe_ttm = (price / eps_ttm) if price and eps_ttm not in (None, 0) else None
            ev_sales = (ev / rev_ttm) if rev_ttm not in (None, 0) else None
            ev_ebitda = (ev / ebd_ttm) if ebd_ttm not in (None, 0) else None

            # Persistencia (una fila por trimestre)
            if rev_ttm is not None:
                _save_upsert(company, "Revenue_TTM", rev_ttm, date_q, "TTM")
            if ni_ttm is not None:
                _save_upsert(company, "NetIncome_TTM", ni_ttm, date_q, "TTM")
            if ebd_ttm is not None:
                _save_upsert(company, "EBITDA_TTM", ebd_ttm, date_q, "TTM")
            if yoy is not None:
                _save_upsert(company, "Revenue_YoY", yoy, date_q, "TTM")
            if eps_ttm is not None:
                _save_upsert(company, "EPS_TTM", eps_ttm, date_q, "TTM")
            if pe_ttm is not None:
                _save_upsert(company, "PE_TTM", pe_ttm, date_q, "TTM")
            if ev_sales is not None:
                _save_upsert(company, "EV_Sales", ev_sales, date_q, "TTM")
            if ev_ebitda is not None:
                _save_upsert(company, "EV_EBITDA", ev_ebitda, date_q, "TTM")

    # Extras diarios (último precio y marketcap) – útil para otras vistas
    b = (
        PriceBar.objects.filter(company=company)
        .only("date", "close")
        .order_by("-date")
        .first()
    )
    if b:
        try:
            price_last = float(b.close)
            Metric.objects.update_or_create(
                company=company,
                key="Price",
                period_end=b.date,
                period_type="D",
                defaults={"value": Decimal(str(price_last))},
            )
            # MarketCap diario con acciones más recientes disponibles
            shares_last = (shrs_dil_q[-1][1] if shrs_dil_q else None) or (
                shrs_q[-1][1] if shrs_q else None
            )
            if shares_last:
                mcap_last = price_last * shares_last
                Metric.objects.update_or_create(
                    company=company,
                    key="MarketCap",
                    period_end=b.date,
                    period_type="D",
                    defaults={"value": Decimal(str(mcap_last))},
                )
        except Exception:
            pass


# -----------------------------
# Django command
# -----------------------------
class Command(BaseCommand):
    help = "Recalcula series TTM HISTÓRICAS por trimestre (P/E, EV/Sales, EV/EBITDA, Revenue/NI/EBITDA/EPS TTM, YoY)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tickers", nargs="*", help="Limitar a ciertos tickers (ej. AAPL MSFT)"
        )
        parser.add_argument("--verbose", action="store_true", help="Log detallado")

    def handle(self, *args, **opts):
        qs = Company.objects.all()
        if opts.get("tickers"):
            qs = qs.filter(ticker__in=[t.upper() for t in opts["tickers"]])

        for c in qs:
            if opts["verbose"]:
                self.stdout.write(f"→ {c.ticker}: recomputando histórico TTM ...")
            try:
                recompute_historical(c, verbose=opts["verbose"])
            except Exception as e:
                self.stderr.write(f"  {c.ticker}: error {e}")

        self.stdout.write(self.style.SUCCESS("Recompute histórico TTM completo."))
