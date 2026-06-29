"""
Views DRF per la console pilotaggio.

Gruppi di endpoint:
1. Autenticazione console (login QR / logout).
2. Runtime sessione di volo (start, stato, comando, ack).
3. QR sottosistemi (guasto/ripristino) per P(N)G con 0SA / 0RI.
4. Staff CRUD per cataloghi (sotto /api/pilot/staff/).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi.models import (
    A_vista,
    Manifesto,
    Personaggio,
    Prefettura,
    QrCode,
)

from .allarme_equipaggio import (
    build_allarme_led_payload,
    imposta_allarme_equipaggio_sessione,
)
from .auth import PilotConsoleTokenAuthentication, get_pilot_from_request
from .engine import (
    _clamp_livello,
    _sessione_ha_decollato,
    applica_effetto_espulsione,
    applica_effetto_guasto,
    applica_effetto_inversione,
    build_annuncio_decollo,
    calcola_distanza_target,
    completa_decollo_sessione,
    evento_attivo_corrente,
    eventi_attivi_correnti,
    finalizza_volo_sottosistemi,
    get_o_crea_stato_sottosistema,
    percentuale_sistemi_operativi,
    prepara_sessione_nuovo_volo,
    staff_azione_sottosistema_sessione,
    staff_imposta_carburante_sessione,
    capacita_carburante_serbatoi,
    intervallo_tick_effettivo_sessione,
    secondi_fino_valutazione_evento,
    termina_sessione_volo,
    tick_sessione_se_dovuto,
    sessione_nave_operativa,
)
from .models import (
    ComandoCriticoGlobale,
    ComandoNave,
    CoppiaColoriComponente,
    DEFCON_MAX,
    EVENTO_ESITO_PENDING,
    EventoAttivoSessione,
    EventoNave,
    IntensitaComando,
    PilotConsoleToken,
    PilotRuntimeConfig,
    PilotConsoleLoginTicket,
    SESSIONE_STATO_ARRIVATA,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_IDLE,
    SESSIONE_STATO_VOLO,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoAllertaPilot,
    StatoSottosistemaSessione,
    TentativoCodice,
    VoceDiarioVolo,
)
from gestione_plot.permissions import IsStaffOrMaster

from .permissions import IsPilotConsole
from .serializers import (
    ComandoCriticoGlobaleListSerializer,
    ComandoCriticoGlobaleSerializer,
    ComandoNaveSerializer,
    CoppiaColoriComponenteSerializer,
    EventoAttivoSerializer,
    EventoNaveListSerializer,
    EventoNaveSerializer,
    IntensitaComandoListSerializer,
    IntensitaComandoSerializer,
    PilotConsoleTokenSerializer,
    PilotRuntimeConfigSerializer,
    SequenzaVoloSerializer,
    SessioneVoloSerializer,
    SottosistemaNaveListSerializer,
    SottosistemaNaveSerializer,
    StatoAllertaPilotListSerializer,
    StatoAllertaPilotPublicSerializer,
    StatoAllertaPilotSerializer,
    StatoSottosistemaRuntimeSerializer,
    TentativoCodiceSerializer,
    VoceDiarioVoloSerializer,
)


SIGLA_PILOTAGGIO = "0PI"
SIGLA_SABOTAGGIO = "0SA"
SIGLA_RIPARAZIONE = "0RI"
RIGENERAZIONE_CARBURANTE_AL_MINUTO = 100.0


def _personaggio_da_qr(qr: QrCode) -> Optional[Personaggio]:
    """Risolve il Personaggio collegato al QR (via inventario_ptr_id == vista_id)."""
    if qr is None or qr.vista_id is None:
        return None
    return Personaggio.objects.filter(inventario_ptr_id=qr.vista_id).first()


def _sottosistema_da_qr(qr: QrCode) -> Optional[SottosistemaNave]:
    if qr is None or qr.vista_id is None:
        return None
    return SottosistemaNave.objects.filter(a_vista_id=qr.vista_id).first()


def _sessione_attiva_corrente() -> Optional[SessioneVolo]:
    """Singleton nave: unica sessione idle/volo non terminata (condivisa da tutti i piloti)."""
    return sessione_nave_operativa()


def _ultima_sessione_nave() -> Optional[SessioneVolo]:
    return SessioneVolo.objects.order_by("-created_at").first()


def _capacita_energia_nave() -> tuple[float, float]:
    capacita_serbatoi = float(
        SottosistemaNave.objects.filter(attivo=True, tipo="serbatoio").aggregate(
            total=Sum("capacita_carburante")
        )["total"]
        or 0.0
    )
    capacita_batterie = float(
        SottosistemaNave.objects.filter(attivo=True, tipo="batteria").aggregate(
            total=Sum("capacita_storage")
        )["total"]
        or 0.0
    )
    carburante_max = max(0.0, capacita_serbatoi) or 1000.0
    storage_max = max(0.0, capacita_batterie)
    return carburante_max, storage_max


def _risorse_energia_da_ultima_sessione() -> tuple[float, float, float, float]:
    """
    Carburante e batterie ereditati dall'ultimo volo/sessione (nessun rifornimento automatico).
    """
    carburante_max, storage_max = _capacita_energia_nave()
    ultima = _ultima_sessione_nave()
    if ultima is None:
        return carburante_max, carburante_max, storage_max, storage_max
    carb_att = max(0.0, min(carburante_max, float(ultima.carburante_attuale or 0.0)))
    stor_att = max(0.0, min(storage_max, float(ultima.storage_energia_attuale or 0.0)))
    return carb_att, carburante_max, stor_att, storage_max


def _sessione_pilota_operativa(pilota) -> Optional[SessioneVolo]:
    """Compat: una nave → sessione globale, non legata al pilota connesso."""
    return _sessione_attiva_corrente()


def _chiudi_sessioni_orfane_nave() -> list[dict]:
    """
    Chiude sessioni idle/volo duplicate (oltre alla sessione nave canonica).
    Le orfane non devono ricevere tick ne' propagare spegnimento sulla nave persistente.
    """
    from pilotaggio.engine import termina_sessione_volo
    from pilotaggio.nave_sync_context import suppress_sessione_nave_sync

    canonica = _sessione_attiva_corrente()
    if canonica is None:
        return []
    orfane = list(
        SessioneVolo.objects.exclude(stato__in=[SESSIONE_STATO_ARRIVATA, SESSIONE_STATO_CRASHED])
        .exclude(pk=canonica.pk)
        .order_by("created_at")
    )
    if not orfane:
        return []

    chiuse: list[dict] = []
    with suppress_sessione_nave_sync():
        for sessione in orfane:
            chiuse.append(
                {
                    "id": str(sessione.pk),
                    "stato_precedente": sessione.stato,
                    "pilota_id": sessione.pilota_id,
                    "pilota_nome": (
                        getattr(sessione.pilota, "nome", str(sessione.pilota))
                        if sessione.pilota_id
                        else None
                    ),
                    "created_at": (
                        sessione.created_at.isoformat() if sessione.created_at else None
                    ),
                }
            )
            if sessione.stato == SESSIONE_STATO_VOLO:
                termina_sessione_volo(
                    sessione,
                    SESSIONE_STATO_ARRIVATA,
                    sync_nave_sottosistemi=False,
                )
            else:
                sessione.stato = SESSIONE_STATO_ARRIVATA
                sessione.ended_at = timezone.now()
                sessione.save(update_fields=["stato", "ended_at", "updated_at"])
    return chiuse


def _chiudi_sessioni_orfane_pilota(pilota) -> list[dict]:
    """Compat: una nave → chiusura orfane globale (il pilota e' ignorato)."""
    return _chiudi_sessioni_orfane_nave()


def _sessioni_orfane_queryset(*, pilota_id=None):
    qs = (
        SessioneVolo.objects.exclude(
            stato__in=[SESSIONE_STATO_ARRIVATA, SESSIONE_STATO_CRASHED]
        )
        .select_related("pilota")
        .order_by("-created_at")
    )
    if pilota_id is not None:
        qs = qs.filter(pilota_id=pilota_id)
    return qs


def _riepilogo_sessioni_orfane(*, pilota_id=None) -> dict:
    """Elenco sessioni duplicate oltre alla sessione nave canonica."""
    canonica = _sessione_attiva_corrente()
    orfane: list[dict] = []
    canoniche: list[dict] = []

    for sessione in _sessioni_orfane_queryset(pilota_id=pilota_id):
        row = {
            "id": str(sessione.pk),
            "stato": sessione.stato,
            "pilota_id": sessione.pilota_id,
            "pilota_nome": getattr(sessione.pilota, "nome", None) if sessione.pilota_id else None,
            "created_at": (
                sessione.created_at.isoformat() if sessione.created_at else None
            ),
        }
        if canonica is not None and sessione.pk == canonica.pk:
            row["orfana"] = False
            canoniche.append(row)
        else:
            row["orfana"] = True
            orfane.append(row)

    return {
        "totale_orfane": len(orfane),
        "totale_attive": len(orfane) + len(canoniche),
        "sessioni_orfane": orfane,
        "sessioni_canoniche": canoniche,
    }


def pulisci_sessioni_orfane_staff(*, pilota_id=None) -> dict:
    """Chiude tutte le sessioni orfane (singleton nave)."""
    chiuse = _chiudi_sessioni_orfane_nave()

    riepilogo = _riepilogo_sessioni_orfane(pilota_id=pilota_id)
    return {
        "totale_chiuse": len(chiuse),
        "sessioni_chiuse": chiuse,
        "sessioni_attive_rimanenti": riepilogo["totale_attive"],
        "orfane_rimanenti": riepilogo["totale_orfane"],
    }


def _motore_livello_target(sessione: SessioneVolo) -> int:
    motore = (
        StatoSottosistemaSessione.objects.filter(
            sessione=sessione, sottosistema__tipo="motore"
        )
        .order_by("sottosistema__ordine", "sottosistema__codice")
        .first()
    )
    return int(motore.livello_target or 0) if motore else 0


def _errore_se_motore_non_spento(sessione: SessioneVolo):
    if _motore_livello_target(sessione) != 0:
        return Response(
            {
                "error": (
                    "Operazione disponibile solo con motore principale a livello 0."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _sessione_staff_operativa() -> Optional[SessioneVolo]:
    """
    Sessione per il pannello staff: idle/volo attivi, oppure ultima sessione
    (anche terminata) per controllo manuale sottosistemi.
    """
    attiva = _sessione_attiva_corrente()
    if attiva is not None:
        return attiva
    return SessioneVolo.objects.order_by("-created_at").first()


def _sessione_pilota_per_console(pilota) -> Optional[SessioneVolo]:
    """
    Sessione mostrata dalla console pilota (nave unica: tutti i piloti vedono la stessa).
    """
    attiva = _sessione_attiva_corrente()
    if attiva is not None:
        return attiva
    return _ultima_sessione_nave()


def _ensure_sessione_idle_pilota(pilota) -> SessioneVolo:
    """Sessione a terra condivisa dopo logout/reset (stato nave persistente)."""
    attiva = _sessione_attiva_corrente()
    if attiva is not None:
        if attiva.stato == SESSIONE_STATO_IDLE:
            from pilotaggio.stato_nave import propaga_stati_nave_a_sessione

            propaga_stati_nave_a_sessione(attiva)
        return attiva

    ultima = _ultima_sessione_nave()
    if ultima is not None and ultima.is_terminata:
        finalizza_volo_sottosistemi(ultima)

    carb_att, carb_max, stor_att, stor_max = _risorse_energia_da_ultima_sessione()
    sessione = SessioneVolo.objects.create(
        pilota=pilota,
        stato=SESSIONE_STATO_IDLE,
        defcon=0,
        durata_pianificata_secondi=600,
        carburante_attuale=carb_att,
        carburante_massimo=carb_max,
        storage_energia_attuale=stor_att,
        storage_energia_massimo=stor_max,
    )
    from pilotaggio.stato_nave import propaga_stati_nave_a_sessione

    propaga_stati_nave_a_sessione(sessione)
    return sessione


def _request_prefers_html(request) -> bool:
    accept = str(request.headers.get("Accept", "")).lower()
    if "application/json" in accept:
        return False
    return "text/html" in accept


def _ensure_runtime_subsystems(sessione: SessioneVolo) -> None:
    """
    Inizializza gli stati runtime sottosistema per la sessione corrente.
    """
    presenti = set(
        StatoSottosistemaSessione.objects.filter(sessione=sessione).values_list(
            "sottosistema_id", flat=True
        )
    )
    to_create = []
    from pilotaggio.stato_nave import defaults_stato_da_nave

    for s in SottosistemaNave.objects.filter(attivo=True).order_by("ordine", "codice"):
        if s.pk in presenti:
            continue
        defaults = defaults_stato_da_nave(s)
        to_create.append(
            StatoSottosistemaSessione(
                sessione=sessione,
                sottosistema=s,
                **defaults,
            )
        )
    if to_create:
        StatoSottosistemaSessione.objects.bulk_create(to_create)


def _tick_runtime_payload(sessione: Optional[SessioneVolo] = None) -> dict:
    cfg = PilotRuntimeConfig.get_solo()
    heartbeat = cfg.tick_last_heartbeat
    base_interval = float(cfg.tick_interval_secondi or 5.0)
    effective_interval = base_interval
    evento_attivo = False
    if sessione is not None and sessione.is_attiva:
        effective_interval = float(intervallo_tick_effettivo_sessione(sessione))
        evento_attivo = EventoAttivoSessione.objects.filter(
            sessione=sessione, esito=EVENTO_ESITO_PENDING
        ).exists()
    alive = False
    if heartbeat is not None:
        delta = (timezone.now() - heartbeat).total_seconds()
        alive = delta <= max(8.0, effective_interval * 2.5)
    return {
        "enabled": bool(cfg.tick_enabled),
        "interval": effective_interval,
        "interval_base": base_interval,
        "evento_attivo": evento_attivo,
        "last_heartbeat": heartbeat.isoformat() if heartbeat else None,
        "alive": alive,
        "login_required_console": bool(cfg.login_required_console),
        "alarm_audio_enabled": bool(cfg.alarm_audio_enabled),
        "riparazione_componenti_abilitata": bool(cfg.riparazione_componenti_abilitata),
        "compattatore_console_abilitata": bool(cfg.compattatore_console_abilitata),
        "compattatore_stat_accesso_sigla": cfg.compattatore_stat_accesso_sigla or "0IN",
        "compattatore_quantico_abilitato": bool(cfg.compattatore_quantico_abilitato),
    }


def _login_required_console() -> bool:
    return bool(PilotRuntimeConfig.get_solo().login_required_console)


def _ensure_tick_enabled() -> None:
    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.tick_enabled:
        cfg.tick_enabled = True
        cfg.save(update_fields=["tick_enabled", "updated_at"])


def _disable_tick_if_no_active_sessions() -> None:
    if SessioneVolo.objects.exclude(stato__in=["arrivata", "crashed"]).exists():
        return
    cfg = PilotRuntimeConfig.get_solo()
    if cfg.tick_enabled:
        cfg.tick_enabled = False
        cfg.save(update_fields=["tick_enabled", "updated_at"])


def _calcola_carburante_con_rigenerazione(
    base_carburante: float, carburante_massimo: float, riferimento_at, now
) -> float:
    if riferimento_at is None:
        return max(0.0, min(float(carburante_massimo or 0.0), float(base_carburante or 0.0)))
    elapsed_sec = max(0.0, float((now - riferimento_at).total_seconds()))
    regen = (elapsed_sec / 60.0) * RIGENERAZIONE_CARBURANTE_AL_MINUTO
    return max(
        0.0,
        min(float(carburante_massimo or 0.0), float(base_carburante or 0.0) + regen),
    )


# ---------------------------------------------------------------------------
# 1) Autenticazione console
# ---------------------------------------------------------------------------


class PilotQrLoginView(APIView):
    """
    POST /api/pilot/auth/qr-login/
    Body: {"qr_id": "..."}

    Verifica:
    - QR collegato a un Personaggio (inventario_ptr);
    - statistica 0PI del personaggio >= 1;
    Rilascia un PilotConsoleToken e revoca eventuali token precedenti dello
    stesso pilota.
    """

    authentication_classes: list = []
    permission_classes: list = [permissions.AllowAny]

    def post(self, request):
        if not _login_required_console():
            return Response(
                {"error": "Login console disattivato in questa configurazione."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qr_id = (request.data.get("qr_id") or "").strip()
        if not qr_id:
            return Response(
                {"error": "qr_id mancante."}, status=status.HTTP_400_BAD_REQUEST
            )
        qr = QrCode.objects.select_related("vista").filter(id=qr_id).first()
        if not qr:
            return Response(
                {"error": "QR non trovato."}, status=status.HTTP_404_NOT_FOUND
            )
        pilota = _personaggio_da_qr(qr)
        if not pilota:
            return Response(
                {"error": "Questo QR non e' associato a un personaggio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        valore = pilota.get_valore_statistica(SIGLA_PILOTAGGIO)
        if int(valore or 0) < 1:
            return Response(
                {
                    "error": (
                        f"Accesso negato: serve statistica {SIGLA_PILOTAGGIO} >= 1 "
                        f"(hai {valore})."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            PilotConsoleToken.objects.filter(
                pilota=pilota, revocato_at__isnull=True
            ).update(revocato_at=timezone.now())
            token = PilotConsoleToken.objects.create(
                pilota=pilota, token=PilotConsoleToken.genera_token()
            )

        return Response(
            {
                "token": token.token,
                "pilota": {
                    "id": pilota.pk,
                    "nome": getattr(pilota, "nome", str(pilota)),
                    "statistica_0PI": valore,
                },
            },
            status=status.HTTP_200_OK,
        )


class PilotConsoleEnabledView(APIView):
    authentication_classes: list = []
    permission_classes: list = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "enabled": bool(getattr(settings, "PILOT_CONSOLE_ENABLED", False)),
                "login_required": _login_required_console(),
            }
        )


class PilotConsoleAutoLoginView(APIView):
    """
    Auto-login per ambienti non produzione quando login console e' disattivato.
    """

    authentication_classes: list = []
    permission_classes: list = [permissions.AllowAny]

    def post(self, request):
        if _login_required_console():
            return Response({"error": "Login obbligatorio: auto-login disabilitato."}, status=status.HTTP_403_FORBIDDEN)

        pilota = None
        candidati = Personaggio.objects.all().order_by("nome")
        for pg in candidati:
            if int(pg.get_valore_statistica(SIGLA_PILOTAGGIO) or 0) >= 1:
                pilota = pg
                break
        if pilota is None:
            pilota = candidati.first()
        if pilota is None:
            return Response({"error": "Nessun personaggio disponibile per auto-login."}, status=status.HTTP_400_BAD_REQUEST)

        # Kiosk con due finestre Chromium (profili separati): ognuna chiama auto-login e
        # ha il suo localStorage. Revocare qui tutti i token del pilota invalidava l'altra
        # finestra → loop continuo di 401 su /session/state/. Riutilizziamo un token attivo
        # se esiste; altrimenti ne creiamo uno nuovo senza revocare gli altri (logout revoca
        # solo il token usato).
        with transaction.atomic():
            existing = (
                PilotConsoleToken.objects.select_for_update()
                .filter(pilota=pilota, revocato_at__isnull=True)
                .order_by("-created_at")
                .first()
            )
            if existing:
                token_obj = existing
                mode = "auto_reuse"
            else:
                token_obj = PilotConsoleToken.objects.create(
                    pilota=pilota, token=PilotConsoleToken.genera_token()
                )
                mode = "auto"

        return Response(
            {
                "token": token_obj.token,
                "pilota": {"id": pilota.pk, "nome": getattr(pilota, "nome", str(pilota))},
                "mode": mode,
            },
            status=status.HTTP_200_OK,
        )


class PilotConsoleTicketCreateView(APIView):
    """
    Crea un ticket temporaneo da mostrare come QR in console.
    """

    authentication_classes: list = []
    permission_classes: list = [permissions.AllowAny]

    def post(self, request):
        if not _login_required_console():
            return Response({"error": "Login ticket disattivato (console senza login)."}, status=status.HTTP_400_BAD_REQUEST)
        if not bool(getattr(settings, "PILOT_CONSOLE_ENABLED", False)):
            return Response({"error": "Console pilota disabilitata su questo ambiente."}, status=status.HTTP_403_FORBIDDEN)
        durata_secondi = int(request.data.get("durata_secondi") or 120)
        durata_secondi = max(30, min(durata_secondi, 300))
        ticket = PilotConsoleLoginTicket.objects.create(
            codice=PilotConsoleLoginTicket.genera_codice(),
            expires_at=timezone.now() + timedelta(seconds=durata_secondi),
        )
        claim_path = reverse("pilot-ticket-claim", kwargs={"ticket_id": ticket.pk})
        claim_url = request.build_absolute_uri(f"{claim_path}?c={ticket.codice}")
        return Response(
            {
                "ticket_id": str(ticket.pk),
                "codice": ticket.codice,
                "expires_at": ticket.expires_at.isoformat(),
                "claim_url": claim_url,
            },
            status=status.HTTP_201_CREATED,
        )


class PilotConsoleTicketClaimView(APIView):
    """
    Endpoint aperto dal telefono del giocatore già autenticato.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        if not _login_required_console():
            return Response({"error": "Login ticket disattivato (console senza login)."}, status=status.HTTP_400_BAD_REQUEST)
        wants_html = _request_prefers_html(request)
        return_url = "/app/start"
        codice = (request.query_params.get("c") or "").strip()
        ticket = get_object_or_404(PilotConsoleLoginTicket, pk=ticket_id)
        if not codice or ticket.codice != codice:
            if wants_html:
                return render(
                    request,
                    "pilotaggio/claim_result.html",
                    {
                        "ok": False,
                        "title": "Ticket non valido",
                        "message": "Il codice ticket non e' valido.",
                        "return_url": return_url,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response({"error": "Ticket non valido."}, status=status.HTTP_403_FORBIDDEN)
        if ticket.scaduto:
            if wants_html:
                return render(
                    request,
                    "pilotaggio/claim_result.html",
                    {
                        "ok": False,
                        "title": "Ticket scaduto",
                        "message": "Il ticket e' scaduto. Chiedi al pilota di rigenerare il QR.",
                        "return_url": return_url,
                    },
                    status=status.HTTP_410_GONE,
                )
            return Response({"error": "Ticket scaduto."}, status=status.HTTP_410_GONE)

        personaggio_id = request.query_params.get("personaggio_id")
        qs = Personaggio.objects.filter(proprietario=request.user)
        if personaggio_id:
            qs = qs.filter(pk=personaggio_id)
        candidato = None
        for pg in qs.order_by("nome"):
            if int(pg.get_valore_statistica(SIGLA_PILOTAGGIO) or 0) >= 1:
                candidato = pg
                break
        if candidato is None:
            if wants_html:
                return render(
                    request,
                    "pilotaggio/claim_result.html",
                    {
                        "ok": False,
                        "title": "Accesso negato",
                        "message": f"Nessun personaggio valido: serve statistica {SIGLA_PILOTAGGIO} >= 1.",
                        "return_url": return_url,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"error": f"Nessun personaggio valido: serve {SIGLA_PILOTAGGIO} >= 1."},
                status=status.HTTP_403_FORBIDDEN,
            )
        ticket.pilota = candidato
        ticket.claimed_at = timezone.now()
        ticket.save(update_fields=["pilota", "claimed_at", "updated_at"])
        if wants_html:
            return render(
                request,
                "pilotaggio/claim_result.html",
                {
                    "ok": True,
                    "title": "Console sbloccata",
                    "message": f"Autenticazione completata per {getattr(candidato, 'nome', str(candidato))}. Ora puoi tornare alla console pilota.",
                    "return_url": return_url,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "status": "claimed",
                "pilota": {"id": candidato.pk, "nome": getattr(candidato, "nome", str(candidato))},
                "ticket_id": str(ticket.pk),
            }
        )


class PilotConsoleTicketStatusView(APIView):
    authentication_classes: list = []
    permission_classes: list = [permissions.AllowAny]

    def get(self, request, ticket_id):
        if not _login_required_console():
            return Response({"error": "Login ticket disattivato (console senza login)."}, status=status.HTTP_400_BAD_REQUEST)
        codice = (request.query_params.get("c") or "").strip()
        ticket = get_object_or_404(PilotConsoleLoginTicket, pk=ticket_id)
        if not codice or ticket.codice != codice:
            return Response({"error": "Ticket non valido."}, status=status.HTTP_403_FORBIDDEN)
        if ticket.scaduto:
            return Response({"status": "expired"}, status=status.HTTP_200_OK)
        if ticket.pilota_id is None:
            return Response({"status": "pending"}, status=status.HTTP_200_OK)

        if ticket.token_console:
            return Response(
                {
                    "status": "authorized",
                    "token": ticket.token_console,
                    "pilota": {"id": ticket.pilota.pk, "nome": getattr(ticket.pilota, "nome", str(ticket.pilota))},
                },
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            PilotConsoleToken.objects.filter(
                pilota=ticket.pilota, revocato_at__isnull=True
            ).update(revocato_at=timezone.now())
            token = PilotConsoleToken.objects.create(
                pilota=ticket.pilota, token=PilotConsoleToken.genera_token()
            )
            ticket.token_console = token.token
            ticket.token_issued_at = timezone.now()
            ticket.save(update_fields=["token_console", "token_issued_at", "updated_at"])

        return Response(
            {
                "status": "authorized",
                "token": token.token,
                "pilota": {"id": ticket.pilota.pk, "nome": getattr(ticket.pilota, "nome", str(ticket.pilota))},
            },
            status=status.HTTP_200_OK,
        )


class PilotLogoutView(APIView):
    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        token: PilotConsoleToken = request.auth
        pilota = token.pilota
        PilotConsoleToken.objects.filter(pk=token.pk).update(
            revocato_at=timezone.now()
        )
        _ensure_sessione_idle_pilota(pilota)
        _disable_tick_if_no_active_sessions()
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class PilotSessionResetView(APIView):
    """
    POST /api/pilot/session/reset/
    Torna al precontrollo dopo crash/arrivo senza revocare il token console.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _ensure_sessione_idle_pilota(pilota)
        _disable_tick_if_no_active_sessions()
        return Response(_build_state_payload(sessione, pilota), status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 2) Runtime sessione di volo
# ---------------------------------------------------------------------------


def _build_state_payload(sessione: SessioneVolo, pilota: Personaggio) -> dict:
    """Stato runtime completo per la console pilota."""
    if sessione is not None:
        _ensure_runtime_subsystems(sessione)
    decollo = sessione is not None and _sessione_ha_decollato(sessione)
    pending = evento_attivo_corrente(sessione) if sessione and decollo else None
    pending_list = eventi_attivi_correnti(sessione) if sessione and decollo else []

    sub_serializer = StatoSottosistemaRuntimeSerializer(
        StatoSottosistemaSessione.objects.filter(sessione=sessione)
        .select_related("sottosistema")
        .order_by(
            "sottosistema__ordine_gruppo",
            "sottosistema__gruppo",
            "sottosistema__ordine",
            "sottosistema__nome",
            "sottosistema__codice",
        )
        if sessione
        else [],
        many=True,
    )


    stati_qs = StatoAllertaPilot.objects.all().order_by("livello")
    stati_allerta = StatoAllertaPilotPublicSerializer(stati_qs, many=True).data

    sistemi_buckets = {}
    gruppo_ordine_min = {}
    stati_runtime = {
        str(st.pk): st
        for st in (
            sessione.stati_sottosistemi.select_related("sottosistema").all()
            if sessione
            else []
        )
    }
    for row in sub_serializer.data:
        match = stati_runtime.get(str(row["id"]))
        gruppo = (match.sottosistema.gruppo if match else "Sistema").strip() or "Sistema"
        og = (
            int(getattr(match.sottosistema, "ordine_gruppo", 0) or 0)
            if match
            else 0
        )
        gruppo_ordine_min[gruppo] = (
            min(gruppo_ordine_min.get(gruppo, og), og)
            if gruppo in gruppo_ordine_min
            else og
        )
        sistemi_buckets.setdefault(gruppo, []).append(row)
    gruppi_ordinati = sorted(
        sistemi_buckets.keys(),
        key=lambda g: (gruppo_ordine_min.get(g, 0), g.lower()),
    )
    sistemi = {g: sistemi_buckets[g] for g in gruppi_ordinati}
    attesa_valutazione = (
        secondi_fino_valutazione_evento(sessione)
        if sessione is not None and sessione.is_attiva
        else None
    )
    evento_data = EventoAttivoSerializer(pending).data if pending else None
    if evento_data and evento_data.get("direzione_evento"):
        evento_data["descrizione"] = str(evento_data.get("descrizione") or "").replace(
            "<direzione>", str(evento_data["direzione_evento"])
        )
    if evento_data is not None and attesa_valutazione is not None:
        evento_data["secondi_fino_valutazione"] = round(attesa_valutazione, 1)
    if evento_data is not None and pending is not None and pending.reazione_fino_at:
        evento_data["reazione_fino_at"] = pending.reazione_fino_at.isoformat()
        evento_data["intervallo_reazione_secondi"] = pending.intervallo_reazione_secondi
    eventi_data = EventoAttivoSerializer(pending_list, many=True).data if pending_list else []
    for row in eventi_data:
        if row.get("direzione_evento"):
            row["descrizione"] = str(row.get("descrizione") or "").replace(
                "<direzione>", str(row["direzione_evento"])
            )
        if attesa_valutazione is not None:
            row["secondi_fino_valutazione"] = round(attesa_valutazione, 1)

    tick_effettivo = (
        float(intervallo_tick_effettivo_sessione(sessione))
        if sessione is not None and sessione.is_attiva
        else float(getattr(sessione, "tick_secondi", 5) if sessione else 5)
    )

    payload = {
        "pilota": {
            "id": pilota.pk,
            "nome": getattr(pilota, "nome", str(pilota)),
        },
        "sessione": SessioneVoloSerializer(sessione).data if sessione else None,
        "evento_attivo": evento_data,
        "eventi_attivi": eventi_data,
        "sottosistemi": sub_serializer.data,
        "stati_allerta": stati_allerta,
        "defcon_max": DEFCON_MAX,
        "sistemi": sistemi,
        "energia": {
            "produzione": getattr(sessione, "produzione_ultimo_tick", 0.0) if sessione else 0.0,
            "consumo": getattr(sessione, "consumo_ultimo_tick", 0.0) if sessione else 0.0,
            "carburante_attuale": getattr(sessione, "carburante_attuale", 0.0) if sessione else 0.0,
            "carburante_massimo": getattr(sessione, "carburante_massimo", 0.0) if sessione else 0.0,
            "storage_attuale": getattr(sessione, "storage_energia_attuale", 0.0) if sessione else 0.0,
            "storage_massimo": getattr(sessione, "storage_energia_massimo", 0.0) if sessione else 0.0,
            "distanza_percorsa": getattr(sessione, "distanza_percorsa", 0.0) if sessione else 0.0,
            "distanza_target": getattr(sessione, "distanza_target", 0.0) if sessione else 0.0,
            "tick_secondi": tick_effettivo,
            "tick_secondi_base": float(getattr(sessione, "tick_secondi", 5) if sessione else 5),
        },
        "tick_runtime": _tick_runtime_payload(sessione),
        "decollo_effettuato": decollo,
        "percentuale_sistemi_operativi": (
            percentuale_sistemi_operativi(sessione) if sessione else 100
        ),
        "allarme_equipaggio": (
            getattr(sessione, "allarme_equipaggio", "crociera") if sessione else "crociera"
        ),
        "allarme_led": build_allarme_led_payload(sessione),
        "server_time": timezone.now().isoformat(),
    }
    return payload


class PilotStateView(APIView):
    """
    GET /api/pilot/session/state/
    Avanza il tick e restituisce lo stato corrente della console.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def get(self, request):
        from django.db import OperationalError

        pilota = get_pilot_from_request(request)
        _chiudi_sessioni_orfane_pilota(pilota)
        sessione = _sessione_pilota_per_console(pilota)
        if sessione is not None and sessione.is_attiva:
            _ensure_runtime_subsystems(sessione)
            advance_tick = request.query_params.get("tick", "1") not in ("0", "false")
            if advance_tick:
                for attempt in range(2):
                    try:
                        tick_sessione_se_dovuto(sessione)
                        break
                    except OperationalError as exc:
                        if attempt == 0 and "deadlock" in str(exc).lower():
                            continue
                        raise
            sessione.refresh_from_db()
            if sessione.is_terminata:
                _disable_tick_if_no_active_sessions()
        return Response(_build_state_payload(sessione, pilota))


class PilotSessionStartView(APIView):
    """
    POST /api/pilot/session/start/
    Body: {"prefettura_partenza_id": int, "prefettura_arrivo_id": int}

    A nave ferma (stato 0 disattiva). Premi decollo e la sessione entra in volo.
    Distanza e durata derivano dal tragitto (prefettura/regione) e crociera nominale.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        _chiudi_sessioni_orfane_pilota(pilota)
        partenza_id = request.data.get("prefettura_partenza_id")
        arrivo_id = request.data.get("prefettura_arrivo_id")
        partenza = Prefettura.objects.filter(pk=partenza_id).first() if partenza_id else None
        arrivo = Prefettura.objects.filter(pk=arrivo_id).first() if arrivo_id else None
        if partenza is None or arrivo is None:
            return Response(
                {"error": "Prefetture di partenza e arrivo richieste."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attiva = _sessione_attiva_corrente()
        if attiva is not None and attiva.stato != SESSIONE_STATO_IDLE:
            return Response(
                {"error": "La nave ha gia' una missione in corso."},
                status=status.HTTP_409_CONFLICT,
            )

        distanza_target, durata_pianificata = calcola_distanza_target(
            partenza, arrivo, defcon_iniziale=0
        )
        now = timezone.now()
        carburante_max_target, storage_max_target = _capacita_energia_nave()

        with transaction.atomic():
            if attiva is None:
                carb_att, carb_max, stor_att, stor_max = _risorse_energia_da_ultima_sessione()
                attiva = SessioneVolo.objects.create(
                    pilota=pilota,
                    prefettura_partenza=partenza,
                    prefettura_arrivo=arrivo,
                    stato=SESSIONE_STATO_VOLO,
                    durata_pianificata_secondi=durata_pianificata,
                    defcon=0,
                    distanza_target=float(distanza_target),
                    distanza_percorsa=0.0,
                    carburante_massimo=carb_max,
                    carburante_attuale=carb_att,
                    storage_energia_massimo=stor_max,
                    storage_energia_attuale=stor_att,
                    crash_reason="",
                )
            else:
                attiva.pilota = pilota
                attiva.prefettura_partenza = partenza
                attiva.prefettura_arrivo = arrivo
                attiva.stato = SESSIONE_STATO_VOLO
                attiva.durata_pianificata_secondi = durata_pianificata
                attiva.defcon = 0
                attiva.distanza_target = float(distanza_target)
                attiva.distanza_percorsa = 0.0
                attiva.carburante_massimo = carburante_max_target
                attiva.storage_energia_massimo = storage_max_target
                attiva.carburante_attuale = min(
                    float(attiva.carburante_attuale or 0.0),
                    float(attiva.carburante_massimo or carburante_max_target),
                )
                attiva.storage_energia_attuale = min(
                    float(attiva.storage_energia_attuale or 0.0),
                    float(attiva.storage_energia_massimo or storage_max_target),
                )
                attiva.crash_reason = ""
                attiva.save()
            attiva.started_at = now
            attiva.save(update_fields=["started_at", "crash_reason", "updated_at"])
            prepara_sessione_nuovo_volo(attiva)
            _ensure_runtime_subsystems(attiva)
            _ensure_tick_enabled()
            from .flight_log import log_volo_iniziato

            log_volo_iniziato(
                attiva,
                partenza=getattr(partenza, "nome", "?"),
                arrivo=getattr(arrivo, "nome", "?"),
            )

        return Response(_build_state_payload(attiva, pilota))


class PilotSessionCommandView(APIView):
    """
    Endpoint legacy: sequenze/codici manuali dismessi.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        return Response(
            {
                "error": (
                    "Input codici dismesso: la console usa regolazione energetica dei sottosistemi."
                )
            },
            status=status.HTTP_410_GONE,
        )


class PilotSubsystemSetView(APIView):
    """
    POST /api/pilot/session/subsystem-set/
    Body: {
      "sottosistema_id": "...",
      "livello": 0..9,
      "direzione": "avanti|indietro|su|giu|destra|sinistra",
      "invertito": bool,
      "espulso": bool
    }
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        _chiudi_sessioni_orfane_pilota(pilota)
        sessione = _sessione_pilota_operativa(pilota)
        if sessione is None:
            return Response({"error": "Nessuna sessione attiva."}, status=status.HTTP_400_BAD_REQUEST)

        sottosistema_id = request.data.get("sottosistema_id")
        sottosistema = SottosistemaNave.objects.filter(pk=sottosistema_id).first()
        if not sottosistema:
            return Response({"error": "Sottosistema non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if sottosistema.tipo in {"batteria", "serbatoio"}:
            return Response(
                {"error": "Sottosistema non comandabile dalla plancia."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stato = get_o_crea_stato_sottosistema(sessione, sottosistema)
        livello = _clamp_livello(request.data.get("livello", stato.livello_target))
        direzione = str(request.data.get("direzione") or stato.direzione or "avanti")
        if direzione not in {"avanti", "indietro", "su", "giu", "destra", "sinistra"}:
            direzione = "avanti"
        stato.livello_target = livello
        invertito_pre = bool(stato.invertito)
        espulso_pre = bool(stato.espulso)
        if sottosistema.supporta_direzioni:
            stato.direzione = direzione
        if sottosistema.supporta_inversione:
            stato.invertito = bool(request.data.get("invertito", stato.invertito))
        if sottosistema.supporta_espulsione:
            stato.espulso = bool(request.data.get("espulso", stato.espulso))
            if stato.espulso:
                stato.online = False
                stato.livello_target = 0
                stato.livello_attuale = 0
        stato.save()
        if bool(stato.invertito) and not invertito_pre:
            applica_effetto_inversione(sessione, stato)
        if bool(stato.espulso) and not espulso_pre:
            applica_effetto_espulsione(sessione, stato)
            from .flight_log import log_guasto_sottosistema

            log_guasto_sottosistema(sessione, stato, causa="pilota")
        if not stato.online:
            applica_effetto_guasto(sessione, stato)
        sessione.refresh_from_db()
        return Response(_build_state_payload(sessione, pilota), status=status.HTTP_200_OK)


class PilotSessionAbortView(APIView):
    """
    POST /api/pilot/session/abort/
    Termina forzatamente la sessione (solo se non in volo); usata per reset
    di test/staff in dev.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _sessione_attiva_corrente()
        if sessione is None:
            return Response({"status": "no_session"}, status=status.HTTP_200_OK)
        termina_sessione_volo(
            sessione,
            SESSIONE_STATO_CRASHED,
            extra_update_fields={"crash_reason": "manual_abort"},
        )
        from .flight_log import log_precipizio

        log_precipizio(sessione, "manual_abort")
        _disable_tick_if_no_active_sessions()
        return Response(_build_state_payload(sessione, pilota))


class PilotSessionEmergencyLandingView(APIView):
    """
    POST /api/pilot/session/emergency-landing/
    Atterraggio immediato se il motore principale e' a livello 0.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _sessione_attiva_corrente()
        if sessione is None:
            return Response({"error": "Nessuna sessione attiva."}, status=status.HTTP_400_BAD_REQUEST)

        motore = (
            StatoSottosistemaSessione.objects.select_related("sottosistema")
            .filter(sessione=sessione, sottosistema__tipo="motore")
            .order_by("sottosistema__ordine", "sottosistema__codice")
            .first()
        )
        if motore is None:
            return Response({"error": "Motore principale non configurato."}, status=status.HTTP_400_BAD_REQUEST)
        if int(motore.livello_target or 0) != 0:
            return Response(
                {"error": "Atterraggio di emergenza disponibile solo con motore principale a 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not _sessione_ha_decollato(sessione):
            return Response(
                {"error": "Atterraggio di emergenza disponibile solo dopo il decollo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        distanza_finale = float(sessione.distanza_target or sessione.distanza_percorsa or 0.0)
        termina_sessione_volo(
            sessione,
            SESSIONE_STATO_ARRIVATA,
            extra_update_fields={"distanza_percorsa": distanza_finale},
        )
        from .flight_log import log_arrivo

        log_arrivo(sessione, emergenza=True)
        _disable_tick_if_no_active_sessions()
        return Response(_build_state_payload(sessione, pilota))


class PilotSessionTakeoffView(APIView):
    """
    POST /api/pilot/session/takeoff/
    Prepara l'annuncio vocale di decollo (nave ancora a terra).
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _sessione_attiva_corrente()
        if sessione is None or sessione.stato != SESSIONE_STATO_VOLO:
            return Response({"error": "Nessuna missione attiva."}, status=status.HTTP_400_BAD_REQUEST)
        if _sessione_ha_decollato(sessione):
            return Response({"error": "Decollo già effettuato."}, status=status.HTTP_409_CONFLICT)

        motore = (
            StatoSottosistemaSessione.objects.select_related("sottosistema")
            .filter(sessione=sessione, sottosistema__tipo="motore")
            .order_by("sottosistema__ordine", "sottosistema__codice")
            .first()
        )
        if motore is not None and int(motore.livello_target or 0) != 0:
            return Response(
                {"error": "Decollo disponibile solo con motore principale a livello 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        annuncio = build_annuncio_decollo(sessione)
        pct = percentuale_sistemi_operativi(sessione)
        return Response(
            {
                "announcement": annuncio,
                "percentuale_sistemi_operativi": pct,
            },
            status=status.HTTP_200_OK,
        )


class PilotSessionTakeoffCompleteView(APIView):
    """
    POST /api/pilot/session/takeoff/complete/
    Conferma decollo dopo sequenza vocale: inizia crociera ed eventi.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _sessione_attiva_corrente()
        if sessione is None or sessione.stato != SESSIONE_STATO_VOLO:
            return Response({"error": "Nessuna missione attiva."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            completa_decollo_sessione(sessione)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sessione.refresh_from_db()
        return Response(_build_state_payload(sessione, pilota), status=status.HTTP_200_OK)


class PilotSessionLandingView(APIView):
    """
    POST /api/pilot/session/landing/
    Atterraggio programmato (dopo decollo, motore a 0).
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _sessione_pilota_operativa(pilota)
        if sessione is None or sessione.stato != SESSIONE_STATO_VOLO:
            return Response({"error": "Nessuna missione attiva."}, status=status.HTTP_400_BAD_REQUEST)
        if not _sessione_ha_decollato(sessione):
            return Response(
                {"error": "Atterraggio disponibile solo dopo il decollo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        err = _errore_se_motore_non_spento(sessione)
        if err is not None:
            return err

        distanza_finale = float(sessione.distanza_target or sessione.distanza_percorsa or 0.0)
        termina_sessione_volo(
            sessione,
            SESSIONE_STATO_ARRIVATA,
            extra_update_fields={"distanza_percorsa": distanza_finale},
        )
        from .flight_log import log_arrivo

        log_arrivo(sessione, emergenza=False)
        _disable_tick_if_no_active_sessions()
        return Response(_build_state_payload(sessione, pilota))


class PilotSessionAllarmeEquipaggioView(APIView):
    """
    POST /api/pilot/session/allarme-equipaggio/
    Body: { "allarme": "crociera"|"giallo"|"rosso"|"nero"|"blu" }
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        sessione = _sessione_pilota_operativa(pilota)
        if sessione is None:
            return Response({"error": "Nessuna sessione attiva."}, status=status.HTTP_400_BAD_REQUEST)
        allarme = request.data.get("allarme")
        try:
            annuncio = imposta_allarme_equipaggio_sessione(sessione, allarme)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sessione.refresh_from_db()
        payload = _build_state_payload(sessione, pilota)
        payload["announcement"] = annuncio
        return Response(payload, status=status.HTTP_200_OK)


class PilotAllarmeLedStateView(APIView):
    """
    GET /api/pilot/allarme-led/state/
    Stato cromatico per futuri dispositivi LED WiFi (polling LAN, senza auth).
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        sessione = _sessione_attiva_corrente()
        return Response(build_allarme_led_payload(sessione))


class PilotTickRuntimeStatusView(APIView):
    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def get(self, request):
        return Response(_tick_runtime_payload())


class PilotTickRuntimeControlView(APIView):
    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        action = str(request.data.get("action") or "").strip().lower()
        if action not in {"start", "stop"}:
            return Response({"error": "Azione non valida (start|stop)."}, status=status.HTTP_400_BAD_REQUEST)
        cfg = PilotRuntimeConfig.get_solo()
        cfg.tick_enabled = action == "start"
        cfg.save(update_fields=["tick_enabled", "updated_at"])
        return Response(_tick_runtime_payload(), status=status.HTTP_200_OK)


class PilotSessionHistoryView(generics.ListAPIView):
    """GET /api/pilot/session/history/  - ultimi tentativi della sessione attiva."""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]
    serializer_class = TentativoCodiceSerializer

    def get_queryset(self):
        pilota = get_pilot_from_request(self.request)
        sessione = _sessione_pilota_per_console(pilota)
        if sessione is None:
            return TentativoCodice.objects.none()
        return TentativoCodice.objects.filter(sessione=sessione).order_by("-created_at")[:30]


class PilotSessionDiarioView(APIView):
    """GET /api/pilot/session/diario/ — cronologia leggibile del volo (o sessione passata)."""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def get(self, request):
        pilota = get_pilot_from_request(request)
        sessione_id = request.query_params.get("sessione_id")
        if sessione_id:
            sessione = SessioneVolo.objects.filter(pk=sessione_id).first()
        else:
            sessione = _sessione_pilota_per_console(pilota)
        if sessione is None:
            return Response({"sessione": None, "voci": []})
        from .flight_log import riepilogo_sessione_per_pilota

        voci = VoceDiarioVolo.objects.filter(sessione=sessione).order_by("created_at")
        return Response(
            {
                "sessione": riepilogo_sessione_per_pilota(sessione),
                "voci": VoceDiarioVoloSerializer(voci, many=True).data,
            }
        )


class PilotSessionVoliView(APIView):
    """GET /api/pilot/session/voli/ — elenco voli recenti del pilota con sintesi."""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def get(self, request):
        get_pilot_from_request(request)
        from .flight_log import riepilogo_sessione_per_pilota

        qs = (
            SessioneVolo.objects.exclude(stato=SESSIONE_STATO_IDLE)
            .select_related("prefettura_partenza", "prefettura_arrivo", "pilota")
            .order_by("-ended_at", "-created_at")[:25]
        )
        return Response({"voli": [riepilogo_sessione_per_pilota(s) for s in qs]})


# ---------------------------------------------------------------------------
# 3) QR sottosistemi (guasto / ripristino) - usato dall'app principale (token DRF)
# ---------------------------------------------------------------------------


class PilotSubsystemQrActionView(APIView):
    """
    POST /api/pilot/subsystems/qr-action/
    Body: {"qr_id": "...", "personaggio_id": int, "azione": "sabota"}

    Sabotaggio esplicito (pulsante in app): richiede 0SA > 0, guasto immediato.
    La scansione QR da sola mostra solo telemetria; non applica effetti.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from pilotaggio.qr_sottosistema import sabota_sottosistema_da_qr

        qr_id = (request.data.get("qr_id") or "").strip()
        personaggio_id = request.data.get("personaggio_id")
        azione = str(request.data.get("azione") or "").strip().lower()

        if not qr_id:
            return Response({"error": "qr_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        if not personaggio_id:
            return Response(
                {"error": "personaggio_id mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if azione != "sabota":
            return Response(
                {"error": "Azione non valida: usare azione=sabota."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pg = Personaggio.objects.filter(
            pk=personaggio_id, proprietario=request.user
        ).first()
        if not pg:
            return Response(
                {"error": "Personaggio non valido per questo utente."},
                status=status.HTTP_403_FORBIDDEN,
            )
        qr = QrCode.objects.select_related("vista").filter(id=qr_id).first()
        if not qr:
            return Response(
                {"error": "QR non trovato."}, status=status.HTTP_404_NOT_FOUND
            )

        result = sabota_sottosistema_da_qr(qr_code=qr, personaggio=pg)
        if not result.get("ok"):
            return Response(
                {"error": result.get("error", "Sabotaggio non riuscito.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        out = {k: v for k, v in result.items() if k != "ok"}
        return Response(out, status=status.HTTP_200_OK)


class PilotSubsystemQrRepairView(APIView):
    """
    POST /api/pilot/subsystems/qr-repair/
    Body: {qr_id, personaggio_id, minigioco_session_id?}

    Ripara un sottosistema guasto (dopo minigioco se configurato).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from pilotaggio.qr_sottosistema import ripristina_sottosistema_da_qr

        qr_id = (request.data.get("qr_id") or "").strip()
        personaggio_id = request.data.get("personaggio_id")
        minigioco_session_id = (request.data.get("minigioco_session_id") or "").strip() or None

        if not qr_id:
            return Response({"error": "qr_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        if not personaggio_id:
            return Response(
                {"error": "personaggio_id mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pg = Personaggio.objects.filter(pk=personaggio_id, proprietario=request.user).first()
        if not pg:
            return Response(
                {"error": "Personaggio non valido per questo utente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qr = QrCode.objects.select_related("vista").filter(id=qr_id).first()
        if not qr:
            return Response({"error": "QR non trovato."}, status=status.HTTP_404_NOT_FOUND)

        componenti_scelti = request.data.get("componenti_scelti")
        if componenti_scelti is not None and not isinstance(componenti_scelti, list):
            return Response(
                {"error": "componenti_scelti deve essere una lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = ripristina_sottosistema_da_qr(
            qr_code=qr,
            personaggio=pg,
            minigioco_session_id=minigioco_session_id,
            componenti_scelti=componenti_scelti,
        )
        if not result.get("ok"):
            return Response(
                {"error": result.get("error", "Riparazione non riuscita.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        out = {k: v for k, v in result.items() if k != "ok"}
        return Response(out, status=status.HTTP_200_OK)


class PilotSubsystemQrRechargeView(APIView):
    """
    POST /api/pilot/subsystems/qr-recharge/
    Body: {qr_id, personaggio_id, componenti_scelti[]}

    Ricarica batteria (storage) o serbatoio (carburante) consumando componenti da stiva.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from pilotaggio.qr_sottosistema import ricarica_sottosistema_da_qr

        qr_id = (request.data.get("qr_id") or "").strip()
        personaggio_id = request.data.get("personaggio_id")
        if not qr_id:
            return Response({"error": "qr_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        if not personaggio_id:
            return Response(
                {"error": "personaggio_id mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pg = Personaggio.objects.filter(pk=personaggio_id, proprietario=request.user).first()
        if not pg:
            return Response(
                {"error": "Personaggio non valido per questo utente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qr = QrCode.objects.select_related("vista").filter(id=qr_id).first()
        if not qr:
            return Response({"error": "QR non trovato."}, status=status.HTTP_404_NOT_FOUND)

        componenti_scelti = request.data.get("componenti_scelti")
        if componenti_scelti is not None and not isinstance(componenti_scelti, list):
            return Response(
                {"error": "componenti_scelti deve essere una lista."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = ricarica_sottosistema_da_qr(
            qr_code=qr,
            personaggio=pg,
            componenti_scelti=componenti_scelti,
        )
        if not result.get("ok"):
            return Response(
                {"error": result.get("error", "Ricarica non riuscita.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        out = {k: v for k, v in result.items() if k != "ok"}
        return Response(out, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 4) Cataloghi pubblici (per la console pilota e per dropdown frontend)
# ---------------------------------------------------------------------------


class PilotCatalogView(APIView):
    """
    GET /api/pilot/catalog/

    Restituisce l'elenco di sottosistemi e comandi attivi per assistere il
    pilota nella visualizzazione dei codici disponibili.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def get(self, request):
        sotto = SottosistemaNave.objects.filter(attivo=True).order_by(
            "ordine_gruppo", "gruppo", "ordine", "nome", "codice"
        )
        cmd = ComandoNave.objects.filter(attivo=True).order_by("codice")
        intensita = IntensitaComando.objects.filter(attivo=True).order_by("valore")
        combinations = []
        lista_sottosistema_numero_comando = []
        for s in sotto:
            for i in intensita:
                comandi_per_slot = []
                for c in cmd:
                    combinations.append(
                        {
                            "sottosistema_codice": s.codice,
                            "sottosistema_nome": s.nome,
                            "comando_codice": c.codice,
                            "comando_nome": c.nome,
                            "intensita": i.valore,
                            "intensita_nome": i.nome or f"Intensita {i.valore}",
                            "codice": f"{s.codice}{c.codice}{i.valore}",
                        }
                    )
                    comandi_per_slot.append(
                        {
                            "comando_codice": c.codice,
                            "comando_nome": c.nome,
                        }
                    )
                lista_sottosistema_numero_comando.append(
                    {
                        "chiave": f"{s.codice}{i.valore}",
                        "sottosistema_codice": s.codice,
                        "sottosistema_nome": s.nome,
                        "numero": i.valore,
                        "comandi_disponibili": comandi_per_slot,
                    }
                )
        stati_qs = StatoAllertaPilot.objects.all().order_by("livello")
        stati_allerta = StatoAllertaPilotPublicSerializer(stati_qs, many=True).data

        return Response(
            {
                "sottosistemi": SottosistemaNaveSerializer(sotto, many=True).data,
                "comandi": ComandoNaveSerializer(cmd, many=True).data,
                "intensita": IntensitaComandoSerializer(intensita, many=True).data,
                "stati_allerta": stati_allerta,
                "lista_combinazioni_codici": combinations,
                "lista_sottosistema_numero_comando": lista_sottosistema_numero_comando,
            }
        )


class PilotPrefettureView(generics.ListAPIView):
    """Elenco prefetture per dropdown partenza/arrivo (login console pilota)."""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def list(self, request, *args, **kwargs):
        rows = []
        for p in Prefettura.objects.select_related("regione", "era").order_by(
            "era__ordine", "ordine", "nome"
        ):
            rows.append(
                {
                    "id": p.pk,
                    "nome": p.nome,
                    "regione_id": p.regione_id,
                    "regione": getattr(p.regione, "nome", "") if p.regione_id else "",
                    "era": getattr(p.era, "nome", "") if p.era_id else "",
                }
            )
        return Response(rows)


# ---------------------------------------------------------------------------
# 5) Staff CRUD (sotto /api/pilot/staff/)
# ---------------------------------------------------------------------------


class StaffSottosistemaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get_queryset(self):
        from django.db.models import BooleanField, OuterRef, Subquery
        from django.db.models.functions import Coalesce

        from personaggi.models import MinigiocoQrConfig

        qs = SottosistemaNave.objects.all().order_by(
            "ordine_gruppo", "gruppo", "ordine", "nome", "codice"
        )
        if self.action != "list":
            return qs
        cfg_sub = MinigiocoQrConfig.objects.filter(
            qr_code__vista_id=OuterRef("a_vista_id"),
        ).values("usa_default_pagina")[:1]
        return qs.annotate(
            minigioco_usa_default=Coalesce(
                Subquery(cfg_sub, output_field=BooleanField()),
                False,
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return SottosistemaNaveListSerializer
        return SottosistemaNaveSerializer

    @action(detail=True, methods=["post"], url_path="associa-a-vista")
    def associa_a_vista(self, request, pk=None):
        """Associa un A_vista esistente al sottosistema (per generare QR)."""
        sottos = self.get_object()
        a_vista_id = request.data.get("a_vista_id")
        if a_vista_id in (None, ""):
            sottos.a_vista = None
            sottos.save(update_fields=["a_vista", "updated_at"])
        else:
            av = get_object_or_404(A_vista, pk=a_vista_id)
            sottos.a_vista = av
            sottos.save(update_fields=["a_vista", "updated_at"])
        return Response(self.get_serializer(sottos).data)

    @action(detail=True, methods=["post"], url_path="associa-qr")
    def associa_qr(self, request, pk=None):
        """
        Collega un QR al sottosistema senza passare da id vista a mano.

        - Se il QR ha già una vista: il sottosistema punta a quella vista.
        - Se il QR è libero: crea un Manifesto dedicato, associa il QR al manifesto,
          poi collega il sottosistema a quella vista.
        In entrambi i casi il codice a barre resta nel modello QrCode → A_vista come da dominio.
        """
        sottos = self.get_object()
        qr_id = request.data.get("qr_id")
        if not qr_id:
            return Response(
                {"error": "qr_id richiesto"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            qr = get_object_or_404(QrCode, pk=qr_id)

            if qr.vista_id is None:
                base = f"[Pilot {sottos.codice}] {sottos.nome}".strip()
                nome_man = (base[:100]) if base else f"Pilot {sottos.codice}"
                manifest = Manifesto.objects.create(nome=nome_man, testo="")
                qr.vista = manifest
                qr.save()
                vista_target = manifest
            else:
                vista_target = qr.vista

            altro = (
                SottosistemaNave.objects.filter(a_vista_id=vista_target.pk)
                .exclude(pk=sottos.pk)
                .first()
            )
            if altro is not None:
                return Response(
                    {
                        "error": (
                            f"La vista collegata a questo QR è già usata dal sottosistema "
                            f"«{altro.codice} — {altro.nome}» (id {altro.pk})."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sottos.a_vista = vista_target
            sottos.save(update_fields=["a_vista", "updated_at"])

        return Response(self.get_serializer(sottos).data)

    @action(detail=True, methods=["get", "post"], url_path="carburante-sessione")
    def carburante_sessione(self, request, pk=None):
        """
        GET/POST carburante sulla sessione console attiva (solo sottosistema tipo serbatoio).

        POST body: { "carburante_attuale": <float> } oppure { "riempi": true }
        """
        sottos = self.get_object()
        if str(sottos.tipo or "").strip().lower() != "serbatoio":
            return Response(
                {"error": "Operazione consentita solo su sottosistemi tipo serbatoio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessione = _sessione_attiva_corrente()
        massimo = capacita_carburante_serbatoi()

        def _payload(sess: Optional[SessioneVolo]) -> dict:
            if sess is None:
                return {
                    "sessione_attiva": False,
                    "carburante_attuale": None,
                    "carburante_massimo": massimo,
                    "sessione_stato": None,
                    "pilota_nome": None,
                    "sessione_id": None,
                }
            pilota = getattr(sess, "pilota", None)
            return {
                "sessione_attiva": True,
                "carburante_attuale": float(sess.carburante_attuale or 0.0),
                "carburante_massimo": massimo,
                "sessione_stato": sess.stato,
                "pilota_nome": getattr(pilota, "nome", str(pilota)) if pilota else "",
                "sessione_id": str(sess.pk),
            }

        if request.method == "GET":
            return Response(_payload(sessione))

        if sessione is None:
            return Response(
                {"error": "Nessuna sessione console attiva (idle o in volo)."},
                status=status.HTTP_409_CONFLICT,
            )

        if request.data.get("riempi") in (True, "true", "1", 1):
            target = massimo
        else:
            raw = request.data.get("carburante_attuale")
            if raw is None:
                return Response(
                    {"error": "Specificare carburante_attuale o riempi=true."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                target = float(raw)
            except (TypeError, ValueError):
                return Response(
                    {"error": "carburante_attuale non valido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                sessione = staff_imposta_carburante_sessione(sessione, target)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out = _payload(sessione)
        out["applicato"] = True
        return Response(out, status=status.HTTP_200_OK)


class StaffComandoViewSet(viewsets.ModelViewSet):
    queryset = ComandoNave.objects.all().order_by("codice")
    serializer_class = ComandoNaveSerializer
    permission_classes = [IsAuthenticated, IsStaffOrMaster]


class StaffComandoCriticoGlobaleViewSet(viewsets.ModelViewSet):
    """Pattern globali: un codice valido che li matcha precipita la nave subito."""

    queryset = ComandoCriticoGlobale.objects.all().order_by("nome", "pattern")
    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get_serializer_class(self):
        if self.action == "list":
            return ComandoCriticoGlobaleListSerializer
        return ComandoCriticoGlobaleSerializer


class StaffIntensitaViewSet(viewsets.ModelViewSet):
    queryset = IntensitaComando.objects.all().order_by("valore")
    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get_serializer_class(self):
        if self.action == "list":
            return IntensitaComandoListSerializer
        return IntensitaComandoSerializer


class StaffEventoViewSet(viewsets.ModelViewSet):
    queryset = EventoNave.objects.all().order_by("nome")
    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get_serializer_class(self):
        if self.action == "list":
            return EventoNaveListSerializer
        return EventoNaveSerializer


class StaffSequenzaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Legacy read-only: sequenze non piu' usate nel gameplay corrente.
    """

    queryset = SequenzaVolo.objects.all().order_by("tipo", "-created_at")
    serializer_class = SequenzaVoloSerializer
    permission_classes = [IsAuthenticated, IsStaffOrMaster]


class StaffStatoAllertaViewSet(viewsets.ModelViewSet):
    """CRUD livelli DEFCON 0..6 (colori, tempi, nave abbattuta)."""

    queryset = StatoAllertaPilot.objects.all().order_by("livello")
    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get_serializer_class(self):
        if self.action == "list":
            return StatoAllertaPilotListSerializer
        return StatoAllertaPilotSerializer


class StaffSessioneListView(generics.ListAPIView):
    """Elenco sessioni di volo (lettura) per staff."""

    permission_classes = [IsAuthenticated, IsStaffOrMaster]
    serializer_class = SessioneVoloSerializer
    queryset = SessioneVolo.objects.all().order_by("-created_at")


def _build_staff_sessione_live_payload(sessione: Optional[SessioneVolo]) -> dict:
    if sessione is None:
        return {
            "sessione": None,
            "decollo_effettuato": False,
            "sessione_terminata": False,
            "eventi_attivi": [],
            "sottosistemi": [],
        }

    _ensure_runtime_subsystems(sessione)
    stati_qs = (
        StatoSottosistemaSessione.objects.filter(sessione=sessione)
        .select_related("sottosistema")
        .order_by(
            "sottosistema__ordine_gruppo",
            "sottosistema__gruppo",
            "sottosistema__ordine",
            "sottosistema__nome",
        )
    )
    pending = eventi_attivi_correnti(sessione)
    if not _sessione_ha_decollato(sessione):
        pending = []
    return {
        "sessione": SessioneVoloSerializer(sessione).data,
        "decollo_effettuato": _sessione_ha_decollato(sessione),
        "sessione_terminata": sessione.is_terminata,
        "eventi_attivi": EventoAttivoSerializer(pending, many=True).data,
        "sottosistemi": StatoSottosistemaRuntimeSerializer(stati_qs, many=True).data,
    }


class StaffSessioneLiveView(APIView):
    """
    GET /api/pilot/staff/sessione-live/
    Stato runtime della sessione attiva (volo) per pannello staff.
    """

    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get(self, request):
        sessione = _sessione_staff_operativa()
        return Response(_build_staff_sessione_live_payload(sessione))


class StaffSessioneSottosistemaAzioneView(APIView):
    """
    POST /api/pilot/staff/sessione-live/sottosistema/
    Body: { sottosistema_id, azione: guasto|ripara|ripristino }
    """

    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def post(self, request):
        sessione = _sessione_staff_operativa()
        if sessione is None:
            return Response(
                {"error": "Nessuna sessione console disponibile."},
                status=status.HTTP_409_CONFLICT,
            )

        sottosistema_id = request.data.get("sottosistema_id")
        azione = request.data.get("azione")
        if not sottosistema_id:
            return Response(
                {"error": "sottosistema_id mancante."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sottosistema = SottosistemaNave.objects.filter(
            pk=sottosistema_id, attivo=True
        ).first()
        if sottosistema is None:
            return Response(
                {"error": "Sottosistema non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with transaction.atomic():
                esito, stato = staff_azione_sottosistema_sessione(
                    sessione, sottosistema, str(azione or "")
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        sessione.refresh_from_db()
        payload = _build_staff_sessione_live_payload(sessione)
        payload["azione"] = esito
        payload["stato_aggiornato"] = StatoSottosistemaRuntimeSerializer(stato).data
        return Response(payload, status=status.HTTP_200_OK)


class StaffSessioniOrfaneView(APIView):
    """
    GET /api/pilot/staff/sessioni-orfane/
    Anteprima sessioni idle/volo duplicate (orfane) per pilota.

    POST /api/pilot/staff/sessioni-orfane/
    Chiude le orfane; resta una sessione attiva per pilota (la piu' recente).
    Body opzionale: { "pilota_id": <int> }
    """

    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get(self, request):
        pilota_id = request.query_params.get("pilota_id")
        if pilota_id is not None:
            try:
                pilota_id = int(pilota_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "pilota_id non valido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(_riepilogo_sessioni_orfane(pilota_id=pilota_id))

    def post(self, request):
        pilota_id = request.data.get("pilota_id")
        if pilota_id is not None:
            try:
                pilota_id = int(pilota_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "pilota_id non valido."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        with transaction.atomic():
            risultato = pulisci_sessioni_orfane_staff(pilota_id=pilota_id)
        risultato["sessione_live"] = _build_staff_sessione_live_payload(
            _sessione_staff_operativa()
        )
        return Response(risultato, status=status.HTTP_200_OK)


class StaffPilotRuntimeConfigView(APIView):
    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get(self, request):
        cfg = PilotRuntimeConfig.get_solo()
        return Response(PilotRuntimeConfigSerializer(cfg).data)

    def patch(self, request):
        cfg = PilotRuntimeConfig.get_solo()
        serializer = PilotRuntimeConfigSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PilotStivaView(APIView):
    """GET /api/pilot/stiva/?personaggio_id= — inventario componenti nave (read-only, richiede stat accesso)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from personaggi.models import Personaggio

        from .componenti_stiva import build_stiva_payload, mattoni_componente_qs
        from .models import PilotRuntimeConfig

        cfg = PilotRuntimeConfig.get_solo()
        sigla = (cfg.compattatore_stat_accesso_sigla or "0IN").strip()

        personaggio_id = (request.query_params.get("personaggio_id") or "").strip()
        if not request.user.is_staff:
            if not personaggio_id:
                return Response(
                    {"error": "personaggio_id richiesto."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pg = Personaggio.objects.filter(pk=personaggio_id, proprietario=request.user).first()
            if pg is None:
                return Response(
                    {"error": "Personaggio non valido per questo utente."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if int(pg.get_valore_statistica(sigla) or 0) <= 0:
                return Response(
                    {"error": f"Accesso stiva richiede {sigla} > 0 sul personaggio."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        payload = build_stiva_payload()
        payload["mattoni_catalogo"] = [
            {
                "id": str(m.pk),
                "nome": m.nome,
                "indice_componente": m.indice_componente,
                "colore_id": str(m.caratteristica_associata_id),
                "colore_nome": m.caratteristica_associata.nome if m.caratteristica_associata else "",
            }
            for m in mattoni_componente_qs()
        ]
        payload["stat_accesso_sigla"] = sigla
        return Response(payload)


class StaffPilotStivaView(APIView):
    """
    GET /api/pilot/staff/stiva/
    POST body {mattone_id, delta} — aggiunge/toglie quantità (staff).
    """

    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def get(self, request):
        from .componenti_stiva import build_stiva_payload, mattoni_componente_qs

        payload = build_stiva_payload()
        payload["mattoni_catalogo"] = [
            {
                "id": str(m.pk),
                "nome": m.nome,
                "indice_componente": m.indice_componente,
                "colore_id": str(m.caratteristica_associata_id),
                "colore_nome": m.caratteristica_associata.nome if m.caratteristica_associata else "",
            }
            for m in mattoni_componente_qs()
        ]
        return Response(payload)

    def post(self, request):
        from .componenti_stiva import staff_modifica_stiva

        mattone_id = request.data.get("mattone_id")
        delta = request.data.get("delta")
        if not mattone_id:
            return Response({"error": "mattone_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            delta_int = int(delta)
        except (TypeError, ValueError):
            return Response({"error": "delta non valido."}, status=status.HTTP_400_BAD_REQUEST)
        if delta_int == 0:
            return Response({"error": "delta non può essere zero."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = staff_modifica_stiva(mattone_id=mattone_id, delta=delta_int)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_200_OK)


class StaffCoppiaColoriComponenteViewSet(viewsets.ModelViewSet):
    """CRUD coppie colori opposti (staff)."""

    queryset = CoppiaColoriComponente.objects.select_related("colore_a", "colore_b").order_by(
        "ordine", "created_at"
    )
    serializer_class = CoppiaColoriComponenteSerializer
    permission_classes = [IsAuthenticated, IsStaffOrMaster]


class StaffAggiornaCodiciEventiView(APIView):
    """
    POST /api/pilot/staff/eventi/aggiorna-codici-da-stato/
    Body opzionale: { evento_id, dry_run, solo_attivi }
    Rigenera codice esatto, parziali e precipizio da stato sottosistemi.
    """

    permission_classes = [IsAuthenticated, IsStaffOrMaster]

    def post(self, request):
        from .evento_codici import aggiorna_codici_eventi_da_stato

        evento_id = request.data.get("evento_id")
        dry_run = bool(request.data.get("dry_run", False))
        solo_attivi = request.data.get("solo_attivi", True)
        if isinstance(solo_attivi, str):
            solo_attivi = solo_attivi.lower() not in {"0", "false", "no"}

        try:
            payload = aggiorna_codici_eventi_da_stato(
                evento_id=evento_id,
                solo_attivi=bool(solo_attivi),
                dry_run=dry_run,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_200_OK)


class PilotCompattatoreStateView(APIView):
    """GET /api/pilot/compattatore/state/"""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def get(self, request):
        from .compattatore_engine import build_compattatore_state_payload

        return Response(build_compattatore_state_payload())


class PilotCompattatoreCompressioneView(APIView):
    """POST /api/pilot/compattatore/compressione/ body {mattone_id}"""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        from .compattatore_engine import operazione_compressione

        mattone_id = request.data.get("mattone_id")
        if not mattone_id:
            return Response({"error": "mattone_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = operazione_compressione(mattone_id=str(mattone_id))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class PilotCompattatoreDecompressioneView(APIView):
    """POST /api/pilot/compattatore/decompressione/ body {mattone_id}"""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        from .compattatore_engine import operazione_decompressione

        mattone_id = request.data.get("mattone_id")
        if not mattone_id:
            return Response({"error": "mattone_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = operazione_decompressione(mattone_id=str(mattone_id))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class PilotCompattatoreRisonanzaView(APIView):
    """POST /api/pilot/compattatore/risonanza/ body {mattone_id}"""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        from .compattatore_engine import operazione_risonanza

        mattone_id = request.data.get("mattone_id")
        if not mattone_id:
            return Response({"error": "mattone_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = operazione_risonanza(mattone_id=str(mattone_id))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)


class PilotCompattatoreQuanticoView(APIView):
    """
    POST /api/pilot/compattatore/quantico/
    body { nome_oggetto? } oppure { qr_id, personaggio_id? }
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        from .compattatore_engine import operazione_compattatore_quantico

        try:
            payload = operazione_compattatore_quantico(
                nome_oggetto=request.data.get("nome_oggetto"),
                qr_id=request.data.get("qr_id"),
                personaggio_id=request.data.get("personaggio_id"),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload)
