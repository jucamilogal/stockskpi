from django.urls import path
from .views import CompanyListView, CompanyDetailRedirect

app_name = "companies"

urlpatterns = [
    path("", CompanyListView.as_view(), name="list"),
    path("<str:ticker>/", CompanyDetailRedirect.as_view(), name="detail"),
]
