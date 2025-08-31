from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import MetricViewSet, export_metrics_csv, export_metrics_xlsx

router = DefaultRouter()
router.register(r"metrics", MetricViewSet, basename="metric")

urlpatterns = [
    path("", include(router.urls)),
    path("metrics/export.csv", export_metrics_csv,   name="metrics-export-csv"),
    path("metrics/export.xlsx", export_metrics_xlsx, name="metrics-export-xlsx"),
]
