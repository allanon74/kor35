"""
Lobby scontro carte OPEN — QR sessione, pre-partita (mazzo, posta), avvio partita.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from personaggi.carte_collezionabili_models import (
    CARTE_ACCESSO_OPEN,
    DUELLO_AVVIO_LOBBY,
    DUELLO_MODALITA_LIVE,
    DUELLO_MODALITA_MANUALE,
    DUELLO_STATO_ANNULLATO,
    DUELLO_STATO_IN_CORSO,
    DUELLO_STATO_LOBBY,
    DUELLO_STATO_PREMATCH,
    DuelloCarte,
    INFLUENZA_INIZIALE,
    POSTA_FONTE_CREDITI,
    POSTA_FONTE_RISERVA,
)
from personaggi.carte_collezionabili_service import (
    assert_personaggio_puo_accedere_carte,
    get_carte_accesso_modo,
    personaggio_puo_accedere_carte,
    valida_setup_duello,
)
from personaggi.carte_duello_service import (
    _avvia_turno_con_effetti,
    _genera_codice_invito,
    _inizializza_stato_gioco,
    _pg_key,
    _valida_coppia_duello,
    serializza_duello,
)
from personaggi.carte_duello_ws import broadcast_duello_update
from personaggi.models import Personaggio, QrCode
from personaggi.scontro_carte_avista import duello_da_vista_pk, ensure_portale_avista


def _prematch_vuoto() -> dict:
    return {
        "posta_cr": 0,
        "posta_accettata": False,
        "posta_ultima_proposta_da": None,
        "sfidante": {
            "mazzo_ids": [],
            "leader_id": None,
            "pronto": False,
            "posta_fonte": POSTA_FONTE_RISERVA,
        },
        "sfidato": {
            "mazzo_ids": [],
            "leader_id": None,
            "pronto": False,
            "posta_fonte": POSTA_FONTE_RISERVA,
        },
    }


def _ruolo_in_duello(duello: DuelloCarte, personaggio: Personaggio) -> str:
    return "sfidante" if duello.sfidante_id == personaggio.id else "sfidato"


def _qr_image_data_uri(qr_id) -> str:
    import base64
    import io

    import qrcode

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=8, border=3)
    qr.add_data(str(qr_id))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"


def _ensure_qr_lobby(duello: DuelloCarte) -> QrCode:
    if duello.qr_code_id:
        return duello.qr_code
    portale = ensure_portale_avista(duello)
    qr = QrCode.objects.create(
        vista=portale,
        testo=f"Scontro carte — {duello.sfidante.nome}",
    )
    duello.qr_code = qr
    duello.save(update_fields=["qr_code", "updated_at"])
    return qr


def _lobby_attiva_per_sfidante(sfidante: Personaggio):
    return DuelloCarte.objects.filter(
        sfidante=sfidante,
        stato__in=(DUELLO_STATO_LOBBY, DUELLO_STATO_PREMATCH),
    ).first()


def _valida_posta_disponibile(pg: Personaggio, posta: Decimal, fonte: str):
    if posta <= 0:
        return
    if fonte == POSTA_FONTE_RISERVA:
        if pg.riserva < posta:
            raise ValidationError(
                f"Riserva scommesse insufficiente ({pg.riserva} CR, servono {posta} CR)."
            )
    elif fonte == POSTA_FONTE_CREDITI:
        if Decimal(str(pg.crediti)) < posta:
            raise ValidationError(
                f"Crediti insufficienti ({pg.crediti} CR, servono {posta} CR)."
            )
    else:
        raise ValidationError("Fonte posta non valida.")


def serializza_scontro_qr(duello: DuelloCarte, scanner_pg: Personaggio) -> dict:
    assert_personaggio_puo_accedere_carte(scanner_pg)
    if get_carte_accesso_modo(scanner_pg.campagna) != CARTE_ACCESSO_OPEN:
        raise ValidationError("Le lobby scontro sono disponibili solo in modalità OPEN.")
    if duello.stato not in (DUELLO_STATO_LOBBY, DUELLO_STATO_PREMATCH):
        raise ValidationError("Questo scontro non accetta più partecipanti.")
    if duello.sfidante_id == scanner_pg.id:
        raise ValidationError("Non puoi unirti al tuo stesso scontro.")
    if duello.sfidato_id and duello.sfidato_id != scanner_pg.id:
        raise ValidationError("Questo scontro ha già un avversario.")
    return {
        "duello_id": str(duello.id),
        "stato": duello.stato,
        "sfidante": {"id": duello.sfidante_id, "nome": duello.sfidante.nome},
        "sfidato": (
            {"id": duello.sfidato_id, "nome": duello.sfidato.nome}
            if duello.sfidato_id
            else None
        ),
        "puo_unirsi": duello.stato == DUELLO_STATO_LOBBY and not duello.sfidato_id,
        "gia_partecipante": duello.sfidato_id == scanner_pg.id,
        "qr_code_id": duello.qr_code_id,
    }


@transaction.atomic
def apri_scontro_lobby(sfidante: Personaggio) -> dict:
    assert_personaggio_puo_accedere_carte(sfidante)
    if get_carte_accesso_modo(sfidante.campagna) != CARTE_ACCESSO_OPEN:
        raise ValidationError("Apri scontro è disponibile solo in modalità OPEN.")

    esistente = _lobby_attiva_per_sfidante(sfidante)
    if esistente:
        qr = _ensure_qr_lobby(esistente)
        payload = serializza_duello(esistente, sfidante)
        payload["qrcode_id"] = qr.id
        payload["qr_image_data_uri"] = _qr_image_data_uri(qr.id)
        return payload

    duello = DuelloCarte.objects.create(
        campagna=sfidante.campagna,
        sfidante=sfidante,
        sfidato=None,
        stato=DUELLO_STATO_LOBBY,
        avvio_tipo=DUELLO_AVVIO_LOBBY,
        stato_prematch=_prematch_vuoto(),
        codice_invito=_genera_codice_invito(),
    )
    qr = _ensure_qr_lobby(duello)
    payload = serializza_duello(duello, sfidante)
    payload["qrcode_id"] = qr.id
    payload["qr_image_data_uri"] = _qr_image_data_uri(qr.id)
    broadcast_duello_update(duello.id, payload)
    return payload


@transaction.atomic
def unisciti_scontro_lobby(sfidato: Personaggio, *, qrcode_id=None, duello_id=None) -> dict:
    assert_personaggio_puo_accedere_carte(sfidato)
    if get_carte_accesso_modo(sfidato.campagna) != CARTE_ACCESSO_OPEN:
        raise ValidationError("Unisciti allo scontro è disponibile solo in modalità OPEN.")

    duello = None
    if duello_id:
        duello = (
            DuelloCarte.objects.select_for_update(of=("self",))
            .filter(pk=duello_id)
            .first()
        )
    elif qrcode_id:
        from personaggi.qr_logic import validate_qr_id

        try:
            qr_pk = validate_qr_id(qrcode_id)
        except ValueError as exc:
            raise ValidationError("ID QR non valido.") from exc
        qr = QrCode.objects.select_related("vista").filter(pk=qr_pk).first()
        if not qr:
            raise ValidationError("QR non trovato.")
        candidato = None
        if qr.vista_id:
            candidato = duello_da_vista_pk(qr.vista_id)
        if not candidato:
            candidato = DuelloCarte.objects.filter(qr_code=qr).select_related("sfidante").first()
        duello = (
            DuelloCarte.objects.select_for_update(of=("self",))
            .filter(pk=candidato.pk)
            .first()
            if candidato
            else None
        )
    if not duello:
        raise ValidationError("Scontro non trovato.")
    duello = DuelloCarte.objects.select_related("sfidante", "sfidato").get(pk=duello.pk)

    if duello.stato != DUELLO_STATO_LOBBY:
        if duello.stato == DUELLO_STATO_PREMATCH and duello.sfidato_id == sfidato.id:
            return serializza_duello(duello, sfidato)
        raise ValidationError("Questo scontro non è più in attesa di un avversario.")
    if duello.sfidato_id:
        raise ValidationError("Questo scontro ha già un avversario.")

    _valida_coppia_duello(duello.sfidante, sfidato)
    duello.sfidato = sfidato
    duello.stato = DUELLO_STATO_PREMATCH
    pre = duello.stato_prematch or _prematch_vuoto()
    duello.stato_prematch = pre
    duello.save()

    payload = serializza_duello(duello, sfidato)
    broadcast_duello_update(duello.id, payload)
    _notify_lobby_aggiornata(duello)
    return payload


def _notify_lobby_aggiornata(duello: DuelloCarte):
    """Avvisa l'host (sfidante) che un avversario si è unito alla lobby."""
    if not duello.sfidante_id or not duello.sfidato_id:
        return
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {
            "type": "send_notification",
            "message": {
                "action": "DUELLO_LOBBY",
                "duello_id": str(duello.id),
                "sfidante_nome": duello.sfidante.nome,
                "sfidato_nome": duello.sfidato.nome,
                "destinatario_personaggio_id": duello.sfidante_id,
            },
        },
    )


def _notify_prematch_al_avversario(duello: DuelloCarte, da_personaggio: Personaggio):
    """Avvisa l'altro giocatore di un aggiornamento pre-partita."""
    if not duello.sfidante_id or not duello.sfidato_id:
        return
    altro_id = (
        duello.sfidato_id
        if da_personaggio.id == duello.sfidante_id
        else duello.sfidante_id
    )
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {
            "type": "send_notification",
            "message": {
                "action": "DUELLO_PREMATCH",
                "duello_id": str(duello.id),
                "da_nome": da_personaggio.nome,
                "destinatario_personaggio_id": altro_id,
            },
        },
    )


def _maybe_avvia_partita(duello: DuelloCarte) -> bool:
    pre = duello.stato_prematch or {}
    posta = Decimal(str(pre.get("posta_cr") or duello.posta_cr or 0))
    if not pre.get("posta_accettata") and posta > 0:
        return False
    if posta <= 0:
        pre["posta_accettata"] = True
    s = pre.get("sfidante") or {}
    t = pre.get("sfidato") or {}
    if not (s.get("pronto") and t.get("pronto")):
        return False
    mazzo_a = s.get("mazzo_ids") or []
    mazzo_b = t.get("mazzo_ids") or []
    leader_a = s.get("leader_id")
    leader_b = t.get("leader_id")
    ok_a, err_a = valida_setup_duello(mazzo_a, leader_a, duello.sfidante)
    ok_b, err_b = valida_setup_duello(mazzo_b, leader_b, duello.sfidato)
    if not ok_a:
        raise ValidationError(" ".join(err_a))
    if not ok_b:
        raise ValidationError(" ".join(err_b))

    fonte_a = s.get("posta_fonte") or POSTA_FONTE_RISERVA
    fonte_b = t.get("posta_fonte") or POSTA_FONTE_RISERVA
    _valida_posta_disponibile(duello.sfidante, posta, fonte_a)
    _valida_posta_disponibile(duello.sfidato, posta, fonte_b)

    import random

    duello.mazzo_sfidante_ids = [str(x) for x in mazzo_a]
    duello.mazzo_sfidato_ids = [str(x) for x in mazzo_b]
    duello.leader_sfidante_id = str(leader_a)
    duello.leader_sfidato_id = str(leader_b)
    duello.posta_cr = posta
    duello.modalita_partita = pre.get("modalita_partita") or duello.modalita_partita
    duello.stato = DUELLO_STATO_IN_CORSO
    duello.influenza_sfidante = INFLUENZA_INIZIALE
    duello.influenza_sfidato = INFLUENZA_INIZIALE
    duello.stato_gioco = _inizializza_stato_gioco(duello)
    if duello.modalita_partita == DUELLO_MODALITA_LIVE:
        primo = random.choice([duello.sfidante, duello.sfidato])
        duello.turno_personaggio = primo
        _avvia_turno_con_effetti(duello, primo)
    else:
        duello.turno_personaggio = None
    duello.stato_prematch = pre
    duello.save()
    return True


@transaction.atomic
def azione_prematch(duello_id, personaggio: Personaggio, azione: str, payload: dict | None = None) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    duello = DuelloCarte.objects.select_for_update(of=("self",)).get(pk=duello_id)
    duello = DuelloCarte.objects.select_related("sfidante", "sfidato").get(pk=duello_id)
    if duello.stato != DUELLO_STATO_PREMATCH:
        raise ValidationError("Non sei in fase pre-partita.")
    if personaggio.id not in (duello.sfidante_id, duello.sfidato_id):
        raise ValidationError("Non partecipi a questo scontro.")

    payload = payload or {}
    azione = (azione or "").strip().lower()
    ruolo = _ruolo_in_duello(duello, personaggio)
    pre = dict(duello.stato_prematch or _prematch_vuoto())
    lato = dict(pre.get(ruolo) or {})
    posta = Decimal(str(pre.get("posta_cr") or 0))

    if azione == "proponi_posta":
        if ruolo == "sfidato" and not pre.get("posta_ultima_proposta_da"):
            raise ValidationError("Solo il creatore può proporre la posta iniziale.")
        nuova = Decimal(str(payload.get("posta_cr", 0)))
        if nuova < 0:
            raise ValidationError("La posta non può essere negativa.")
        pre["posta_cr"] = float(nuova)
        pre["posta_accettata"] = nuova <= 0
        pre["posta_ultima_proposta_da"] = ruolo
        if nuova <= 0:
            pre["posta_ultima_proposta_da"] = None

    elif azione == "rispondi_posta":
        risposta = (payload.get("risposta") or "").strip().lower()
        if risposta not in ("accetta", "rifiuta", "contro"):
            raise ValidationError("Risposta non valida (accetta, rifiuta, contro).")
        if ruolo == pre.get("posta_ultima_proposta_da"):
            raise ValidationError("Non puoi rispondere alla tua proposta.")
        if risposta == "accetta":
            pre["posta_accettata"] = True
        elif risposta == "rifiuta":
            pre["posta_accettata"] = False
            pre["posta_ultima_proposta_da"] = None
        elif risposta == "contro":
            nuova = Decimal(str(payload.get("posta_cr", 0)))
            if nuova < 0:
                raise ValidationError("La posta non può essere negativa.")
            pre["posta_cr"] = float(nuova)
            pre["posta_accettata"] = nuova <= 0
            pre["posta_ultima_proposta_da"] = ruolo

    elif azione == "imposta_mazzo":
        mazzo_ids = payload.get("mazzo_ids") or []
        leader_id = payload.get("leader_id")
        ok, errs = valida_setup_duello(mazzo_ids, leader_id, personaggio)
        if not ok:
            raise ValidationError(" ".join(errs))
        lato["mazzo_ids"] = [str(x) for x in mazzo_ids]
        lato["leader_id"] = str(leader_id)
        lato["pronto"] = False

    elif azione == "imposta_posta_fonte":
        fonte = (payload.get("posta_fonte") or "").strip().lower()
        if fonte not in (POSTA_FONTE_RISERVA, POSTA_FONTE_CREDITI):
            raise ValidationError("Fonte posta non valida.")
        lato["posta_fonte"] = fonte

    elif azione == "imposta_modalita":
        mod = (payload.get("modalita") or "").strip().upper()
        if mod not in (DUELLO_MODALITA_LIVE, DUELLO_MODALITA_MANUALE):
            raise ValidationError("Modalità non valida.")
        pre["modalita_partita"] = mod
        duello.modalita_partita = mod

    elif azione == "segna_pronto":
        pronto = bool(payload.get("pronto", True))
        if pronto:
            if not lato.get("mazzo_ids"):
                raise ValidationError("Seleziona un mazzo prima di essere pronto.")
            if not lato.get("leader_id"):
                raise ValidationError("Seleziona un Leader prima di essere pronto.")
            posta_attuale = Decimal(str(pre.get("posta_cr") or 0))
            if posta_attuale > 0 and not pre.get("posta_accettata"):
                raise ValidationError("Accetta la posta prima di essere pronto.")
            fonte = lato.get("posta_fonte") or POSTA_FONTE_RISERVA
            _valida_posta_disponibile(personaggio, posta_attuale, fonte)
        lato["pronto"] = pronto

    elif azione == "annulla":
        duello.stato = DUELLO_STATO_ANNULLATO
        duello.save(update_fields=["stato", "updated_at"])
        out = serializza_duello(duello, personaggio)
        broadcast_duello_update(duello.id, out)
        return out

    else:
        raise ValidationError("Azione pre-partita non valida.")

    pre[ruolo] = lato
    duello.stato_prematch = pre
    duello.posta_cr = Decimal(str(pre.get("posta_cr") or 0))
    duello.save()

    avviato = _maybe_avvia_partita(duello)
    out = serializza_duello(duello, personaggio)
    broadcast_duello_update(duello.id, out)
    if avviato:
        from personaggi.carte_duello_service import _notify_partita_iniziata

        duello.refresh_from_db()
        _notify_partita_iniziata(duello)
    elif azione != "annulla":
        _notify_prematch_al_avversario(duello, personaggio)
    return out


def liquida_posta_duello(duello: DuelloCarte):
    """Alla fine partita: perdente paga da riserva/crediti, vincitore incassa sui crediti."""
    from personaggi.carte_collezionabili_models import DUELLO_STATO_FINITO

    if duello.stato != DUELLO_STATO_FINITO or not duello.vincitore_id:
        return
    posta = Decimal(str(duello.posta_cr or 0))
    if posta <= 0:
        return
    pre = duello.stato_prematch or {}
    if pre.get("posta_liquidata"):
        return
    perdente = duello.sfidato if duello.vincitore_id == duello.sfidante_id else duello.sfidante
    ruolo_perd = "sfidante" if perdente.id == duello.sfidante_id else "sfidato"
    fonte = (pre.get(ruolo_perd) or {}).get("posta_fonte") or POSTA_FONTE_RISERVA

    if fonte == POSTA_FONTE_RISERVA:
        perdente.riserva = max(Decimal("0"), perdente.riserva - posta)
        perdente.save(update_fields=["riserva", "updated_at"])
        perdente.aggiungi_log(f"Duello carte perso: -{posta} CR dalla riserva scommesse.")
    else:
        perdente.modifica_crediti(-float(posta), "Posta persa duello carte")

    vincitore = duello.vincitore
    vincitore.modifica_crediti(float(posta), "Vittoria duello carte")
    vincitore.aggiungi_log(f"Vittoria duello carte: +{posta} CR.")
    pre["posta_liquidata"] = True
    duello.stato_prematch = pre
