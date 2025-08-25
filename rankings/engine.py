import pandas as pd
from django.db import transaction
from companies.models import Company
from fundamentals.models import Metric
from rankings.models import Ranking, RankingResult

SLUG = "quality_value"
DEF = {"name": SLUG, "weights": {"Revenue_YoY": 1.0, "NetIncome_TTM": 0.5}}

def run_ranking():
    rows = []
    for c in Company.objects.all():
        m = {x.key: float(x.value) for x in Metric.objects.filter(company=c)}
        if "Revenue_YoY" in m and "NetIncome_TTM" in m:
            rows.append({"ticker": c.ticker, **m})
    if not rows:
        return None

    df = pd.DataFrame(rows).set_index("ticker")
    for k in DEF["weights"]:
        mu = df[k].mean()
        sd = df[k].std(ddof=0) or 1.0
        df[f"z_{k}"] = (df[k] - mu) / sd
    df["score"] = sum(DEF["weights"][k] * df[f"z_{k}"] for k in DEF["weights"])
    df.sort_values("score", ascending=False, inplace=True)

    with transaction.atomic():
        # Reuse (or create) the same Ranking row
        r, _ = Ranking.objects.get_or_create(
            slug=SLUG,
            defaults={"name": "Quality + Value", "definition_json": DEF},
        )
        # keep definition up to date
        r.definition_json = DEF
        r.save(update_fields=["definition_json"])

        # Replace previous results
        RankingResult.objects.filter(ranking=r).delete()

        for i, (tic, row) in enumerate(df.iterrows(), 1):
            drivers = {k: float(row[f"z_{k}"]) for k in DEF["weights"]}
            RankingResult.objects.create(
                ranking=r,
                company=Company.objects.get(ticker=tic),
                score=float(row["score"]),
                rank=i,
                snapshot_json=drivers,
            )
    return r
