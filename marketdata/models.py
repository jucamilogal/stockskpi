from django.db import models
from companies.models import Company

class PriceBar(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    date = models.DateField(db_index=True)
    open = models.DecimalField(max_digits=16, decimal_places=6)
    high = models.DecimalField(max_digits=16, decimal_places=6)
    low  = models.DecimalField(max_digits=16, decimal_places=6)
    close= models.DecimalField(max_digits=16, decimal_places=6)
    volume = models.BigIntegerField()

    class Meta:
        unique_together = ("company","date")
        indexes = [models.Index(fields=["company","date"])]
