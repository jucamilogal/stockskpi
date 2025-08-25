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
