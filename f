[1mdiff --git a/api/filters.py b/api/filters.py[m
[1mnew file mode 100644[m
[1mindex 0000000..f8e6d43[m
[1m--- /dev/null[m
[1m+++ b/api/filters.py[m
[36m@@ -0,0 +1,16 @@[m
[32m+[m[32mimport django_filters as df[m
[32m+[m[32mfrom fundamentals.models import Metric[m
[32m+[m
[32m+[m[32mclass MetricFilter(df.FilterSet):[m
[32m+[m[32m    # Campos “amigables”[m
[32m+[m[32m    ticker = df.CharFilter(field_name="company__ticker", lookup_expr="iexact")[m
[32m+[m[32m    sector = df.CharFilter(field_name="company__sector", lookup_expr="iexact")[m
[32m+[m[32m    key = df.CharFilter(field_name="key", lookup_expr="iexact")[m
[32m+[m
[32m+[m[32m    # Rangos y búsquedas[m
[32m+[m[32m    min_value = df.NumberFilter(field_name="value", lookup_expr="gte")[m
[32m+[m[32m    max_value = df.NumberFilter(field_name="value", lookup_expr="lte")[m
[32m+[m
[32m+[m[32m    class Meta:[m
[32m+[m[32m        model = Metric[m
[32m+[m[32m        fields = ["ticker", "sector", "key", "period_type"][m
[1mdiff --git a/api/serializers.py b/api/serializers.py[m
[1mindex b375ef0..fb10388 100644[m
[1m--- a/api/serializers.py[m
[1m+++ b/api/serializers.py[m
[36m@@ -1,3 +1,4 @@[m
[32m+[m[32m# EXISTENTE:[m
 from rankings.models import RankingResult[m
 from companies.models import Company[m
 from rest_framework import serializers[m
[36m@@ -12,3 +13,15 @@[m [mclass RankingResultSerializer(serializers.ModelSerializer):[m
     class Meta:[m
         model = RankingResult[m
         fields = ["company", "score", "rank", "snapshot_json"][m
[32m+[m
[32m+[m[32mfrom fundamentals.models import Metric[m
[32m+[m
[32m+[m[32mclass MetricSerializer(serializers.ModelSerializer):[m
[32m+[m[32m    ticker = serializers.CharField(source="company.ticker", read_only=True)[m
[32m+[m[32m    company_name = serializers.CharField(source="company.name", read_only=True)[m
[32m+[m[32m    sector = serializers.CharField(source="company.sector", read_only=True)[m
[32m+[m
[32m+[m[32m    class Meta:[m
[32m+[m[32m        model = Metric[m
[32m+[m[32m        fields = ["id", "ticker", "company_name", "sector", "key", "value", "period_end", "period_type"][m
[41m+[m
[1mdiff --git a/api/urls.py b/api/urls.py[m
[1mnew file mode 100644[m
[1mindex 0000000..466c885[m
[1m--- /dev/null[m
[1m+++ b/api/urls.py[m
[36m@@ -0,0 +1,13 @@[m
[32m+[m[32mfrom django.urls import path, include[m
[32m+[m[32mfrom rest_framework.routers import DefaultRouter[m
[32m+[m
[32m+[m[32mfrom api.views import MetricViewSet, export_metrics_csv, export_metrics_xlsx[m
[32m+[m
[32m+[m[32mrouter = DefaultRouter()[m
[32m+[m[32mrouter.register(r"metrics", MetricViewSet, basename="metric")[m
[32m+[m
[32m+[m[32murlpatterns = [[m
[32m+[m[32m    path("", include(router.urls)),[m
[32m+[m[32m    path("metrics/export.csv", export_metrics_csv,   name="metrics-export-csv"),[m
[32m+[m[32m    path("metrics/export.xlsx", export_metrics_xlsx, name="metrics-export-xlsx"),[m
[32m+[m[32m][m
[1mdiff --git a/api/views.py b/api/views.py[m
[1mindex ba56bab..a2fb6e8 100644[m
[1m--- a/api/views.py[m
[1m+++ b/api/views.py[m
[36m@@ -1,4 +1,7 @@[m
 from django.http import HttpResponse[m
[32m+[m[32mfrom rest_framework import viewsets, mixins[m
[32m+[m[32mfrom rest_framework.decorators import api_view, permission_classes[m
[32m+[m[32mfrom rest_framework.permissions import AllowAny[m
 from rest_framework.viewsets import ReadOnlyModelViewSet[m
 from rankings.models import Ranking, RankingResult[m
 from .serializers import RankingResultSerializer[m
[36m@@ -11,8 +14,12 @@[m [mfrom django.utils.decorators import method_decorator[m
 from django.views.decorators.cache import cache_page[m
 import csv, math[m
 [m
[32m+[m[32mimport pandas as pd[m
[32m+[m
 from companies.models import Company[m
 from fundamentals.models import Metric[m
[32m+[m[32mfrom api.serializers import MetricSerializer[m
[32m+[m[32mfrom api.filters import MetricFilter[m
 [m
 class LatestRankingViewSet(ReadOnlyModelViewSet):[m
     serializer_class = RankingResultSerializer[m
[36m@@ -336,4 +343,60 @@[m [mclass Screener(APIView):[m
             return resp[m
 [m
         # JSON response[m
[31m-        return Response([{k: r.get(k) for k in fields} for r in rows])[m
\ No newline at end of file[m
[32m+[m[32m        return Response([{k: r.get(k) for k in fields} for r in rows])[m
[32m+[m[41m    [m
[32m+[m[32m    # --- API REST: listado/consulta de métricas con filtros/ordenación ---[m
[32m+[m[32m@method_decorator(cache_page(60), name="dispatch")  # cache 60s[m
[32m+[m[32mclass MetricViewSet(mixins.ListModelMixin,[m
[32m+[m[32m                    mixins.RetrieveModelMixin,[m
[32m+[m[32m                    viewsets.GenericViewSet):[m
[32m+[m[32m    queryset = ([m
[32m+[m[32m        Metric.objects[m
[32m+[m[32m        .select_related("company")[m
[32m+[m[32m        .only("id", "key", "value", "period_end", "period_type",[m
[32m+[m[32m              "company__ticker", "company__name", "company__sector")[m
[32m+[m[32m    )[m
[32m+[m[32m    serializer_class = MetricSerializer[m
[32m+[m[32m    filterset_class = MetricFilter[m
[32m+[m[32m    permission_classes = [AllowAny][m
[32m+[m[32m    ordering_fields = ["value", "period_end", "company__ticker", "company__name", "company__sector"][m
[32m+[m[32m    search_fields = ["company__ticker", "company__name"][m
[32m+[m
[32m+[m[32m# --- Export: CSV y XLSX aplicando LOS MISMOS filtros ---[m
[32m+[m[32mdef _filtered_metrics_queryset(request):[m
[32m+[m[32m    qs = MetricViewSet.queryset[m
[32m+[m[32m    f = MetricFilter(request.GET, queryset=qs)[m
[32m+[m[32m    return f.qs[m
[32m+[m
[32m+[m[32m@cache_page(60)[m
[32m+[m[32m@api_view(["GET"])[m
[32m+[m[32m@permission_classes([AllowAny])[m
[32m+[m[32mdef export_metrics_csv(request):[m
[32m+[m[32m    qs = _filtered_metrics_queryset(request)[m
[32m+[m[32m    rows = qs.values([m
[32m+[m[32m        "company__ticker", "company__name", "company__sector",[m
[32m+[m[32m        "key", "value", "period_end", "period_type"[m
[32m+[m[32m    )[m
[32m+[m[32m    df = pd.DataFrame(rows)[m
[32m+[m[32m    resp = HttpResponse(content_type="text/csv")[m
[32m+[m[32m    resp["Content-Disposition"] = 'attachment; filename="metrics.csv"'[m
[32m+[m[32m    df.to_csv(resp, index=False)[m
[32m+[m[32m    return resp[m
[32m+[m
[32m+[m[32m@cache_page(60)[m
[32m+[m[32m@api_view(["GET"])[m
[32m+[m[32m@permission_classes([AllowAny])[m
[32m+[m[32mdef export_metrics_xlsx(request):[m
[32m+[m[32m    qs = _filtered_metrics_queryset(request)[m
[32m+[m[32m    rows = qs.values([m
[32m+[m[32m        "company__ticker", "company__name", "company__sector",[m
[32m+[m[32m        "key", "value", "period_end", "period_type"[m
[32m+[m[32m    )[m
[32m+[m[32m    df = pd.DataFrame(rows)[m
[32m+[m[32m    resp = HttpResponse([m
[32m+[m[32m        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"[m
[32m+[m[32m    )[m
[32m+[m[32m    resp["Content-Disposition"] = 'attachment; filename="metrics.xlsx"'[m
[32m+[m[32m    with pd.ExcelWriter(resp, engine="xlsxwriter") as xw:[m
[32m+[m[32m        df.to_excel(xw, index=False, sheet_name="metrics")[m
[32m+[m[32m    return resp[m
\ No newline at end of file[m
[1mdiff --git a/charts/views.py b/charts/views.py[m
[1mindex 91ea44a..71a4d88 100644[m
[1m--- a/charts/views.py[m
[1m+++ b/charts/views.py[m
[36m@@ -1,3 +1,211 @@[m
[32m+[m[32m# charts/views.py[m
[32m+[m[32mfrom __future__ import annotations[m
[32m+[m
[32m+[m[32mimport csv[m
[32m+[m[32mfrom typing import Dict, List[m
[32m+[m
[32m+[m[32mfrom django.http import HttpResponse[m
 from django.shortcuts import render[m
[32m+[m[32mfrom django.views.decorators.cache import cache_page[m
[32m+[m
[32m+[m[32mfrom companies.models import Company[m
[32m+[m[32mfrom fundamentals.models import Metric[m
[32m+[m
[32m+[m
[32m+[m[32m# -----------------------------[m
[32m+[m[32m# Utilidades[m
[32m+[m[32m# -----------------------------[m
[32m+[m[32mdef _safe_float(x):[m
[32m+[m[32m    try:[m
[32m+[m[32m        return float(x)[m
[32m+[m[32m    except (TypeError, ValueError):[m
[32m+[m[32m        return None[m
[32m+[m
[32m+[m
[32m+[m[32mdef _latest_metric_map(key: str) -> Dict[int, float]:[m
[32m+[m[32m    """[m
[32m+[m[32m    Devuelve {company_id: ultimo_valor} para la métrica 'key'[m
[32m+[m[32m    tomando el registro más reciente por compañía.[m
[32m+[m[32m    """[m
[32m+[m[32m    qs = ([m
[32m+[m[32m        Metric.objects.filter(key=key)[m
[32m+[m[32m        .order_by("company_id", "-period_end", "-id")[m
[32m+[m[32m        .values("company_id", "value")[m
[32m+[m[32m    )[m
[32m+[m[32m    out, seen = {}, set()[m
[32m+[m[32m    for row in qs:[m
[32m+[m[32m        cid = row["company_id"][m
[32m+[m[32m        if cid in seen:[m
[32m+[m[32m            continue[m
[32m+[m[32m        out[cid] = _safe_float(row["value"])[m
[32m+[m[32m        seen.add(cid)[m
[32m+[m[32m    return out[m
[32m+[m
[32m+[m
[32m+[m[32mdef _csv_response(filename: str, rows: List[dict], headers: List[str], keys: List[str]) -> HttpResponse:[m
[32m+[m[32m    resp = HttpResponse(content_type="text/csv; charset=utf-8")[m
[32m+[m[32m    resp["Content-Disposition"] = f'attachment; filename="{filename}"'[m
[32m+[m[32m    w = csv.writer(resp)[m
[32m+[m[32m    w.writerow(headers)[m
[32m+[m[32m    for r in rows:[m
[32m+[m[32m        w.writerow([r.get(k, "") for k in keys])[m
[32m+[m[32m    return resp[m
[32m+[m
[32m+[m
[32m+[m[32m# -----------------------------[m
[32m+[m[32m# Screener[m
[32m+[m[32m# -----------------------------[m
[32m+[m[32m@cache_page(60)  # 1 minuto de caché (ajusta o elimina durante desarrollo)[m
[32m+[m[32mdef screener_view(request):[m
[32m+[m[32m    sector_q = (request.GET.get("sector") or "").strip()[m
[32m+[m[32m    min_mcap_q = _safe_float((request.GET.get("min_mcap") or "").strip())[m
[32m+[m[32m    order_q = (request.GET.get("order") or "pe_asc").strip()[m
[32m+[m[32m    limit_q = int(request.GET.get("limit") or 100)[m
[32m+[m[32m    fmt_q = (request.GET.get("format") or "").lower()[m
[32m+[m
[32m+[m[32m    # Trae mapas de métricas "último valor por compañía"[m
[32m+[m[32m    maps = {[m
[32m+[m[32m        "PE_TTM": _latest_metric_map("PE_TTM"),[m
[32m+[m[32m        "EV_EBITDA": _latest_metric_map("EV_EBITDA"),[m
[32m+[m[32m        "EV_Sales": _latest_metric_map("EV_Sales"),[m
[32m+[m[32m        "FCF_Yield": _latest_metric_map("FCF_Yield"),[m
[32m+[m[32m        "NetMargin_TTM": _latest_metric_map("NetMargin_TTM"),[m
[32m+[m[32m        "MarketCap": _latest_metric_map("MarketCap"),[m
[32m+[m[32m        "RSI_14": _latest_metric_map("RSI_14"),[m
[32m+[m[32m        "Revenue_YoY": _latest_metric_map("Revenue_YoY"),[m
[32m+[m[32m    }[m
[32m+[m
[32m+[m[32m    # Compañías base (opcionalmente filtradas por sector)[m
[32m+[m[32m    companies = Company.objects.only("id", "ticker", "name", "sector", "currency")[m
[32m+[m[32m    if sector_q:[m
[32m+[m[32m        companies = companies.filter(sector__iexact=sector_q)[m
[32m+[m
[32m+[m[32m    rows = [][m
[32m+[m[32m    for c in companies:[m
[32m+[m[32m        mcap = maps["MarketCap"].get(c.id)[m
[32m+[m
[32m+[m[32m        # Filtro de market cap mínimo[m
[32m+[m[32m        if min_mcap_q is not None and (mcap is None or mcap < min_mcap_q):[m
[32m+[m[32m            continue[m
[32m+[m
[32m+[m[32m        rows.append([m
[32m+[m[32m            {[m
[32m+[m[32m                "ticker": c.ticker,[m
[32m+[m[32m                "name": c.name,[m
[32m+[m[32m                "sector": c.sector,[m
[32m+[m[32m                "currency": c.currency,[m
[32m+[m[32m                "marketcap": mcap,[m
[32m+[m[32m                "pe_ttm": maps["PE_TTM"].get(c.id),[m
[32m+[m[32m                "ev_sales": maps["EV_Sales"].get(c.id),[m
[32m+[m[32m                "ev_ebitda": maps["EV_EBITDA"].get(c.id),[m
[32m+[m[32m                "fcf_yield": maps["FCF_Yield"].get(c.id),[m
[32m+[m[32m                "rev_yoy": maps["Revenue_YoY"].get(c.id),[m
[32m+[m[32m                "rsi14": maps["RSI_14"].get(c.id),[m
[32m+[m[32m            }[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    # Ordenamiento[m
[32m+[m[32m    # order= pe_asc | pe_desc | evs_asc | evs_desc | yoy_desc | yoy_asc | rsi_asc | rsi_desc | mcap_desc | mcap_asc[m
[32m+[m[32m    order_map = {[m
[32m+[m[32m        "pe_asc": ("pe_ttm", False),[m
[32m+[m[32m        "pe_desc": ("pe_ttm", True),[m
[32m+[m[32m        "evs_asc": ("ev_sales", False),[m
[32m+[m[32m        "evs_desc": ("ev_sales", True),[m
[32m+[m[32m        "yoy_desc": ("rev_yoy", True),[m
[32m+[m[32m        "yoy_asc": ("rev_yoy", False),[m
[32m+[m[32m        "rsi_asc": ("rsi14", False),[m
[32m+[m[32m        "rsi_desc": ("rsi14", True),[m
[32m+[m[32m        "mcap_desc": ("marketcap", True),[m
[32m+[m[32m        "mcap_asc": ("marketcap", False),[m
[32m+[m[32m    }[m
[32m+[m[32m    sort_key, reverse = order_map.get(order_q, ("pe_ttm", False))[m
[32m+[m
[32m+[m[32m    def _key(r):[m
[32m+[m[32m        v = r.get(sort_key)[m
[32m+[m[32m        # Forzamos que None quede al final[m
[32m+[m[32m        return (v is None, v)[m
[32m+[m
[32m+[m[32m    rows.sort(key=_key, reverse=reverse)[m
[32m+[m
[32m+[m[32m    # Límite[m
[32m+[m[32m    rows = rows[: max(1, min(limit_q, 1000))][m
[32m+[m
[32m+[m[32m    # CSV si se pide ?format=csv[m
[32m+[m[32m    if fmt_q == "csv":[m
[32m+[m[32m        headers = [[m
[32m+[m[32m            "Ticker",[m
[32m+[m[32m            "Name",[m
[32m+[m[32m            "Sector",[m
[32m+[m[32m            "MarketCap",[m
[32m+[m[32m            "P/E (TTM)",[m
[32m+[m[32m            "EV/Sales",[m
[32m+[m[32m            "EV/EBITDA",[m
[32m+[m[32m            "FCF Yield",[m
[32m+[m[32m            "Revenue YoY",[m
[32m+[m[32m            "RSI 14",[m
[32m+[m[32m        ][m
[32m+[m[32m        keys = ["ticker", "name", "sector", "marketcap", "pe_ttm", "ev_sales", "ev_ebitda", "fcf_yield", "rev_yoy", "rsi14"][m
[32m+[m[32m        return _csv_response("screener.csv", rows, headers, keys)[m
[32m+[m
[32m+[m[32m    context = {[m
[32m+[m[32m        "rows": rows,[m
[32m+[m[32m        "selected_sector": sector_q,[m
[32m+[m[32m        "min_mcap": "" if min_mcap_q is None else min_mcap_q,[m
[32m+[m[32m        "order": order_q,[m
[32m+[m[32m        "limit": limit_q,[m
[32m+[m[32m        "sectors": Company.objects.order_by("sector")[m
[32m+[m[32m        .values_list("sector", flat=True)[m
[32m+[m[32m        .distinct(),[m
[32m+[m[32m    }[m
[32m+[m[32m    return render(request, "screener.html", context)[m
[32m+[m
[32m+[m
[32m+[m[32m# -----------------------------[m
[32m+[m[32m# Ranking P/E[m
[32m+[m[32m# -----------------------------[m
[32m+[m[32m@cache_page(60 * 5)  # 5 minutos[m
[32m+[m[32mdef pe_view(request):[m
[32m+[m[32m    """Ranking por P/E (más bajo primero)."""[m
[32m+[m[32m    sector_q = (request.GET.get("sector") or "").strip()[m
[32m+[m[32m    min_mcap_q = _safe_float((request.GET.get("min_mcap") or "").strip())[m
[32m+[m
[32m+[m[32m    pe_map = _latest_metric_map("PE_TTM")[m
[32m+[m[32m    mcap_map = _latest_metric_map("MarketCap")[m
[32m+[m
[32m+[m[32m    companies = Company.objects.only("id", "ticker", "name", "sector")[m
[32m+[m[32m    if sector_q:[m
[32m+[m[32m        companies = companies.filter(sector__iexact=sector_q)[m
[32m+[m
[32m+[m[32m    rows = [][m
[32m+[m[32m    for c in companies:[m
[32m+[m[32m        pe = pe_map.get(c.id)[m
[32m+[m[32m        mcap = mcap_map.get(c.id)[m
[32m+[m
[32m+[m[32m        if min_mcap_q is not None and (mcap is None or mcap < min_mcap_q):[m
[32m+[m[32m            continue[m
[32m+[m
[32m+[m[32m        rows.append([m
[32m+[m[32m            {[m
[32m+[m[32m                "ticker": c.ticker,[m
[32m+[m[32m                "name": c.name,[m
[32m+[m[32m                "sector": c.sector,[m
[32m+[m[32m                "marketcap": mcap,[m
[32m+[m[32m                "pe_ttm": pe,[m
[32m+[m[32m            }[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    rows.sort(key=lambda r: (r["pe_ttm"] is None, r["pe_ttm"] if r["pe_ttm"] is not None else float("inf")))[m
[32m+[m[32m    rows = rows[:200][m
 [m
[31m-# Create your views here.[m
[32m+[m[32m    return render([m
[32m+[m[32m        request,[m
[32m+[m[32m        "pe.html",[m
[32m+[m[32m        {[m
[32m+[m[32m            "rows": rows,[m
[32m+[m[32m            "selected_sector": sector_q,[m
[32m+[m[32m            "min_mcap": "" if min_mcap_q is None else min_mcap_q,[m
[32m+[m[32m            "sectors": Company.objects.order_by("sector")[m
[32m+[m[32m            .values_list("sector", flat=True)[m
[32m+[m[32m            .distinct(),[m
[32m+[m[32m        },[m
[32m+[m[32m    )[m
[1mdiff --git a/core/management/__init__.py b/core/management/__init__.py[m
[1mnew file mode 100644[m
[1mindex 0000000..e69de29[m
[1mdiff --git a/core/management/commands/__init__.py b/core/management/commands/__init__.py[m
[1mnew file mode 100644[m
[1mindex 0000000..e69de29[m
[1mdiff --git a/core/management/commands/clear_cache.py b/core/management/commands/clear_cache.py[m
[1mnew file mode 100644[m
[1mindex 0000000..2531029[m
[1m--- /dev/null[m
[1m+++ b/core/management/commands/clear_cache.py[m
[36m@@ -0,0 +1,28 @@[m
[32m+[m[32mfrom django.core.management.base import BaseCommand[m
[32m+[m[32mfrom django.core.cache import cache, caches[m
[32m+[m[32mfrom django.conf import settings[m
[32m+[m
[32m+[m[32mclass Command(BaseCommand):[m
[32m+[m[32m    help = "Limpia el caché de Django. Por defecto limpia el 'default'. Usa --all para limpiar todos los alias definidos en CACHES."[m
[32m+[m
[32m+[m[32m    def add_arguments(self, parser):[m
[32m+[m[32m        parser.add_argument([m
[32m+[m[32m            "--all",[m
[32m+[m[32m            action="store_true",[m
[32m+[m[32m            help="Limpia todos los alias de caché definidos en settings.CACHES",[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    def handle(self, *args, **options):[m
[32m+[m[32m        cleared = [][m
[32m+[m
[32m+[m[32m        if options.get("all"):[m
[32m+[m[32m            # Limpiar todos los alias definidos en settings.CACHES[m
[32m+[m[32m            for alias in getattr(settings, "CACHES", {}).keys():[m
[32m+[m[32m                caches[alias].clear()[m
[32m+[m[32m                cleared.append(alias)[m
[32m+[m[32m        else:[m
[32m+[m[32m            # Limpiar solo el alias 'default'[m
[32m+[m[32m            cache.clear()[m
[32m+[m[32m            cleared.append("default")[m
[32m+[m
[32m+[m[32m        self.stdout.write(self.style.SUCCESS(f"Caché limpiado: {', '.join(cleared)}"))[m
\ No newline at end of file[m
[1mdiff --git a/core/views.py b/core/views.py[m
[1mindex 089647e..4cfbe6b 100644[m
[1m--- a/core/views.py[m
[1m+++ b/core/views.py[m
[36m@@ -1,12 +1,28 @@[m
[32m+[m[32m# core/views.py[m
 from django.shortcuts import render[m
[32m+[m[32mfrom django.views.decorators.cache import cache_page[m
 from companies.models import Company[m
 [m
[32m+[m[32m# TTLs de caché (segundos)[m
[32m+[m[32mCACHE_DASHBOARD = 60 * 3  # 3 minutos; ajusta a gusto[m
[32m+[m
[32m+[m[32m@cache_page(CACHE_DASHBOARD)[m
 def dashboard(request):[m
[31m-    tickers = list(Company.objects.order_by("ticker").values_list("ticker", flat=True))[m
[31m-    return render(request, "dashboard.html", {"tickers": tickers})[m
[32m+[m[32m    """