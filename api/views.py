# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from fundamentals.models import Metric

PERIOD_MAP = {"annual": "A", "a": "A", "A": "A", "quarter": "Q", "q": "Q", "Q": "Q"}

class MetricSeriesByTicker(APIView):
    """
    Devuelve la serie histórica de un metric key para un ticker.
    GET /api/metrics/<ticker>/series/?key=ebitda&period=annual
    """
    def get(self, request, ticker: str):
        key = request.GET.get("key")
        if not key:
            return Response({"detail": "param 'key' is required"}, status=status.HTTP_400_BAD_REQUEST)

        period = request.GET.get("period")
        if period:
            period = PERIOD_MAP.get(period, period)

        qs = Metric.objects.filter(
            company__ticker__iexact=ticker,
            key__iexact=key,
        )
        if period in ("A", "Q"):
            qs = qs.filter(period=period)

        # Ajusta el campo de fecha si en tu modelo no es 'as_of'
        qs = qs.order_by("as_of")

        data = [{"date": m.as_of, "value": float(m.value)} for m in qs]
        return Response({
            "ticker": ticker.upper(),
            "key": key.lower(),
            "period": period or "all",
            "count": len(data),
            "series": data,
        })
