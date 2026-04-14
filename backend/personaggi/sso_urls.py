from django.urls import path

from personaggi.sso import (
    ArcanaSSOCallbackView,
    ArcanaSSOExchangeTicketView,
    ArcanaSSOLoginStartView,
    ArcanaSSOPasswordStatusView,
    ArcanaSSOSetLocalPasswordView,
    ArcanaSSOStaffProfilesView,
    ArcanaSSOStatusView,
)


urlpatterns = [
    path("status/", ArcanaSSOStatusView.as_view(), name="arcana-sso-status"),
    path("login/", ArcanaSSOLoginStartView.as_view(), name="arcana-sso-login"),
    path("callback/", ArcanaSSOCallbackView.as_view(), name="arcana-sso-callback"),
    path("exchange-ticket/", ArcanaSSOExchangeTicketView.as_view(), name="arcana-sso-exchange-ticket"),
    path("password-status/", ArcanaSSOPasswordStatusView.as_view(), name="arcana-sso-password-status"),
    path("set-local-password/", ArcanaSSOSetLocalPasswordView.as_view(), name="arcana-sso-set-local-password"),
    path("staff/profiles/", ArcanaSSOStaffProfilesView.as_view(), name="arcana-sso-staff-profiles"),
]
