"""
Logica Task/Missioni: ricompense, esclusiva, solo-primo, claim auto + notifica, riepilogo evento.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from personaggi.models import Carriera, Messaggio, Personaggio, get_active_korp_ids

from .models import Evento, Missione, MissioneEvento, MissioneRisoluzione

ZERO = Decimal("0.00")


def _q2(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fattore_for_korp(korp) -> Decimal:
    if not korp:
        return Decimal("1.00")
    return _q2(getattr(korp, "fattore_task", 1) or 1)


def personaggio_ha_korp(personaggio, korp_id) -> bool:
    if not personaggio or not korp_id:
        return False
    return int(korp_id) in {int(x) for x in get_active_korp_ids(personaggio)}


def personaggio_puo_svolgere(missione: Missione, personaggio: Personaggio) -> bool:
    """Esclusive: solo membri della KORP. Altrimenti tutti."""
    if not missione.esclusiva:
        return True
    if not missione.korp_id:
        return False
    return personaggio_ha_korp(personaggio, missione.korp_id)


def calcola_ricompensa_base(missione: Missione, *, is_primo: bool) -> tuple[Decimal, int]:
    cr = _q2(missione.reward_crediti)
    pr = int(missione.reward_prestigio or 0)
    if missione.premio_solo_primo and not is_primo:
        return ZERO, 0
    if not is_primo:
        cr = max(ZERO, cr - _q2(missione.malus_non_primo_crediti))
        pr = max(0, pr - int(missione.malus_non_primo_prestigio or 0))
        cr = _q2(cr + _q2(missione.bonus_successive_crediti))
        pr = pr + int(missione.bonus_successive_prestigio or 0)
    return cr, pr


def applica_fattore_korp(
    missione: Missione,
    personaggio: Personaggio | None,
    cr: Decimal,
    pr: int,
) -> tuple[Decimal, int, bool, Decimal]:
    """Fattore solo se PG membro della KORP della task."""
    if not missione.korp_id or not personaggio:
        return _q2(cr), int(pr), False, Decimal("1.00")
    if not personaggio_ha_korp(personaggio, missione.korp_id):
        return _q2(cr), int(pr), False, Decimal("1.00")
    fattore = fattore_for_korp(missione.korp)
    cr2 = _q2(cr * fattore)
    pr2 = int((Decimal(pr) * fattore).to_integral_value(rounding=ROUND_HALF_UP))
    return cr2, pr2, True, fattore


def ricompensa_per_visualizzazione(missione, personaggio, *, is_primo=True) -> dict:
    cr, pr = calcola_ricompensa_base(missione, is_primo=is_primo)
    cr2, pr2, is_bonus, fattore = applica_fattore_korp(missione, personaggio, cr, pr)
    return {
        "reward_crediti": cr2,
        "reward_prestigio": pr2,
        "reward_crediti_base": cr,
        "reward_prestigio_base": pr,
        "is_korp_bonus": is_bonus,
        "fattore_applicato": fattore,
    }


def _is_primo(missione_id, evento_id) -> bool:
    return not MissioneRisoluzione.objects.filter(
        missione_id=missione_id, evento_id=evento_id
    ).exists()


def _notifica_ricompensa(risoluzione: MissioneRisoluzione) -> None:
    pg = risoluzione.personaggio
    titolo = risoluzione.missione.titolo
    cr = _q2(risoluzione.reward_crediti)
    pr = int(risoluzione.reward_prestigio or 0)
    parti = []
    if cr > ZERO:
        parti.append(f"{cr} Crediti")
    if pr > 0:
        parti.append(f"{pr} Prestigio")
    premio = " e ".join(parti) if parti else "nessun premio (solo riconoscimento)"
    evento_lbl = risoluzione.evento.titolo if risoluzione.evento_id else "evento"
    Messaggio.objects.create(
        mittente=None,
        tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
        destinatario_personaggio=pg,
        titolo=f"Task completata: {titolo}",
        testo=(
            f"Hai risolto la task «{titolo}» ({evento_lbl}).\n"
            f"Ricompensa accreditata automaticamente: {premio}."
        ),
        campagna=pg.campagna,
        is_staff_message=True,
    )


@transaction.atomic
def reclama_ricompensa(risoluzione: MissioneRisoluzione, *, notifica: bool = True) -> MissioneRisoluzione:
    if risoluzione.ricompensa_reclamata:
        return risoluzione
    cr = _q2(risoluzione.reward_crediti)
    pr = int(risoluzione.reward_prestigio or 0)
    pg = risoluzione.personaggio
    titolo = risoluzione.missione.titolo
    if cr > ZERO:
        pg.modifica_crediti(cr, f"Task «{titolo}» — ricompensa Crediti")
    if pr > 0:
        pg.modifica_prestigio(pr, f"Task «{titolo}» — ricompensa Prestigio")
    risoluzione.ricompensa_reclamata = True
    risoluzione.reclamata_at = timezone.now()
    risoluzione.save(update_fields=["ricompensa_reclamata", "reclamata_at", "updated_at"])
    if notifica:
        _notifica_ricompensa(risoluzione)
    return risoluzione


@transaction.atomic
def assegna_risoluzione(
    *,
    missione: Missione,
    evento: Evento,
    personaggio: Personaggio,
    proposta_tecnica=None,
    social_post=None,
    quest=None,
    giorno=None,
    note: str = "",
    auto_claim: bool = True,
) -> MissioneRisoluzione:
    if not MissioneEvento.objects.filter(missione=missione, evento=evento).exists():
        raise ValueError("La task non è associata a questo evento.")
    if not personaggio_puo_svolgere(missione, personaggio):
        raise ValueError("Task esclusiva: il personaggio non appartiene alla KORP richiesta.")
    if MissioneRisoluzione.objects.filter(
        missione=missione, evento=evento, personaggio=personaggio
    ).exists():
        raise ValueError("Questo personaggio ha già risolto questa task per l'evento.")
    if missione.premio_solo_primo and not _is_primo(missione.id, evento.id):
        raise ValueError("Task a premio solo al primo: già risolta da un altro personaggio.")

    is_primo = _is_primo(missione.id, evento.id)
    cr, pr = calcola_ricompensa_base(missione, is_primo=is_primo)
    cr, pr, _, _ = applica_fattore_korp(missione, personaggio, cr, pr)

    ris = MissioneRisoluzione.objects.create(
        missione=missione,
        evento=evento,
        personaggio=personaggio,
        is_primo=is_primo,
        reward_crediti=cr,
        reward_prestigio=pr,
        proposta_tecnica=proposta_tecnica,
        social_post=social_post,
        quest=quest,
        giorno=giorno,
        note=note or "",
    )
    if auto_claim:
        reclama_ricompensa(ris, notifica=True)
        ris.refresh_from_db()
    return ris


def riepilogo_premi_evento(evento: Evento) -> list[dict]:
    """
    Per KORP X:
    - di Korp = task di X × fattore_X
    - non di Korp = generiche + altre KORP non esclusive (senza fattore)
    """
    missioni = list(
        Missione.objects.filter(eventi=evento, attiva=True).select_related("korp")
    )
    korps = list(Carriera.objects.filter(tipo_carriera__codice="korp").order_by("nome"))
    out = []
    for korp in korps:
        di_korp = [m for m in missioni if m.korp_id == korp.id]
        non_di_korp = [
            m
            for m in missioni
            if m.korp_id != korp.id and not m.esclusiva
        ]
        fattore = fattore_for_korp(korp)
        cr_k = sum((_q2(m.reward_crediti) for m in di_korp), ZERO)
        pr_k = sum((int(m.reward_prestigio or 0) for m in di_korp), 0)
        cr_n = sum((_q2(m.reward_crediti) for m in non_di_korp), ZERO)
        pr_n = sum((int(m.reward_prestigio or 0) for m in non_di_korp), 0)
        out.append({
            "korp_id": korp.id,
            "korp_nome": korp.nome,
            "fattore_task": fattore,
            "crediti_korp": _q2(cr_k * fattore),
            "prestigio_korp": int((Decimal(pr_k) * fattore).to_integral_value(rounding=ROUND_HALF_UP)),
            "crediti_non_korp": _q2(cr_n),
            "prestigio_non_korp": pr_n,
            "n_task_korp": len(di_korp),
            "n_task_non_korp": len(non_di_korp),
        })
    return out


def lista_missioni_per_personaggio(personaggio: Personaggio) -> list[dict]:
    missioni = list(
        Missione.objects.filter(attiva=True)
        .select_related("korp")
        .prefetch_related("eventi")
        .order_by("ordine", "titolo")
    )
    miei = list(
        MissioneRisoluzione.objects.filter(personaggio=personaggio, missione__in=missioni)
        .select_related("evento")
        .order_by("resolved_at")
    )
    rmap: dict[str, list] = {}
    for r in miei:
        rmap.setdefault(str(r.missione_id), []).append({
            "id": str(r.id),
            "evento_id": r.evento_id,
            "evento_titolo": r.evento.titolo if r.evento_id else None,
            "is_primo": r.is_primo,
            "reward_crediti": str(r.reward_crediti),
            "reward_prestigio": r.reward_prestigio,
            "ricompensa_reclamata": r.ricompensa_reclamata,
            "reclamata_at": r.reclamata_at.isoformat() if r.reclamata_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })

    # solo_primo già risolti da altri (per evento) — per filtrare effettuabili
    solo_primo_ids = [m.id for m in missioni if m.premio_solo_primo]
    presi = set()
    if solo_primo_ids:
        for mid, eid in MissioneRisoluzione.objects.filter(
            missione_id__in=solo_primo_ids
        ).values_list("missione_id", "evento_id"):
            presi.add((str(mid), eid))

    korp_ids = set(get_active_korp_ids(personaggio))
    rows = []
    for m in missioni:
        if not personaggio_puo_svolgere(m, personaggio):
            continue
        miei_r = rmap.get(str(m.id), [])
        svolta = len(miei_r) > 0
        eventi_ids = list(m.eventi.values_list("id", flat=True))
        # effettuabile se esiste almeno un evento senza mia risoluzione
        # e, se solo_primo, senza risoluzione altrui
        effettuabile = False
        for eid in eventi_ids:
            gia_mia = any(r["evento_id"] == eid for r in miei_r)
            if gia_mia:
                continue
            if m.premio_solo_primo and (str(m.id), eid) in presi:
                continue
            effettuabile = True
            break
        if not effettuabile and not svolta:
            # nessuna risoluzione mia e non effettuabile → nascondi (es. solo_primo presa)
            if m.premio_solo_primo:
                continue

        view = ricompensa_per_visualizzazione(m, personaggio, is_primo=True)
        rows.append({
            "id": str(m.id),
            "sync_id": str(m.sync_id),
            "titolo": m.titolo,
            "descrizione": m.descrizione,
            "korp_id": m.korp_id,
            "korp_nome": m.korp.nome if m.korp_id else None,
            "esclusiva": m.esclusiva,
            "tipo_risoluzione": m.tipo_risoluzione,
            "premio_solo_primo": m.premio_solo_primo,
            "attiva": m.attiva,
            "ordine": m.ordine,
            "eventi_ids": eventi_ids,
            "svolta": svolta,
            "effettuabile": effettuabile,
            "risoluzioni": miei_r,
            "is_korp_bonus": view["is_korp_bonus"],
            "fattore_applicato": str(view["fattore_applicato"]),
            "reward_crediti": str(view["reward_crediti"]),
            "reward_prestigio": view["reward_prestigio"],
            "reward_crediti_base": str(view["reward_crediti_base"]),
            "reward_prestigio_base": view["reward_prestigio_base"],
        })

    def sort_key(row):
        is_mine = row["korp_id"] in korp_ids if row["korp_id"] else False
        return (
            0 if is_mine else 1,
            1 if row["svolta"] else 0,
            0 if row["effettuabile"] else 1,
            row["ordine"],
            row["titolo"].lower(),
        )

    rows.sort(key=sort_key)
    return rows
