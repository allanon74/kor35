from django.urls import path

from personaggi.sso import ArcanaSSOCallbackView, ArcanaSSOExchangeTicketView, ArcanaSSOLoginStartView


urlpatterns = [
    path("login/", ArcanaSSOLoginStartView.as_view(), name="arcana-sso-login"),
    path("callback/", ArcanaSSOCallbackView.as_view(), name="arcana-sso-callback"),
    path("exchange-ticket/", ArcanaSSOExchangeTicketView.as_view(), name="arcana-sso-exchange-ticket"),
]
