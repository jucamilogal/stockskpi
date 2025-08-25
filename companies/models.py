from django.db import models

class Company(models.Model):
    ticker = models.CharField(max_length=10, unique=True)
    cik = models.CharField(max_length=20, blank=True, null=True)
    name = models.CharField(max_length=200)
    sector = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, default="USD")

    def __str__(self):
        return f"{self.ticker} - {self.name}"
