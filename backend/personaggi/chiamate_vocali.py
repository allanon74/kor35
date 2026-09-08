"""
Chiamate vocali in-app (WebRTC). Segnalazione via Channels; media peer-to-peer / TURN.

Sessione locale al nodo: non sincronizzata master↔edge.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import timedelta
from typing import Any, Iterable

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db.models import Q
from django.http.request import split_domain_port
from django.utils import timezone
from django.contrib.auth.models import User

from personaggi.models import (
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
    CampagnaUtente,
    ChiamataVocale,
    Personaggio,
)
from personaggi.ws_auth import user_notifications_group

RING_TIMEOUT_SECONDS = 45
VOCE_USER_PREFIX = "voce_user_"


def voce_user_group(user_id: int) -> str:
    return f"{VOCE_USER_PREFIX}{int(user_id)}"


def turn_rest_credentials(*, user=None, now=None) -> tuple[str, str] | None:
    """Credenziali TURN temporanee (draft-uberti-behave-turn-rest / coturn --use-auth-secret)."""
    secret = str(getattr(settings, "TURN_AUTH_SECRET", "") or "").strip()
    if not secret:
        return None
    ttl = int(getattr(settings, "TURN_CREDENTIAL_TTL", 28800) or 28800)
    expiry = int((now or timezone.now()).timestamp()) + max(60, ttl)
    uid = getattr(user, "pk", None)
    username = f"{expiry}:{uid}" if uid is not None else str(expiry)
    digest = hmac.new(secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
    credential = base64.b64encode(digest).decode("ascii")
    return username, credential


def ice_servers(request=None) -> list[dict]:
    """ICE servers da env (STUN + TURN).

    Se TURN_RELAY_ENABLED e TURN_AUTO_FROM_HOST, il TURN è l'host da cui il
    client ha aperto l'app (LAN evento, www.kor35.it, localhost).
    Con TURN_AUTH_SECRET (prod) le credenziali sono HMAC a tempo.
    """
    servers: list[dict] = []
    stun = list(getattr(settings, "STUN_URLS", None) or [])
    if not stun:
        stun = ["stun:stun.l.google.com:19302"]
    for url in stun:
        url = str(url).strip()
        if url:
            servers.append({"urls": url})
    turn_urls = [str(u).strip() for u in (getattr(settings, "TURN_URLS", None) or []) if str(u).strip()]
    relay_on = bool(getattr(settings, "TURN_RELAY_ENABLED", False))
    auto_host = bool(getattr(settings, "TURN_AUTO_FROM_HOST", True))
    if not turn_urls and relay_on and auto_host and request is not None:
        host = (split_domain_port(request.get_host())[0] or "").strip()
        if host:
            port = int(getattr(settings, "TURN_PORT", 3478) or 3478)
            turn_urls = [
                f"turn:{host}:{port}?transport=udp",
                f"turn:{host}:{port}?transport=tcp",
            ]
    hmac_creds = turn_rest_credentials(user=getattr(request, "user", None) if request else None)
    if hmac_creds:
        user, cred = hmac_creds
    else:
        user = str(getattr(settings, "TURN_USERNAME", "") or "").strip()
        cred = str(getattr(settings, "TURN_CREDENTIAL", "") or "").strip()
    for url in turn_urls:
        entry: dict[str, Any] = {"urls": url}
        if user:
            entry["username"] = user
            entry["credential"] = cred
        servers.append(entry)
    return servers


def chiamate_vocali_abilitate() -> bool:
    return bool(getattr(settings, "CHIAMATE_VOCALI_ENABLED", True))


def user_is_campaign_staff(user, campagna) -> bool:
    if not user or not campagna:
        return False
    if user.is_superuser or user.is_staff:
        return True
    ruolo = (
        CampagnaUtente.objects.filter(user=user, campagna=campagna, attivo=True)
        .values_list("ruolo", flat=True)
        .first()
    )
    return ruolo in (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def staff_user_ids(campagna) -> list[int]:
    if not campagna:
        return []
    ids = list(
        CampagnaUtente.objects.filter(
            campagna=campagna,
            attivo=True,
            ruolo__in=(CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER),
        ).values_list("user_id", flat=True)
    )
    extra = list(
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(is_staff=True))
        .values_list("id", flat=True)
    )
    return sorted({i for i in ids + extra if i})


def scadi_chiamate_vecchie() -> int:
    cutoff = timezone.now() - timedelta(seconds=RING_TIMEOUT_SECONDS + 5)
    qs = ChiamataVocale.objects.filter(
        stato=ChiamataVocale.STATO_RINGING,
        created_at__lt=cutoff,
    )
    n = 0
    for call in qs:
        call.stato = ChiamataVocale.STATO_PERSA
        call.closed_at = timezone.now()
        call.save(update_fields=["stato", "closed_at", "updated_at"])
        _notifica_parti(call, "VOCE_PERSA")
        n += 1
    return n


def user_ha_chiamata_attiva(user: User) -> ChiamataVocale | None:
    if not user:
        return None
    attivi = (ChiamataVocale.STATO_RINGING, ChiamataVocale.STATO_IN_CORSO)
    return (
        ChiamataVocale.objects.filter(stato__in=attivi)
        .filter(
            Q(chiamante__proprietario=user)
            | Q(chiamato__proprietario=user)
            | Q(accettata_da=user)
        )
        .select_related("chiamante", "chiamato", "campagna", "accettata_da")
        .order_by("-created_at")
        .first()
    )


def serializza_chiamata(call: ChiamataVocale, user=None) -> dict:
    ruolo = None
    if user:
        if call.chiamante.proprietario_id == user.id:
            ruolo = "caller"
        elif call.verso_staff and user_is_campaign_staff(user, call.campagna):
            ruolo = "callee"
        elif call.chiamato_id and call.chiamato.proprietario_id == user.id:
            ruolo = "callee"
    chiamato = None
    if call.chiamato_id:
        chiamato = {"id": call.chiamato_id, "nome": call.chiamato.nome}
    elif call.verso_staff:
        chiamato = {"id": None, "nome": "Staff"}
    return {
        "id": str(call.id),
        "stato": call.stato,
        "verso_staff": call.verso_staff,
        "chiamante": {"id": call.chiamante_id, "nome": call.chiamante.nome},
        "chiamato": chiamato,
        "accettata_da_username": call.accettata_da.username if call.accettata_da_id else None,
        "ruolo": ruolo,
        "created_at": call.created_at.isoformat() if call.created_at else None,
    }


def _destinatari_user_ids(call: ChiamataVocale, *, extra: Iterable[int] | None = None) -> list[int]:
    ids = set()
    if call.chiamante.proprietario_id:
        ids.add(call.chiamante.proprietario_id)
    if call.chiamato_id and call.chiamato.proprietario_id:
        ids.add(call.chiamato.proprietario_id)
    if call.accettata_da_id:
        ids.add(call.accettata_da_id)
    if call.verso_staff and call.stato == ChiamataVocale.STATO_RINGING:
        ids.update(staff_user_ids(call.campagna))
    if extra:
        ids.update(int(i) for i in extra if i)
    return sorted(ids)


def _ws_payload(action: str, call: ChiamataVocale, extra: dict | None = None) -> dict:
    payload = {
        "action": action,
        "call_id": str(call.id),
        "stato": call.stato,
        "verso_staff": call.verso_staff,
        "chiamante_id": call.chiamante_id,
        "chiamante_nome": call.chiamante.nome,
        "chiamato_id": call.chiamato_id,
        "chiamato_nome": call.chiamato.nome if call.chiamato_id else ("Staff" if call.verso_staff else None),
        "accettata_da_id": call.accettata_da_id,
    }
    if extra:
        payload.update(extra)
    return payload


def _notifica_parti(call: ChiamataVocale, action: str, extra: dict | None = None, user_ids: list[int] | None = None):
    data = _ws_payload(action, call, extra)
    ids = user_ids if user_ids is not None else _destinatari_user_ids(call)
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    for uid in {int(u) for u in ids if u}:
        async_to_sync(channel_layer.group_send)(
            voce_user_group(uid),
            {"type": "voce_signal", "message": data},
        )
        async_to_sync(channel_layer.group_send)(
            user_notifications_group(uid),
            {"type": "send_notification", "message": data},
        )


def _push_invito(call: ChiamataVocale, user_ids: list[int]):
    try:
        from personaggi.notify import notify_user_ids
    except Exception:
        return
    if call.verso_staff:
        body = f"{call.chiamante.nome} chiama lo staff."
    else:
        body = f"{call.chiamante.nome} ti sta chiamando."
    notify_user_ids(
        user_ids,
        category="in_game",
        head="Chiamata vocale",
        body=body,
        url="/?tab=messaggi",
    )


def avvia_chiamata(*, chiamante: Personaggio, chiamato: Personaggio | None, verso_staff: bool) -> ChiamataVocale:
    from personaggi.campagna_moduli import MODULO_CHIAMATE, modulo_accesso_error, personaggio_puo_accedere_modulo

    scadi_chiamate_vecchie()
    owner = chiamante.proprietario
    if not owner:
        raise ValueError("Il chiamante non ha un giocatore associato.")
    msg_mod = modulo_accesso_error(chiamante, MODULO_CHIAMATE, user=owner)
    if msg_mod:
        raise ValueError(msg_mod)
    if user_ha_chiamata_attiva(owner):
        raise ValueError("Hai già una chiamata in corso.")
    if verso_staff:
        call = ChiamataVocale.objects.create(
            chiamante=chiamante,
            chiamato=None,
            verso_staff=True,
            campagna=chiamante.campagna,
            stato=ChiamataVocale.STATO_RINGING,
        )
        dest_ids = [i for i in staff_user_ids(chiamante.campagna) if i != owner.id]
        if not dest_ids:
            call.stato = ChiamataVocale.STATO_PERSA
            call.closed_at = timezone.now()
            call.save(update_fields=["stato", "closed_at", "updated_at"])
            raise ValueError("Nessuno staff raggiungibile in questa campagna.")
        _notifica_parti(call, "VOCE_INVITO", user_ids=dest_ids + [owner.id])
        _push_invito(call, dest_ids)
        return call

    if not chiamato or not chiamato.proprietario_id:
        raise ValueError("Destinatario non raggiungibile.")
    if chiamato.pk == chiamante.pk:
        raise ValueError("Non puoi chiamare te stesso.")
    dest_mod = modulo_accesso_error(chiamato, MODULO_CHIAMATE, user=chiamato.proprietario)
    if dest_mod:
        raise ValueError(f"{chiamato.nome} non può ricevere chiamate in questa campagna.")
    if user_ha_chiamata_attiva(chiamato.proprietario):
        raise ValueError(f"{chiamato.nome} è già in chiamata.")
    call = ChiamataVocale.objects.create(
        chiamante=chiamante,
        chiamato=chiamato,
        verso_staff=False,
        campagna=chiamante.campagna,
        stato=ChiamataVocale.STATO_RINGING,
    )
    dest_ids = [chiamato.proprietario_id, owner.id]
    _notifica_parti(call, "VOCE_INVITO", user_ids=dest_ids)
    _push_invito(call, [chiamato.proprietario_id])
    return call


def utente_puo_partecipare(call: ChiamataVocale, user) -> bool:
    if not user:
        return False
    if call.chiamante.proprietario_id == user.id:
        return True
    if call.chiamato_id and call.chiamato.proprietario_id == user.id:
        return True
    if call.accettata_da_id == user.id:
        return True
    if call.verso_staff and user_is_campaign_staff(user, call.campagna):
        return True
    return False


def accetta_chiamata(call: ChiamataVocale, user: User) -> ChiamataVocale:
    from personaggi.campagna_moduli import MODULO_CHIAMATE, user_puo_accedere_modulo

    scadi_chiamate_vecchie()
    call.refresh_from_db()
    if call.stato != ChiamataVocale.STATO_RINGING:
        raise ValueError("La chiamata non è più in squillo.")
    if not user_puo_accedere_modulo(user, call.campagna, MODULO_CHIAMATE):
        raise ValueError("Chiamate vocali: modulo non attivo in questa campagna.")
    if call.chiamante.proprietario_id == user.id:
        raise ValueError("Non puoi accettare la tua stessa chiamata.")
    if call.verso_staff:
        if not user_is_campaign_staff(user, call.campagna):
            raise ValueError("Solo lo staff può rispondere.")
    elif not call.chiamato_id or call.chiamato.proprietario_id != user.id:
        raise ValueError("Questa chiamata non è per te.")
    occupato = user_ha_chiamata_attiva(user)
    if occupato and occupato.pk != call.pk:
        raise ValueError("Sei già in un'altra chiamata.")
    staff_ids = staff_user_ids(call.campagna) if call.verso_staff else []
    call.stato = ChiamataVocale.STATO_IN_CORSO
    call.accettata_da = user
    call.save(update_fields=["stato", "accettata_da", "updated_at"])
    _notifica_parti(call, "VOCE_ACCETTATA")
    if staff_ids:
        altri = [i for i in staff_ids if i != user.id and i != call.chiamante.proprietario_id]
        if altri:
            _notifica_parti(call, "VOCE_PRESA", extra={"da_username": user.username}, user_ids=altri)
    return call


def rifiuta_chiamata(call: ChiamataVocale, user: User) -> ChiamataVocale:
    if call.stato != ChiamataVocale.STATO_RINGING:
        raise ValueError("La chiamata non è più in squillo.")
    if call.chiamante.proprietario_id == user.id:
        call.stato = ChiamataVocale.STATO_TERMINATA
        call.closed_at = timezone.now()
        call.save(update_fields=["stato", "closed_at", "updated_at"])
        _notifica_parti(call, "VOCE_CHIUSA", extra={"motivo": "annullata"})
        return call
    if call.verso_staff:
        if not user_is_campaign_staff(user, call.campagna):
            raise ValueError("Solo lo staff può rifiutare.")
    elif not call.chiamato_id or call.chiamato.proprietario_id != user.id:
        raise ValueError("Questa chiamata non è per te.")
    call.stato = ChiamataVocale.STATO_RIFIUTATA
    call.closed_at = timezone.now()
    call.save(update_fields=["stato", "closed_at", "updated_at"])
    _notifica_parti(call, "VOCE_RIFIUTATA")
    return call


def chiudi_chiamata(call: ChiamataVocale, user: User) -> ChiamataVocale:
    if call.stato in (
        ChiamataVocale.STATO_TERMINATA,
        ChiamataVocale.STATO_RIFIUTATA,
        ChiamataVocale.STATO_PERSA,
    ):
        return call
    if not utente_puo_partecipare(call, user):
        raise ValueError("Non puoi chiudere questa chiamata.")
    call.stato = ChiamataVocale.STATO_TERMINATA
    call.closed_at = timezone.now()
    call.save(update_fields=["stato", "closed_at", "updated_at"])
    _notifica_parti(call, "VOCE_CHIUSA", extra={"motivo": "hangup"})
    return call


def altro_user_id(call: ChiamataVocale, user) -> int | None:
    """Utente a cui inoltrare SDP/ICE."""
    if not user:
        return None
    if call.stato != ChiamataVocale.STATO_IN_CORSO:
        return None
    caller_uid = call.chiamante.proprietario_id
    callee_uid = call.accettata_da_id
    if not callee_uid and call.chiamato_id:
        callee_uid = call.chiamato.proprietario_id
    if user.id == caller_uid:
        return callee_uid
    if user.id == callee_uid:
        return caller_uid
    return None
