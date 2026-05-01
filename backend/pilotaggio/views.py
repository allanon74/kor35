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

from .auth import PilotConsoleTokenAuthentication, get_pilot_from_request
from .engine import (
    durata_viaggio_secondi,
    evento_attivo_corrente,
    get_o_crea_stato_sottosistema,
    processa_codice,
    tick_sessione,
)
from .models import (
    ComandoCriticoGlobale,
    ComandoNave,
    DEFCON_MAX,
    EVENTO_ESITO_PENDING,
    EventoNave,
    IntensitaComando,
    PilotConsoleToken,
    PilotConsoleLoginTicket,
    SESSIONE_STATO_ATTERRAGGIO,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_DECOLLO,
    SESSIONE_STATO_IDLE,
    SESSIONE_STATO_VOLO,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoAllertaPilot,
    StatoSottosistemaSessione,
    TentativoCodice,
)
from .permissions import IsPilotConsole, IsStaffUser
from .serializers import (
    ComandoCriticoGlobaleSerializer,
    ComandoNaveSerializer,
    EventoAttivoSerializer,
    EventoNaveSerializer,
    IntensitaComandoSerializer,
    PilotConsoleTokenSerializer,
    SequenzaVoloSerializer,
    SessioneVoloSerializer,
    SottosistemaNaveSerializer,
    StatoAllertaPilotPublicSerializer,
    StatoAllertaPilotSerializer,
    StatoSottosistemaRuntimeSerializer,
    TentativoCodiceSerializer,
)


SIGLA_PILOTAGGIO = "0PI"
SIGLA_SABOTAGGIO = "0SA"
SIGLA_RIPARAZIONE = "0RI"


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
    """
    Singleton logico della console: se piu' sessioni sono attive, prende quella
    piu' recente non terminata. Per console singola Raspberry e' coerente.
    """
    return (
        SessioneVolo.objects.exclude(stato__in=["arrivata", "crashed"])
        .order_by("-created_at")
        .first()
    )


def _request_prefers_html(request) -> bool:
    accept = str(request.headers.get("Accept", "")).lower()
    if "application/json" in accept:
        return False
    return "text/html" in accept


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
        return Response({"enabled": bool(getattr(settings, "PILOT_CONSOLE_ENABLED", False))})


class PilotConsoleTicketCreateView(APIView):
    """
    Crea un ticket temporaneo da mostrare come QR in console.
    """

    authentication_classes: list = []
    permission_classes: list = [permissions.AllowAny]

    def post(self, request):
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
        PilotConsoleToken.objects.filter(pk=token.pk).update(
            revocato_at=timezone.now()
        )
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# 2) Runtime sessione di volo
# ---------------------------------------------------------------------------


def _build_state_payload(sessione: SessioneVolo, pilota: Personaggio) -> dict:
    """Stato runtime completo per la console pilota."""
    pending = evento_attivo_corrente(sessione) if sessione else None

    sub_serializer = StatoSottosistemaRuntimeSerializer(
        StatoSottosistemaSessione.objects.filter(sessione=sessione).select_related(
            "sottosistema"
        )
        if sessione
        else [],
        many=True,
    )

    decollo_seq = (
        SequenzaVolo.objects.filter(tipo="decollo", attiva=True)
        .order_by("-created_at")
        .first()
    )
    atterraggio_seq = (
        SequenzaVolo.objects.filter(tipo="atterraggio", attiva=True)
        .order_by("-created_at")
        .first()
    )

    stati_qs = StatoAllertaPilot.objects.all().order_by("livello")
    stati_allerta = StatoAllertaPilotPublicSerializer(stati_qs, many=True).data

    payload = {
        "pilota": {
            "id": pilota.pk,
            "nome": getattr(pilota, "nome", str(pilota)),
        },
        "sessione": SessioneVoloSerializer(sessione).data if sessione else None,
        "evento_attivo": EventoAttivoSerializer(pending).data if pending else None,
        "sottosistemi": sub_serializer.data,
        "stati_allerta": stati_allerta,
        "sequenze": {
            "decollo": {
                "presente": bool(decollo_seq),
                "lunghezza": len(decollo_seq.codici) if decollo_seq else 0,
                "idx_corrente": sessione.decollo_idx if sessione else 0,
            },
            "atterraggio": {
                "presente": bool(atterraggio_seq),
                "lunghezza": len(atterraggio_seq.codici) if atterraggio_seq else 0,
                "idx_corrente": sessione.atterraggio_idx if sessione else 0,
            },
        },
        "defcon_max": DEFCON_MAX,
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
        pilota = get_pilot_from_request(request)
        sessione = (
            SessioneVolo.objects.filter(pilota=pilota)
            .exclude(stato__in=["arrivata", "crashed"])
            .order_by("-created_at")
            .first()
        )
        if sessione is not None:
            tick_sessione(sessione)
            sessione.refresh_from_db()
        return Response(_build_state_payload(sessione, pilota))


class PilotSessionStartView(APIView):
    """
    POST /api/pilot/session/start/
    Body: {"prefettura_partenza_id": int, "prefettura_arrivo_id": int}

    A nave ferma. Calcola durata viaggio e mette la sessione in fase di decollo
    (richiede sequenza_decollo prima del volo vero).
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        partenza_id = request.data.get("prefettura_partenza_id")
        arrivo_id = request.data.get("prefettura_arrivo_id")
        partenza = Prefettura.objects.filter(pk=partenza_id).first() if partenza_id else None
        arrivo = Prefettura.objects.filter(pk=arrivo_id).first() if arrivo_id else None
        if partenza is None or arrivo is None:
            return Response(
                {"error": "Prefetture di partenza e arrivo richieste."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attiva = (
            SessioneVolo.objects.filter(pilota=pilota)
            .exclude(stato__in=["arrivata", "crashed"])
            .order_by("-created_at")
            .first()
        )
        if attiva is not None and attiva.stato != SESSIONE_STATO_IDLE:
            return Response(
                {"error": "Esiste gia' una sessione in corso."},
                status=status.HTTP_409_CONFLICT,
            )

        durata = durata_viaggio_secondi(partenza, arrivo, defcon_iniziale=0)

        with transaction.atomic():
            if attiva is None:
                attiva = SessioneVolo.objects.create(
                    pilota=pilota,
                    prefettura_partenza=partenza,
                    prefettura_arrivo=arrivo,
                    stato=SESSIONE_STATO_DECOLLO,
                    durata_pianificata_secondi=durata,
                )
            else:
                attiva.prefettura_partenza = partenza
                attiva.prefettura_arrivo = arrivo
                attiva.stato = SESSIONE_STATO_DECOLLO
                attiva.durata_pianificata_secondi = durata
                attiva.decollo_idx = 0
                attiva.atterraggio_idx = 0
                attiva.save()
            attiva.started_at = timezone.now()
            attiva.save(update_fields=["started_at", "updated_at"])

        return Response(_build_state_payload(attiva, pilota))


class PilotSessionCommandView(APIView):
    """
    POST /api/pilot/session/command/
    Body: {"codice": "ABC"}

    Unico endpoint che accetta input dalla tastiera della console.
    """

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]

    def post(self, request):
        pilota = get_pilot_from_request(request)
        codice = (request.data.get("codice") or "").strip().upper()
        sessione = (
            SessioneVolo.objects.filter(pilota=pilota)
            .exclude(stato__in=["arrivata", "crashed"])
            .order_by("-created_at")
            .first()
        )
        if sessione is None:
            return Response(
                {"error": "Nessuna sessione attiva."}, status=status.HTTP_400_BAD_REQUEST
            )
        if sessione.stato == SESSIONE_STATO_IDLE:
            return Response(
                {"error": "Nave a terra: avvia un viaggio prima di inserire codici."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valutazione = processa_codice(sessione, codice)
        sessione.refresh_from_db()
        tick_sessione(sessione)
        sessione.refresh_from_db()

        body = _build_state_payload(sessione, pilota)
        body["valutazione"] = {
            "esito": valutazione.esito,
            "delta_defcon": valutazione.delta_defcon,
            "nuovo_defcon": valutazione.nuovo_defcon,
            "descrizione": valutazione.descrizione,
            "sequenza_avanzata": valutazione.sequenza_avanzata,
            "sequenza_completa": valutazione.sequenza_completa,
        }
        return Response(body)


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
        sessione = (
            SessioneVolo.objects.filter(pilota=pilota)
            .exclude(stato__in=["arrivata", "crashed"])
            .order_by("-created_at")
            .first()
        )
        if sessione is None:
            return Response({"status": "no_session"}, status=status.HTTP_200_OK)
        sessione.stato = SESSIONE_STATO_CRASHED
        sessione.ended_at = timezone.now()
        sessione.save(update_fields=["stato", "ended_at", "updated_at"])
        return Response(_build_state_payload(sessione, pilota))


class PilotSessionHistoryView(generics.ListAPIView):
    """GET /api/pilot/session/history/  - ultimi tentativi della sessione attiva."""

    authentication_classes = [PilotConsoleTokenAuthentication]
    permission_classes = [IsPilotConsole]
    serializer_class = TentativoCodiceSerializer

    def get_queryset(self):
        pilota = get_pilot_from_request(self.request)
        sessione = (
            SessioneVolo.objects.filter(pilota=pilota)
            .order_by("-created_at")
            .first()
        )
        if sessione is None:
            return TentativoCodice.objects.none()
        return TentativoCodice.objects.filter(sessione=sessione).order_by("-created_at")[:30]


# ---------------------------------------------------------------------------
# 3) QR sottosistemi (guasto / ripristino) - usato dall'app principale (token DRF)
# ---------------------------------------------------------------------------


class PilotSubsystemQrActionView(APIView):
    """
    POST /api/pilot/subsystems/qr-action/
    Body: {"qr_id": "...", "personaggio_id": int}

    Risolve il QR -> Sottosistema. Verifica statistiche del PG che scansiona:
    - 0SA >= 1  -> guasto immediato (online=False).
    - 0RI >= 1  -> ripristino programmato dopo `durata_ripristino_secondi`.
    Nessuna delle due -> 403.

    Si applica alla sessione attiva piu' recente; se non c'e' alcuna sessione
    in corso restituisce 409.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        qr_id = (request.data.get("qr_id") or "").strip()
        personaggio_id = request.data.get("personaggio_id")
        if not qr_id:
            return Response({"error": "qr_id mancante."}, status=status.HTTP_400_BAD_REQUEST)
        if not personaggio_id:
            return Response(
                {"error": "personaggio_id mancante."},
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
        sottosistema = _sottosistema_da_qr(qr)
        if not sottosistema:
            return Response(
                {"error": "QR non collegato a un sottosistema nave."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sessione = _sessione_attiva_corrente()
        if sessione is None:
            return Response(
                {
                    "error": "Nessuna sessione di volo attiva.",
                    "sottosistema": SottosistemaNaveSerializer(sottosistema).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        v_sa = int(pg.get_valore_statistica(SIGLA_SABOTAGGIO) or 0)
        v_ri = int(pg.get_valore_statistica(SIGLA_RIPARAZIONE) or 0)

        if v_sa >= 1:
            azione = "guasto"
        elif v_ri >= 1:
            azione = "ripristino"
        else:
            return Response(
                {
                    "error": (
                        f"Servono {SIGLA_SABOTAGGIO} >= 1 (guasto) o "
                        f"{SIGLA_RIPARAZIONE} >= 1 (ripristino)."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            stato = get_o_crea_stato_sottosistema(sessione, sottosistema)
            now = timezone.now()
            if azione == "guasto":
                stato.online = False
                stato.guasto_at = now
                stato.recovery_at = None
                stato.save(
                    update_fields=["online", "guasto_at", "recovery_at", "updated_at"]
                )
            else:
                stato.recovery_at = now + timedelta(
                    seconds=int(sottosistema.durata_ripristino_secondi or 60)
                )
                stato.save(update_fields=["recovery_at", "updated_at"])

        return Response(
            {
                "azione": azione,
                "sottosistema": SottosistemaNaveSerializer(sottosistema).data,
                "stato": StatoSottosistemaRuntimeSerializer(stato).data,
                "sessione_id": str(sessione.pk),
            },
            status=status.HTTP_200_OK,
        )


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
        sotto = SottosistemaNave.objects.filter(attivo=True).order_by("codice")
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
    queryset = SottosistemaNave.objects.all().order_by("codice")
    serializer_class = SottosistemaNaveSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]

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


class StaffComandoViewSet(viewsets.ModelViewSet):
    queryset = ComandoNave.objects.all().order_by("codice")
    serializer_class = ComandoNaveSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class StaffComandoCriticoGlobaleViewSet(viewsets.ModelViewSet):
    """Pattern globali: un codice valido che li matcha precipita la nave subito."""

    queryset = ComandoCriticoGlobale.objects.all().order_by("nome", "pattern")
    serializer_class = ComandoCriticoGlobaleSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class StaffIntensitaViewSet(viewsets.ModelViewSet):
    queryset = IntensitaComando.objects.all().order_by("valore")
    serializer_class = IntensitaComandoSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class StaffEventoViewSet(viewsets.ModelViewSet):
    queryset = EventoNave.objects.all().order_by("nome")
    serializer_class = EventoNaveSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class StaffSequenzaViewSet(viewsets.ModelViewSet):
    queryset = SequenzaVolo.objects.all().order_by("tipo", "-created_at")
    serializer_class = SequenzaVoloSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class StaffStatoAllertaViewSet(viewsets.ModelViewSet):
    """CRUD livelli DEFCON 0..6 (colori, tempi, nave abbattuta)."""

    queryset = StatoAllertaPilot.objects.all().order_by("livello")
    serializer_class = StatoAllertaPilotSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class StaffSessioneListView(generics.ListAPIView):
    """Elenco sessioni di volo (lettura) per staff."""

    permission_classes = [IsAuthenticated, IsStaffUser]
    serializer_class = SessioneVoloSerializer
    queryset = SessioneVolo.objects.all().order_by("-created_at")
