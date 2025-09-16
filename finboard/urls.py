# finboard/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import dashboard  # tu dashboard actual (lo servimos en /dashboard/)
from charts.views import pe_plus_view, pe_view, screener_view, company_dashboard
from api.views import (
    LatestRankingViewSet,
    CompanyRevenueChart,
    CompanyPriceChart,
    MetricSeriesByTicker,
    MetricsLatestByTicker,
    PERanking,
    Screener,
)

router = DefaultRouter()
router.register(r"rankings/latest", LatestRankingViewSet, basename="rankings-latest")

urlpatterns = [
    # Admin & API Docs
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Home (hub) y dashboard
    path("", include("core.urls")),  # "/" -> HomeView (defínelo en core/urls.py)
    path("dashboard/", dashboard, name="dashboard"),
    path("companies/", include("companies.urls")),

    # Páginas HTML (charts)
    path("pe/", pe_view, name="pe"),
    path("pe+/", pe_plus_view, name="pe-plus"),
    path("screener/", screener_view, name="screener"),
    path("stock/<str:ticker>/", company_dashboard, name="company-dashboard"),

    # API (JSON)
    path("api/", include(router.urls)),
    path("api/charts/<str:ticker>/revenue/", CompanyRevenueChart.as_view(), name="company-revenue-chart"),
    path("api/charts/<str:ticker>/price/", CompanyPriceChart.as_view(), name="company-price-chart"),
    path("api/metrics/<str:ticker>/latest/", MetricsLatestByTicker.as_view(), name="metrics-latest-by-ticker"),
    path("api/rankings/pe/", PERanking.as_view(), name="pe-ranking"),
    path("api/screener/", Screener.as_view(), name="screener-api"),  # nombre distinto al HTML para evitar colisión
    path("api/metrics/<str:ticker>/series/", MetricSeriesByTicker.as_view(), name="metrics-series-by-ticker"),
]
