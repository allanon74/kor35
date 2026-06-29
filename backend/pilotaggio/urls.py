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


router.register(
    r"staff/coppie-colori-componente",
    views.StaffCoppiaColoriComponenteViewSet,
    basename="pilot-staff-coppie-colori",
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
    path("session/reset/", views.PilotSessionResetView.as_view(), name="pilot-session-reset"),
    path("session/abort/", views.PilotSessionAbortView.as_view(), name="pilot-session-abort"),
    path("session/emergency-landing/", views.PilotSessionEmergencyLandingView.as_view(), name="pilot-session-emergency-landing"),
    path("session/takeoff/", views.PilotSessionTakeoffView.as_view(), name="pilot-session-takeoff"),
    path("session/takeoff/complete/", views.PilotSessionTakeoffCompleteView.as_view(), name="pilot-session-takeoff-complete"),
    path("session/landing/", views.PilotSessionLandingView.as_view(), name="pilot-session-landing"),
    path("session/allarme-equipaggio/", views.PilotSessionAllarmeEquipaggioView.as_view(), name="pilot-session-allarme-equipaggio"),
    path("allarme-led/state/", views.PilotAllarmeLedStateView.as_view(), name="pilot-allarme-led-state"),
    path("session/history/", views.PilotSessionHistoryView.as_view(), name="pilot-session-history"),
    path("session/diario/", views.PilotSessionDiarioView.as_view(), name="pilot-session-diario"),
    path("session/voli/", views.PilotSessionVoliView.as_view(), name="pilot-session-voli"),
    path("runtime/tick-status/", views.PilotTickRuntimeStatusView.as_view(), name="pilot-runtime-tick-status"),
    path("runtime/tick-control/", views.PilotTickRuntimeControlView.as_view(), name="pilot-runtime-tick-control"),

    path("subsystems/qr-action/", views.PilotSubsystemQrActionView.as_view(), name="pilot-subsystem-qr"),
    path("subsystems/qr-repair/", views.PilotSubsystemQrRepairView.as_view(), name="pilot-subsystem-qr-repair"),
    path("subsystems/qr-recharge/", views.PilotSubsystemQrRechargeView.as_view(), name="pilot-subsystem-qr-recharge"),

    path("catalog/", views.PilotCatalogView.as_view(), name="pilot-catalog"),
    path("prefetture/", views.PilotPrefettureView.as_view(), name="pilot-prefetture"),

    path("staff/sessioni/", views.StaffSessioneListView.as_view(), name="pilot-staff-sessioni"),
    path("staff/sessione-live/", views.StaffSessioneLiveView.as_view(), name="pilot-staff-sessione-live"),
    path(
        "staff/sessione-live/sottosistema/",
        views.StaffSessioneSottosistemaAzioneView.as_view(),
        name="pilot-staff-sessione-sottosistema-azione",
    ),
    path(
        "staff/sessioni-orfane/",
        views.StaffSessioniOrfaneView.as_view(),
        name="pilot-staff-sessioni-orfane",
    ),
    path("navigation-config/", views.PilotNavigationConfigView.as_view(), name="pilot-navigation-config"),
    path("staff/runtime-config/", views.StaffPilotRuntimeConfigView.as_view(), name="pilot-staff-runtime-config"),
    path("staff/stiva/", views.StaffPilotStivaView.as_view(), name="pilot-staff-stiva"),
    path(
        "staff/eventi/aggiorna-codici-da-stato/",
        views.StaffAggiornaCodiciEventiView.as_view(),
        name="pilot-staff-eventi-aggiorna-codici",
    ),
    path("stiva/", views.PilotStivaView.as_view(), name="pilot-stiva"),
    path("compattatore/state/", views.PilotCompattatoreStateView.as_view(), name="pilot-compattatore-state"),
    path(
        "compattatore/compressione/",
        views.PilotCompattatoreCompressioneView.as_view(),
        name="pilot-compattatore-compressione",
    ),
    path(
        "compattatore/decompressione/",
        views.PilotCompattatoreDecompressioneView.as_view(),
        name="pilot-compattatore-decompressione",
    ),
    path(
        "compattatore/risonanza/",
        views.PilotCompattatoreRisonanzaView.as_view(),
        name="pilot-compattatore-risonanza",
    ),
    path(
        "compattatore/quantico/",
        views.PilotCompattatoreQuanticoView.as_view(),
        name="pilot-compattatore-quantico",
    ),
    path("scientifica/console-enabled/", views.ScientificaConsoleEnabledView.as_view(), name="scientifica-console-enabled"),
    path("scientifica/auth/auto-login/", views.ScientificaConsoleAutoLoginView.as_view(), name="scientifica-auto-login"),
    path(
        "scientifica/auth/console-ticket/",
        views.ScientificaConsoleTicketCreateView.as_view(),
        name="scientifica-ticket-create",
    ),
    path("scientifica/state/", views.PilotScientificaStateView.as_view(), name="pilot-scientifica-state"),
    path(
        "scientifica/scan-profondo/",
        views.PilotScientificaScanProfondoView.as_view(),
        name="pilot-scientifica-scan-profondo",
    ),
    path(
        "scientifica/fase/",
        views.PilotScientificaFaseView.as_view(),
        name="pilot-scientifica-fase",
    ),
    path(
        "scientifica/intervento/",
        views.PilotScientificaInterventoView.as_view(),
        name="pilot-scientifica-intervento",
    ),
    path("", include(router.urls)),
]
