import django_filters as df
from fundamentals.models import Metric

class MetricFilter(df.FilterSet):
    # Campos “amigables”
    ticker = df.CharFilter(field_name="company__ticker", lookup_expr="iexact")
    sector = df.CharFilter(field_name="company__sector", lookup_expr="iexact")
    key = df.CharFilter(field_name="key", lookup_expr="iexact")

    # Rangos y búsquedas
    min_value = df.NumberFilter(field_name="value", lookup_expr="gte")
    max_value = df.NumberFilter(field_name="value", lookup_expr="lte")

    class Meta:
        model = Metric
        fields = ["ticker", "sector", "key", "period_type"]
