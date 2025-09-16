from __future__ import annotations
from django.views.generic import ListView, View
from django.db.models import Q
from django.shortcuts import redirect
from .models import Company

class CompanyListView(ListView):
    model = Company
    template_name = "companies/list.html"
    context_object_name = "companies"
    paginate_by = 25

    def get_queryset(self):
        qs = Company.objects.all().order_by("ticker")
        q = (self.request.GET.get("q") or "").strip()
        sector = (self.request.GET.get("sector") or "").strip()
        if q:
            qs = qs.filter(
                Q(ticker__icontains=q) |
                Q(name__icontains=q)
            )
        if sector:
            qs = qs.filter(sector__iexact=sector)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["sector"] = self.request.GET.get("sector", "")
        ctx["sectors"] = (Company.objects
                          .exclude(sector__isnull=True)
                          .exclude(sector__exact="")
                          .values_list("sector", flat=True)
                          .distinct()
                          .order_by("sector"))
        return ctx

class CompanyDetailRedirect(View):
    """Redirige al dashboard por ticker que ya tienes en /stock/<ticker>/."""
    def get(self, request, ticker: str):
        return redirect("company-dashboard", ticker=ticker.upper())
