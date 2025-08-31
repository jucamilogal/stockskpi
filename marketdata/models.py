from django.db import models
from companies.models import Company

class PriceBar(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE)
    date = models.DateField()
    open = models.FloatField(null=True, blank=True)
    high = models.FloatField(null=True, blank=True)
    low = models.FloatField(null=True, blank=True)
    close = models.FloatField(null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)

    class Meta:
        unique_together = [("company", "date")]
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["date"]),
        ]
