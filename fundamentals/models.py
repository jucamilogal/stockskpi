from django.db import models
from companies.models import Company

class Statement(models.Model):
    ST_TYPES = [("IS","Income"),("BS","Balance"),("CF","Cashflow")]
    PTYPES = [("Q","Quarter"),("Y","Year")]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=2, choices=ST_TYPES)
    period_end = models.DateField(db_index=True)
    period_type = models.CharField(max_length=1, choices=PTYPES)
    json_payload = models.JSONField()  # e.g. {"Revenue": 123, "NetIncome": 45}

class Metric(models.Model):
    PTYPES = [("Q","Quarter"),("TTM","TTM")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    key = models.CharField(max_length=64)
    period_end = models.DateField(db_index=True)
    period_type = models.CharField(max_length=4, choices=PTYPES)
    value = models.DecimalField(max_digits=20, decimal_places=6)

    class Meta:
        indexes = [models.Index(fields=["company","key","period_end"])]
