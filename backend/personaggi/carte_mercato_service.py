"""
Mercato scambio carte tra personaggi della stessa campagna.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
    SCAMBIO_STATO_ACCETTATA,
    SCAMBIO_STATO_ANNULLATA,
    SCAMBIO_STATO_APERTA,
    CartaCollezionabile,
    CartaPosseduta,
    DuelloCarte,
    DUELLO_STATO_ANNULLATO,
    DUELLO_STATO_FINITO,
    MazzoDuello,
    OffertaScambioCarte,
)
from personaggi.carte_collezionabili_service import (
    assert_personaggio_puo_accedere_carte,
    build_collezione_payload,
    get_config_carte,
    personaggio_puo_accedere_carte,
)
from personaggi.models import Personaggio


def _motivo_carta_non_scambiabile(cp: CartaPosseduta, *, offerta_esclusa_id=None) -> str | None:
    if cp.slot_reliquiario.exists():
        return "La carta è equipaggiata nel reliquiario."
    offerte_aperte = OffertaScambioCarte.objects.filter(
        carta_offerta=cp,
        stato=SCAMBIO_STATO_APERTA,
    )
    if offerta_esclusa_id:
        offerte_aperte = offerte_aperte.exclude(pk=offerta_esclusa_id)
    if offerte_aperte.exists():
        return "La carta è già in un'offerta aperta."
    cp_id = str(cp.id)
    for mazzo in MazzoDuello.objects.filter(personaggio=cp.personaggio):
        ids = [str(x) for x in (mazzo.carte_possedute_ids or [])]
        if cp_id in ids or mazzo.leader_carta_posseduta_id == cp_id:
            return "La carta è inclusa in un mazzo duello."
    stati_bloccanti = {"LOB", "PRE", "ATT", "COR"}
    duelli = DuelloCarte.objects.filter(
        campagna_id=cp.personaggio.campagna_id,
        stato__in=stati_bloccanti,
    ).filter(Q(sfidante=cp.personaggio) | Q(sfidato=cp.personaggio))
    for duello in duelli:
        for field in (duello.mazzo_sfidante_ids or [], duello.mazzo_sfidato_ids or []):
            if cp_id in [str(x) for x in field]:
                return "La carta è in un duello attivo."
    return None


def _serializza_carta_breve(carta: CartaCollezionabile | None) -> dict | None:
    if not carta:
        return None
    return {
        "id": str(carta.id),
        "codice": carta.codice,
        "nome": carta.nome,
        "rarita": carta.rarita,
        "tipo": carta.tipo,
        "energia": carta.energia,
    }


def _serializza_posseduta_breve(cp: CartaPosseduta | None) -> dict | None:
    if not cp:
        return None
    return {
        "id": str(cp.id),
        "carta": _serializza_carta_breve(cp.carta),
    }


def serializza_offerta_scambio(offerta: OffertaScambioCarte) -> dict:
    offerta = (
        OffertaScambioCarte.objects.select_related(
            "offerente",
            "accettante",
            "carta_offerta__carta",
            "carta_contropartita__carta",
            "richiesta_carta",
            "campagna",
        )
        .filter(pk=offerta.pk)
        .first()
        or offerta
    )
    return {
        "id": str(offerta.id),
        "stato": offerta.stato,
        "messaggio": offerta.messaggio,
        "created_at": offerta.created_at.isoformat(),
        "updated_at": offerta.updated_at.isoformat(),
        "accettata_at": offerta.accettata_at.isoformat() if offerta.accettata_at else None,
        "offerente": {
            "id": str(offerta.offerente_id),
            "nome": offerta.offerente.nome,
        },
        "accettante": (
            {"id": str(offerta.accettante_id), "nome": offerta.accettante.nome}
            if offerta.accettante_id
            else None
        ),
        "carta_offerta": _serializza_posseduta_breve(offerta.carta_offerta),
        "richiesta_carta": _serializza_carta_breve(offerta.richiesta_carta),
        "richiesta_crediti": (
            float(offerta.richiesta_crediti) if offerta.richiesta_crediti is not None else None
        ),
        "carta_contropartita": _serializza_posseduta_breve(offerta.carta_contropartita),
        "commissione_crediti": (
            float(offerta.commissione_crediti) if offerta.commissione_crediti is not None else None
        ),
        "crediti_trasferiti": (
            float(offerta.crediti_trasferiti) if offerta.crediti_trasferiti is not None else None
        ),
        "mio": False,
    }


def _catalogo_richieste_mercato(campagna_id) -> list[dict]:
    return [
        _serializza_carta_breve(c)
        for c in CartaCollezionabile.objects.filter(campagna_id=campagna_id, attiva=True).order_by(
            "nome"
        )
    ]


def build_mercato_payload(personaggio: Personaggio) -> dict:
    if not personaggio_puo_accedere_carte(personaggio):
        return {
            "puo_accedere": False,
            "offerte_aperte": [],
            "mie_offerte": [],
            "storico": [],
            "catalogo_richieste": [],
            "commissione_pct": 0,
        }

    cfg = get_config_carte(personaggio.campagna, create=False)
    commissione_pct = float(cfg.mercato_commissione_pct) if cfg else 8.0

    offerte_qs = (
        OffertaScambioCarte.objects.filter(campagna=personaggio.campagna)
        .select_related(
            "offerente",
            "accettante",
            "carta_offerta__carta",
            "carta_contropartita__carta",
            "richiesta_carta",
        )
        .order_by("-updated_at")
    )

    offerte_aperte = []
    mie_offerte = []
    for offerta in offerte_qs.filter(stato=SCAMBIO_STATO_APERTA):
        row = serializza_offerta_scambio(offerta)
        row["mio"] = offerta.offerente_id == personaggio.id
        row["posso_accettare"] = (
            offerta.offerente_id != personaggio.id
            and _posso_accettare_offerta(personaggio, offerta)[0]
        )
        if offerta.offerente_id == personaggio.id:
            mie_offerte.append(row)
        else:
            offerte_aperte.append(row)

    storico = []
    for offerta in offerte_qs.filter(stato=SCAMBIO_STATO_ACCETTATA).filter(
        Q(offerente=personaggio) | Q(accettante=personaggio)
    )[:30]:
        row = serializza_offerta_scambio(offerta)
        row["mio"] = offerta.offerente_id == personaggio.id
        storico.append(row)

    carte_scambiabili = []
    for cp in CartaPosseduta.objects.filter(personaggio=personaggio).select_related("carta"):
        motivo = _motivo_carta_non_scambiabile(cp)
        carte_scambiabili.append({
            "id": str(cp.id),
            "carta": _serializza_carta_breve(cp.carta),
            "scambiabile": motivo is None,
            "motivo_blocco": motivo,
        })

    return {
        "puo_accedere": True,
        "commissione_pct": commissione_pct,
        "offerte_aperte": offerte_aperte,
        "mie_offerte": mie_offerte,
        "storico": storico,
        "catalogo_richieste": _catalogo_richieste_mercato(personaggio.campagna_id),
        "carte_scambiabili": carte_scambiabili,
        "crediti": float(personaggio.crediti),
    }


def _posso_accettare_offerta(
    accettante: Personaggio,
    offerta: OffertaScambioCarte,
    *,
    carta_contropartita_id=None,
) -> tuple[bool, str]:
    if offerta.stato != SCAMBIO_STATO_APERTA:
        return False, "Offerta non più disponibile."
    if offerta.offerente_id == accettante.id:
        return False, "Non puoi accettare la tua offerta."
    if offerta.campagna_id != accettante.campagna_id:
        return False, "Campagna diversa."

    if offerta.richiesta_crediti and offerta.richiesta_crediti > 0:
        if accettante.crediti < offerta.richiesta_crediti:
            return False, "Crediti insufficienti."

    if offerta.richiesta_carta_id:
        if not carta_contropartita_id:
            return False, "Devi indicare quale copia della carta richiesta offri."
        cp = CartaPosseduta.objects.filter(
            pk=carta_contropartita_id,
            personaggio=accettante,
            carta_id=offerta.richiesta_carta_id,
        ).first()
        if not cp:
            return False, "Carta contropartita non valida."
        motivo = _motivo_carta_non_scambiabile(cp)
        if motivo:
            return False, motivo
    elif not offerta.richiesta_crediti or offerta.richiesta_crediti <= 0:
        return False, "Offerta senza richiesta valida."

    motivo_offerta = _motivo_carta_non_scambiabile(
        offerta.carta_offerta,
        offerta_esclusa_id=offerta.id,
    )
    if motivo_offerta:
        return False, f"Carta offerta non più disponibile: {motivo_offerta}"

    return True, ""


@transaction.atomic
def crea_offerta_scambio(
    personaggio: Personaggio,
    *,
    carta_offerta_id,
    richiesta_carta_id=None,
    richiesta_crediti=None,
    messaggio="",
) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)

    cp = CartaPosseduta.objects.select_related("carta").get(
        pk=carta_offerta_id,
        personaggio=personaggio,
    )
    motivo = _motivo_carta_non_scambiabile(cp)
    if motivo:
        raise ValidationError(motivo)

    richiesta_carta = None
    if richiesta_carta_id:
        richiesta_carta = CartaCollezionabile.objects.get(
            pk=richiesta_carta_id,
            campagna=personaggio.campagna,
            attiva=True,
        )

    crediti = None
    if richiesta_crediti is not None and str(richiesta_crediti).strip() != "":
        crediti = Decimal(str(richiesta_crediti))
        if crediti < 0:
            raise ValidationError("I crediti richiesti non possono essere negativi.")

    if not richiesta_carta and (crediti is None or crediti <= 0):
        raise ValidationError("Indica almeno una carta catalogo richiesta o un importo in crediti.")

    offerta = OffertaScambioCarte.objects.create(
        campagna=personaggio.campagna,
        offerente=personaggio,
        carta_offerta=cp,
        richiesta_carta=richiesta_carta,
        richiesta_crediti=crediti if crediti and crediti > 0 else None,
        messaggio=(messaggio or "").strip(),
        stato=SCAMBIO_STATO_APERTA,
    )
    payload = build_mercato_payload(personaggio)
    payload["offerta_creata"] = serializza_offerta_scambio(offerta)
    return payload


@transaction.atomic
def annulla_offerta_scambio(personaggio: Personaggio, offerta_id) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    offerta = OffertaScambioCarte.objects.select_for_update().get(pk=offerta_id)
    if offerta.offerente_id != personaggio.id:
        raise ValidationError("Solo l'offerente può annullare l'offerta.")
    if offerta.stato != SCAMBIO_STATO_APERTA:
        raise ValidationError("L'offerta non è più annullabile.")
    offerta.stato = SCAMBIO_STATO_ANNULLATA
    offerta.save(update_fields=["stato", "updated_at"])
    return build_mercato_payload(personaggio)


@transaction.atomic
def accetta_offerta_scambio(
    accettante: Personaggio,
    offerta_id,
    *,
    carta_contropartita_id=None,
) -> dict:
    assert_personaggio_puo_accedere_carte(accettante)

    offerta = OffertaScambioCarte.objects.select_for_update().get(pk=offerta_id)
    offerta = OffertaScambioCarte.objects.select_related(
        "offerente",
        "carta_offerta",
        "richiesta_carta",
        "campagna",
    ).get(pk=offerta_id)

    ok, msg = _posso_accettare_offerta(
        accettante,
        offerta,
        carta_contropartita_id=carta_contropartita_id,
    )
    if not ok:
        raise ValidationError(msg)

    offerente = offerta.offerente
    carta_offerta = CartaPosseduta.objects.select_for_update().get(pk=offerta.carta_offerta_id)
    carta_contropartita = None

    if offerta.richiesta_carta_id:
        carta_contropartita = CartaPosseduta.objects.select_for_update().get(
            pk=carta_contropartita_id,
            personaggio=accettante,
            carta_id=offerta.richiesta_carta_id,
        )

    commissione = Decimal("0.00")
    crediti_net = Decimal("0.00")
    if offerta.richiesta_crediti and offerta.richiesta_crediti > 0:
        cfg = get_config_carte(offerta.campagna, create=False)
        pct = cfg.mercato_commissione_pct if cfg else Decimal("8.00")
        importo = Decimal(offerta.richiesta_crediti)
        commissione = (importo * pct / Decimal("100")).quantize(Decimal("0.01"))
        crediti_net = importo - commissione
        accettante.modifica_crediti(
            -importo,
            f"Mercato carte: acquisto da {offerente.nome}",
        )
        offerente.modifica_crediti(
            crediti_net,
            f"Mercato carte: vendita a {accettante.nome}",
        )

    carta_offerta.personaggio = accettante
    carta_offerta.save(update_fields=["personaggio", "updated_at"])

    if carta_contropartita:
        carta_contropartita.personaggio = offerente
        carta_contropartita.save(update_fields=["personaggio", "updated_at"])

    offerta.stato = SCAMBIO_STATO_ACCETTATA
    offerta.accettante = accettante
    offerta.accettata_at = timezone.now()
    offerta.carta_contropartita = carta_contropartita
    offerta.commissione_crediti = commissione if commissione > 0 else None
    offerta.crediti_trasferiti = crediti_net if crediti_net > 0 else None
    offerta.save(
        update_fields=[
            "stato",
            "accettante",
            "accettata_at",
            "carta_contropartita",
            "commissione_crediti",
            "crediti_trasferiti",
            "updated_at",
        ]
    )

    payload = build_mercato_payload(accettante)
    payload["collezione"] = build_collezione_payload(accettante)
    payload["offerta_accettata"] = serializza_offerta_scambio(offerta)
    return payload


def lista_scambi_staff(campagna, *, stato=None, limit=100) -> dict:
    qs = (
        OffertaScambioCarte.objects.filter(campagna=campagna)
        .select_related(
            "offerente",
            "accettante",
            "carta_offerta__carta",
            "carta_contropartita__carta",
            "richiesta_carta",
        )
        .order_by("-updated_at")
    )
    if stato:
        qs = qs.filter(stato=stato)

    rows = [serializza_offerta_scambio(o) for o in qs[:limit]]
    summary = {
        "aperte": OffertaScambioCarte.objects.filter(
            campagna=campagna, stato=SCAMBIO_STATO_APERTA
        ).count(),
        "accettate": OffertaScambioCarte.objects.filter(
            campagna=campagna, stato=SCAMBIO_STATO_ACCETTATA
        ).count(),
        "annullate": OffertaScambioCarte.objects.filter(
            campagna=campagna, stato=SCAMBIO_STATO_ANNULLATA
        ).count(),
    }
    return {"summary": summary, "offerte": rows}
