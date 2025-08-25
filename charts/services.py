import plotly.graph_objects as go
from fundamentals.models import Statement
from marketdata.models import PriceBar

def revenue_trend(company):
    qs = (Statement.objects
          .filter(company=company, statement_type="IS", period_type="Q")
          .order_by("period_end"))
    x = [s.period_end for s in qs]
    y = [s.json_payload.get("Revenue") for s in qs]
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines+markers", name="Revenue"))
    fig.update_layout(title=f"Revenue (Quarterly) — {company.ticker}",
                      xaxis_title="Period End", yaxis_title="Revenue")
    return fig.to_json()

def price_trend(company):
    bars = PriceBar.objects.filter(company=company).order_by("date")
    x = [b.date for b in bars]
    y = [float(b.close) for b in bars]
    fig = go.Figure(go.Scatter(x=x, y=y, mode="lines", name="Close"))
    fig.update_layout(title=f"Price (Daily Close) — {company.ticker}",
                      xaxis_title="Date", yaxis_title="Close")
    return fig.to_json()
