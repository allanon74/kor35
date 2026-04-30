"""
API iscrizione eventi tramite PayPal (start page / giocatore).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from personaggi.models import (
    ArcanaSSOIdentity,
    Campagna,
    CampagnaUtente,
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    Personaggio,
)
from personaggi.sso import ArcanaSSOPasswordStatusView

from .models import Evento, IscrizioneEventoPagamento, PayPalImpostazioniGlobali
from .paypal_api import format_euro_amount, paypal_capture_order, paypal_create_order, paypal_get_access_token

logger = logging.getLogger(__name__)


def _default_main_campaign():
    return Campagna.objects.filter(slug="kor35").first() or Campagna.objects.filter(is_default=True).first()


def _is_master_or_head_main_campaign(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    c = _default_main_campaign()
    if not c:
        return False
    row = CampagnaUtente.objects.filter(user=user, campagna=c, attivo=True).first()
    if not row:
        return False
    return row.ruolo in (CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def _paypal_sandbox_for_user_event(user, evento: Evento, paypal_row: PayPalImpostazioniGlobali) -> bool:
    if evento.iscrizione_test_attiva and _is_master_or_head_main_campaign(user):
        return True
    return bool(paypal_row.use_sandbox)


def _paypal_client_id_secret(sandbox: bool, paypal_row: PayPalImpostazioniGlobali) -> tuple[str, str]:
    if sandbox:
        return (paypal_row.sandbox_client_id or "").strip(), (paypal_row.sandbox_client_secret or "").strip()
    return (paypal_row.live_client_id or "").strip(), (paypal_row.live_client_secret or "").strip()


def _user_registration_checks(user):
    identity = ArcanaSSOIdentity.objects.filter(user=user).first()
    is_arcana = bool(identity)
    ad_status = ArcanaSSOPasswordStatusView._compute_ad_status(identity)
    arcana_compliant = is_arcana and ad_status.get("code") == "compliant"
    has_local_password = ArcanaSSOIdentity.objects.filter(
        user=user, local_password_configured=True
    ).exists()

    main = _default_main_campaign()
    alive_main_pcs = 0
    if main:
        alive_main_pcs = Personaggio.objects.filter(
            proprietario=user,
            campagna=main,
            data_morte__isnull=True,
            tipologia__giocante=True,
        ).count()

    return {
        "is_arcana_user": is_arcana,
        "arcana_compliant": arcana_compliant,
        "has_local_password": has_local_password,
        "alive_main_campaign_pc_count": alive_main_pcs,
        "default_campaign_id": str(main.id) if main else None,
        "ad_status": ad_status,
    }


def _blocking_messages(checks: dict) -> list[str]:
    msgs = []
    if not checks["is_arcana_user"]:
        msgs.append("Accesso con account Arcana Domine richiesto.")
    elif not checks["arcana_compliant"]:
        msgs.append("Retta annuale Arcana Domine non risulta in regola (ruolo «registrato» o assente).")
    if checks["is_arcana_user"] and not checks["has_local_password"]:
        msgs.append("Imposta la password locale dell'app KOR35.")
    if checks["alive_main_campaign_pc_count"] < 1:
        msgs.append("Serve almeno un personaggio vivo nella campagna principale.")
    return msgs


def _events_in_registration_window(now):
    return (
        Evento.objects.filter(
            iscrizione_apertura__isnull=False,
            iscrizione_chiusura__isnull=False,
            iscrizione_apertura__lte=now,
            iscrizione_chiusura__gte=now,
        )
        .filter(iscrizione_costo_euro__gt=0)
        .order_by("data_inizio", "id")
    )


def _already_registered_row(user, evento: Evento):
    row = (
        evento.partecipanti.filter(proprietario=user)
        .order_by("nome")
        .first()
    )
    if row:
        return {"personaggio_id": row.id, "personaggio_nome": row.nome}

    paid = (
        IscrizioneEventoPagamento.objects.filter(
            evento=evento,
            utente=user,
            stato=IscrizioneEventoPagamento.Stato.CAPTURED,
        )
        .select_related("personaggio")
        .order_by("-created_at")
        .first()
    )
    if paid and paid.personaggio:
        return {"personaggio_id": paid.personaggio_id, "personaggio_nome": paid.personaggio.nome}
    return None


def _has_any_character_registered(user, evento: Evento) -> bool:
    if evento.partecipanti.filter(proprietario=user).exists():
        return True
    return IscrizioneEventoPagamento.objects.filter(
        evento=evento,
        utente=user,
        stato=IscrizioneEventoPagamento.Stato.CAPTURED,
    ).exists()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def iscrizioni_evento_eligibility(request):
    """
    Elenco eventi con iscrizione aperta + stato requisiti utente + meta PayPal SDK.
    """
    now = timezone.now()
    paypal_row = PayPalImpostazioniGlobali.get_solo()
    checks = _user_registration_checks(request.user)
    blocking = _blocking_messages(checks)
    all_ok = len(blocking) == 0
    is_staff_main = _is_master_or_head_main_campaign(request.user)

    events_payload = []
    for ev in _events_in_registration_window(now):
        if ev.iscrizione_test_attiva and not is_staff_main:
            continue

        registered = _already_registered_row(request.user, ev)
        sandbox = _paypal_sandbox_for_user_event(request.user, ev, paypal_row)
        cid, sec = _paypal_client_id_secret(sandbox, paypal_row)
        paypal_ready = bool(cid and sec)

        row = {
            "id": ev.id,
            "titolo": ev.titolo,
            "costo_euro": str(ev.iscrizione_costo_euro),
            "is_test": bool(ev.iscrizione_test_attiva),
            "already_registered": registered,
            "paypal_uses_sandbox": sandbox,
            "paypal_client_id": cid if paypal_ready else "",
            "paypal_ready": paypal_ready,
            "paypal_show_card": bool(paypal_row.mostra_pulsante_carta),
            "paypal_show_mybank": bool(paypal_row.mostra_pulsante_mybank),
        }
        if registered:
            row["cta_kind"] = "registered"
            row["blocking_reasons"] = []
        elif not all_ok:
            row["cta_kind"] = "blocked"
            row["blocking_reasons"] = blocking
        else:
            row["cta_kind"] = "subscribe"
            row["blocking_reasons"] = []

        events_payload.append(row)

    return Response(
        {
            "checks": checks,
            "blocking_reasons_global": blocking,
            "all_requirements_ok": all_ok,
            "is_master_head_main_campaign": is_staff_main,
            "events": events_payload,
            "currency": "EUR",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def iscrizioni_evento_crea_ordine(request):
    """
    Crea ordine PayPal e record PENDING (personaggio scelto dal giocatore).
    Body: { "evento_id": <int>, "personaggio_id": <int> }
    """
    paypal_row = PayPalImpostazioniGlobali.get_solo()
    try:
        evento_id = int(request.data.get("evento_id"))
        personaggio_id = int(request.data.get("personaggio_id"))
    except (TypeError, ValueError):
        return Response({"error": "evento_id e personaggio_id richiesti"}, status=status.HTTP_400_BAD_REQUEST)

    evento = Evento.objects.filter(id=evento_id).first()
    if not evento:
        return Response({"error": "Evento non trovato"}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    if not (
        evento.iscrizione_apertura
        and evento.iscrizione_chiusura
        and evento.iscrizione_apertura <= now <= evento.iscrizione_chiusura
    ):
        return Response({"error": "Iscrizioni non aperte per questo evento"}, status=status.HTTP_400_BAD_REQUEST)

    if evento.iscrizione_costo_euro is None or evento.iscrizione_costo_euro <= 0:
        return Response({"error": "Costo iscrizione non configurato"}, status=status.HTTP_400_BAD_REQUEST)

    if evento.iscrizione_test_attiva and not _is_master_or_head_main_campaign(request.user):
        return Response({"error": "Iscrizione test riservata allo staff campagna principale"}, status=status.HTTP_403_FORBIDDEN)

    checks = _user_registration_checks(request.user)
    if _blocking_messages(checks):
        return Response({"error": "Requisiti iscrizione non soddisfatti"}, status=status.HTTP_403_FORBIDDEN)

    main = _default_main_campaign()
    if not main:
        return Response({"error": "Campagna principale non configurata"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    pg = (
        Personaggio.objects.filter(
            id=personaggio_id,
            proprietario=request.user,
            campagna=main,
            data_morte__isnull=True,
            tipologia__giocante=True,
        )
        .select_related("tipologia")
        .first()
    )
    if not pg:
        return Response({"error": "Personaggio non valido o non ammesso"}, status=status.HTTP_400_BAD_REQUEST)

    if _has_any_character_registered(request.user, evento):
        return Response({"error": "Hai già un personaggio iscritto a questo evento"}, status=status.HTTP_409_CONFLICT)

    if evento.partecipanti.filter(id=pg.id).exists():
        return Response({"error": "Personaggio già iscritto a questo evento"}, status=status.HTTP_409_CONFLICT)

    sandbox = _paypal_sandbox_for_user_event(request.user, evento, paypal_row)
    client_id, client_secret = _paypal_client_id_secret(sandbox, paypal_row)
    if not client_id or not client_secret:
        return Response({"error": "PayPal non configurato (client id / secret mancanti)"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    value_str = format_euro_amount(Decimal(evento.iscrizione_costo_euro))
    desc = f"Iscrizione {evento.titolo}"[:120]
    custom_id = f"evt{evento.id}-pg{pg.id}-u{request.user.id}"[:120]

    try:
        token = paypal_get_access_token(client_id=client_id, client_secret=client_secret, sandbox=sandbox)
        po = paypal_create_order(
            access_token=token,
            sandbox=sandbox,
            currency_code="EUR",
            value_str=value_str,
            description=desc,
            custom_id=custom_id,
        )
    except Exception as exc:
        logger.exception("PayPal create order failed")
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    order_id = po.get("id")
    if not order_id:
        return Response({"error": "PayPal non ha restituito id ordine"}, status=status.HTTP_502_BAD_GATEWAY)

    IscrizioneEventoPagamento.objects.create(
        evento=evento,
        personaggio=pg,
        utente=request.user,
        paypal_order_id=str(order_id),
        stato=IscrizioneEventoPagamento.Stato.PENDING,
        importo_euro=evento.iscrizione_costo_euro,
        sandbox_usato=sandbox,
    )

    return Response(
        {
            "paypal_order_id": str(order_id),
            "sandbox": sandbox,
        },
        status=status.HTTP_201_CREATED,
    )


def _extract_capture_id(capture_json: dict) -> str:
    try:
        units = capture_json.get("purchase_units") or []
        if not units:
            return ""
        payments = (units[0] or {}).get("payments") or {}
        captures = payments.get("captures") or []
        if not captures:
            return ""
        return str((captures[0] or {}).get("id") or "")
    except Exception:
        return ""


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def iscrizioni_evento_annulla(request):
    """
    Marca un tentativo ordine come annullato (es. utente chiude o annulla nel popup PayPal).
    Body: { "paypal_order_id": "..." }
    """
    order_id = str(request.data.get("paypal_order_id") or "").strip()
    if not order_id:
        return Response({"error": "paypal_order_id richiesto"}, status=status.HTTP_400_BAD_REQUEST)

    row = IscrizioneEventoPagamento.objects.filter(paypal_order_id=order_id, utente=request.user).first()
    if not row:
        return Response({"error": "Ordine non trovato"}, status=status.HTTP_404_NOT_FOUND)

    if row.stato == IscrizioneEventoPagamento.Stato.CAPTURED:
        return Response({"status": "already_captured"}, status=status.HTTP_200_OK)

    if row.stato != IscrizioneEventoPagamento.Stato.CANCELLED:
        row.stato = IscrizioneEventoPagamento.Stato.CANCELLED
        row.ultimo_errore = "Pagamento annullato dall'utente"
        row.save(update_fields=["stato", "ultimo_errore", "updated_at"])

    return Response({"status": "cancelled"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def iscrizioni_evento_cattura(request):
    """
    Cattura pagamento PayPal e aggiunge il PG ai partecipanti dell'evento.
    Body: { "paypal_order_id": "..." }
    """
    order_id = str(request.data.get("paypal_order_id") or "").strip()
    if not order_id:
        return Response({"error": "paypal_order_id richiesto"}, status=status.HTTP_400_BAD_REQUEST)

    row = IscrizioneEventoPagamento.objects.filter(
        paypal_order_id=order_id,
        utente=request.user,
    ).first()
    if not row:
        return Response({"error": "Ordine non trovato"}, status=status.HTTP_404_NOT_FOUND)

    if row.stato == IscrizioneEventoPagamento.Stato.CAPTURED:
        return Response({"status": "already_captured", "message": "Pagamento già registrato."}, status=status.HTTP_200_OK)

    if row.stato != IscrizioneEventoPagamento.Stato.PENDING:
        return Response({"error": "Ordine non in stato atteso"}, status=status.HTTP_400_BAD_REQUEST)

    paypal_row = PayPalImpostazioniGlobali.get_solo()
    sandbox = bool(row.sandbox_usato)
    client_id, client_secret = _paypal_client_id_secret(sandbox, paypal_row)
    if not client_id or not client_secret:
        return Response({"error": "PayPal non configurato"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    try:
        token = paypal_get_access_token(client_id=client_id, client_secret=client_secret, sandbox=sandbox)
        cap = paypal_capture_order(access_token=token, sandbox=sandbox, order_id=order_id)
    except Exception as exc:
        logger.exception("PayPal capture failed")
        row.stato = IscrizioneEventoPagamento.Stato.FAILED
        row.ultimo_errore = str(exc)[:2000]
        row.save(update_fields=["stato", "ultimo_errore", "updated_at"])
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    st = str(cap.get("status") or "").upper()
    if st != "COMPLETED":
        row.stato = IscrizioneEventoPagamento.Stato.FAILED
        row.ultimo_errore = f"Stato PayPal inatteso: {st}"
        row.save(update_fields=["stato", "ultimo_errore", "updated_at"])
        return Response({"error": row.ultimo_errore}, status=status.HTTP_400_BAD_REQUEST)

    capture_id = _extract_capture_id(cap)

    try:
        with transaction.atomic():
            row_locked = (
                IscrizioneEventoPagamento.objects.select_for_update()
                .filter(pk=row.pk, stato=IscrizioneEventoPagamento.Stato.PENDING)
                .first()
            )
            if not row_locked:
                return Response({"status": "already_captured"}, status=status.HTTP_200_OK)

            ev = Evento.objects.select_for_update().get(pk=row_locked.evento_id)
            other_registered = ev.partecipanti.filter(proprietario=row_locked.utente, tipologia__giocante=True).exclude(id=row_locked.personaggio_id).exists()
            if other_registered:
                row_locked.stato = IscrizioneEventoPagamento.Stato.FAILED
                row_locked.ultimo_errore = "Esiste già un altro tuo personaggio iscritto a questo evento."
                row_locked.save(update_fields=["stato", "ultimo_errore", "updated_at"])
                return Response({"error": row_locked.ultimo_errore}, status=status.HTTP_409_CONFLICT)

            if not ev.partecipanti.filter(id=row_locked.personaggio_id).exists():
                ev.partecipanti.add(row_locked.personaggio_id)
            row_locked.paypal_capture_id = capture_id
            row_locked.stato = IscrizioneEventoPagamento.Stato.CAPTURED
            row_locked.ultimo_errore = ""
            row_locked.save(update_fields=["paypal_capture_id", "stato", "ultimo_errore", "updated_at"])
    except Exception as exc:
        logger.exception("DB capture finalize failed")
        return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(
        {
            "status": "ok",
            "evento_id": row.evento_id,
            "personaggio_id": row.personaggio_id,
        },
        status=status.HTTP_200_OK,
    )
