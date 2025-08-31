# EXISTENTE:
from rankings.models import RankingResult
from companies.models import Company
from rest_framework import serializers

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["ticker", "name", "sector", "currency"]

class RankingResultSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    class Meta:
        model = RankingResult
        fields = ["company", "score", "rank", "snapshot_json"]

from fundamentals.models import Metric

class MetricSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(source="company.ticker", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    sector = serializers.CharField(source="company.sector", read_only=True)

    class Meta:
        model = Metric
        fields = ["id", "ticker", "company_name", "sector", "key", "value", "period_end", "period_type"]

