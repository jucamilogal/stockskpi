from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import dashboard, pe_view, screener_view
from api.views import LatestRankingViewSet, CompanyRevenueChart, CompanyPriceChart, MetricsLatestByTicker, PERanking, Screener

router = DefaultRouter()
router.register(r"rankings/latest", LatestRankingViewSet, basename="rankings-latest")

urlpatterns = [
    path("", dashboard),
    path("pe/", pe_view, name="pe"),
    path("screener/", screener_view, name="screener"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/", include(router.urls)),

    # charts
    path("api/charts/<str:ticker>/revenue/", CompanyRevenueChart.as_view(), name="company-revenue-chart"),
    path("api/charts/<str:ticker>/price/", CompanyPriceChart.as_view(), name="company-price-chart"),

    # metrics-by-ticker
    path("api/metrics/<str:ticker>/latest/", MetricsLatestByTicker.as_view(), name="metrics-latest-by-ticker"),
    
    # metrics & rankings
    path("api/metrics/<str:ticker>/latest/", MetricsLatestByTicker.as_view(), name="metrics-latest-by-ticker"),
    path("api/rankings/pe/", PERanking.as_view(), name="pe-ranking"),
    
    # NEW screener
    path("api/screener/", Screener.as_view(), name="screener"),
]
