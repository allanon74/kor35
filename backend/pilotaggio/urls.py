"""
URL configuration per l'app pilotaggio.

Rotte sotto `/api/pilot/...`:
- auth/qr-login, auth/logout
- session/start, session/state, session/command, session/abort, session/history
- subsystems/qr-action  (login DRF token: usato da app principale)
- catalog, prefetture
- staff/sottosistemi, staff/comandi, staff/intensita, staff/eventi, staff/sequenze,
  staff/stati-allerta, staff/comandi-critici, staff/sessioni
"""
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"staff/sottosistemi", views.StaffSottosistemaViewSet, basename="pilot-staff-sottosistemi")
router.register(r"staff/comandi", views.StaffComandoViewSet, basename="pilot-staff-comandi")
router.register(
    r"staff/comandi-critici",
    views.StaffComandoCriticoGlobaleViewSet,
    basename="pilot-staff-comandi-critici",
)
router.register(r"staff/intensita", views.StaffIntensitaViewSet, basename="pilot-staff-intensita")
router.register(r"staff/eventi", views.StaffEventoViewSet, basename="pilot-staff-eventi")
router.register(r"staff/sequenze", views.StaffSequenzaViewSet, basename="pilot-staff-sequenze")
router.register(
    r"staff/stati-allerta", views.StaffStatoAllertaViewSet, basename="pilot-staff-stati-allerta"
)


urlpatterns = [
    path("console-enabled/", views.PilotConsoleEnabledView.as_view(), name="pilot-console-enabled"),
    path("auth/auto-login/", views.PilotConsoleAutoLoginView.as_view(), name="pilot-auto-login"),
    path("auth/console-ticket/", views.PilotConsoleTicketCreateView.as_view(), name="pilot-ticket-create"),
    path("auth/console-ticket/<uuid:ticket_id>/claim/", views.PilotConsoleTicketClaimView.as_view(), name="pilot-ticket-claim"),
    path("auth/console-ticket/<uuid:ticket_id>/status/", views.PilotConsoleTicketStatusView.as_view(), name="pilot-ticket-status"),
    path("auth/qr-login/", views.PilotQrLoginView.as_view(), name="pilot-qr-login"),
    path("auth/logout/", views.PilotLogoutView.as_view(), name="pilot-logout"),

    path("session/state/", views.PilotStateView.as_view(), name="pilot-state"),
    path("session/start/", views.PilotSessionStartView.as_view(), name="pilot-session-start"),
    path("session/command/", views.PilotSessionCommandView.as_view(), name="pilot-session-command"),
    path("session/subsystem-set/", views.PilotSubsystemSetView.as_view(), name="pilot-session-subsystem-set"),
    path("session/abort/", views.PilotSessionAbortView.as_view(), name="pilot-session-abort"),
    path("session/emergency-landing/", views.PilotSessionEmergencyLandingView.as_view(), name="pilot-session-emergency-landing"),
    path("session/history/", views.PilotSessionHistoryView.as_view(), name="pilot-session-history"),
    path("runtime/tick-status/", views.PilotTickRuntimeStatusView.as_view(), name="pilot-runtime-tick-status"),
    path("runtime/tick-control/", views.PilotTickRuntimeControlView.as_view(), name="pilot-runtime-tick-control"),

    path("subsystems/qr-action/", views.PilotSubsystemQrActionView.as_view(), name="pilot-subsystem-qr"),
    path("subsystems/qr-repair/", views.PilotSubsystemQrRepairView.as_view(), name="pilot-subsystem-qr-repair"),

    path("catalog/", views.PilotCatalogView.as_view(), name="pilot-catalog"),
    path("prefetture/", views.PilotPrefettureView.as_view(), name="pilot-prefetture"),

    path("staff/sessioni/", views.StaffSessioneListView.as_view(), name="pilot-staff-sessioni"),
    path("staff/runtime-config/", views.StaffPilotRuntimeConfigView.as_view(), name="pilot-staff-runtime-config"),
    path("", include(router.urls)),
]
