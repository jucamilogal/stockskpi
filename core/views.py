# core/views.py
from __future__ import annotations

from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

from companies.models import Company
from fundamentals.models import Metric
from marketdata.models import PriceBar


from django.core.cache import cache

class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        quick = cache.get("core:quick_stats")
        if not quick:
            last_bar = PriceBar.objects.order_by("-date").first()
            quick = {
                "companies_count": Company.objects.count(),
                "metrics_count": Metric.objects.count(),
                "last_price_date": getattr(last_bar, "date", None),
                "now": now(),
            }
            cache.set("core:quick_stats", quick, timeout=300)  # 5 min
        ctx["quick_stats"] = quick

        # (resto igual: ctx["sections"] = [...])
        ...
        return ctx

def dashboard(request):
    """
    Fallback del dashboard:
    - Si existe templates/core/dashboard.html lo renderiza.
    - Si no existe, redirige al Screener para no romper la navegación.
    """
    try:
        get_template("core/dashboard.html")
        return render(request, "core/dashboard.html", {})
    except TemplateDoesNotExist:
        return redirect("screener")
