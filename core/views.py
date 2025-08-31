# core/views.py
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from companies.models import Company

# TTLs de caché (segundos)
CACHE_DASHBOARD = 60 * 3  # 3 minutos; ajusta a gusto

@cache_page(CACHE_DASHBOARD)
def dashboard(request):
    """
    Vista principal del dashboard.
    Cacheada para evitar recalcular listados de compañías/sectores con frecuencia.
    La clave de caché incluye la URL completa (querystring).
    """
    qs = Company.objects.only("ticker", "sector", "name")

    tickers = list(qs.order_by("ticker").values_list("ticker", flat=True))
    sectors = list(qs.order_by("sector").values_list("sector", flat=True).distinct())

    default_ticker = request.GET.get("ticker") or (tickers[0] if tickers else "AAPL")

    context = {
        "tickers": tickers,
        "sectors": sectors,
        "default_ticker": default_ticker,
    }
    return render(request, "dashboard.html", context)
