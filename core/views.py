from django.shortcuts import render
from companies.models import Company

def dashboard(request):
    tickers = list(Company.objects.order_by("ticker").values_list("ticker", flat=True))
    return render(request, "dashboard.html", {"tickers": tickers})

def pe_view(request):
    return render(request, "pe.html")

def screener_view(request):
    return render(request, "screener.html")