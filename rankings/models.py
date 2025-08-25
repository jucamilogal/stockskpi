from django.db import models
from companies.models import Company

class Ranking(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    definition_json = models.JSONField()
    run_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class RankingResult(models.Model):
    ranking = models.ForeignKey(Ranking, on_delete=models.CASCADE, related_name="results")
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    score = models.FloatField()
    rank = models.IntegerField()
    snapshot_json = models.JSONField()

    class Meta:
        unique_together = ("ranking", "company")
        indexes = [models.Index(fields=["ranking", "rank"])]
