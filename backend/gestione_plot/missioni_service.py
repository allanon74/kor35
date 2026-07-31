"""
Logica business per Task/Missioni: calcolo ricompense, risoluzione, claim, riepilogo evento.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from personaggi.models import Carriera, Personaggio, get_active_korp_ids

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


def calcola_ricompensa_base(missione: Missione, *, is_primo: bool) -> tuple[Decimal, int]:
    """Premio base (senza fattore KORP) considerando primo/successivi e malus/bonus."""
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
    """
    Se il PG appartiene alla KORP della task, moltiplica per fattore_task.
    Ritorna (cr, pr, is_korp_bonus, fattore_applicato).
    """
    if not missione.korp_id or not personaggio:
        return _q2(cr), int(pr), False, Decimal("1.00")
    if not personaggio_ha_korp(personaggio, missione.korp_id):
        return _q2(cr), int(pr), False, Decimal("1.00")
    fattore = fattore_for_korp(missione.korp)
    cr2 = _q2(cr * fattore)
    pr2 = int((Decimal(pr) * fattore).to_integral_value(rounding=ROUND_HALF_UP))
    return cr2, pr2, True, fattore


def ricompensa_per_visualizzazione(
    missione: Missione,
    personaggio: Personaggio | None,
    *,
    is_primo: bool = True,
) -> dict:
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


def _is_primo_per_missione_evento(missione_id, evento_id) -> bool:
    return not MissioneRisoluzione.objects.filter(
        missione_id=missione_id,
        evento_id=evento_id,
    ).exists()


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
) -> MissioneRisoluzione:
    """
    Crea una risoluzione (una sola per PG/task/evento).
    Solleva ValueError se già assegnata o se task non collegata all'evento.
    """
    if not MissioneEvento.objects.filter(missione=missione, evento=evento).exists():
        raise ValueError("La task non è associata a questo evento.")

    if MissioneRisoluzione.objects.filter(
        missione=missione,
        evento=evento,
        personaggio=personaggio,
    ).exists():
        raise ValueError("Questo personaggio ha già risolto questa task per l'evento.")

    is_primo = _is_primo_per_missione_evento(missione.id, evento.id)
    cr, pr = calcola_ricompensa_base(missione, is_primo=is_primo)
    cr, pr, _, _ = applica_fattore_korp(missione, personaggio, cr, pr)

    return MissioneRisoluzione.objects.create(
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


@transaction.atomic
def reclama_ricompensa(risoluzione: MissioneRisoluzione) -> MissioneRisoluzione:
    if risoluzione.ricompensa_reclamata:
        raise ValueError("Ricompensa già reclamata.")
    cr = _q2(risoluzione.reward_crediti)
    pr = int(risoluzione.reward_prestigio or 0)
    if cr == ZERO and pr == 0:
        risoluzione.ricompensa_reclamata = True
        risoluzione.reclamata_at = timezone.now()
        risoluzione.save(update_fields=["ricompensa_reclamata", "reclamata_at", "updated_at"])
        return risoluzione

    pg = risoluzione.personaggio
    titolo = risoluzione.missione.titolo
    if cr > ZERO:
        pg.modifica_crediti(cr, f"Task «{titolo}» — ricompensa Crediti")
    if pr > 0:
        pg.modifica_prestigio(pr, f"Task «{titolo}» — ricompensa Prestigio")

    risoluzione.ricompensa_reclamata = True
    risoluzione.reclamata_at = timezone.now()
    risoluzione.save(update_fields=["ricompensa_reclamata", "reclamata_at", "updated_at"])
    return risoluzione


def riepilogo_premi_evento(evento: Evento) -> list[dict]:
    """
    Per ogni KORP: Cr/Pr delle task di quella KORP × fattore, più Cr/Pr delle task non-KORP.
    """
    missioni = list(
        Missione.objects.filter(eventi=evento, attiva=True)
        .select_related("korp")
        .order_by("ordine", "titolo")
    )
    generiche = [m for m in missioni if not m.korp_id]
    cr_gen = sum((_q2(m.reward_crediti) for m in generiche), ZERO)
    pr_gen = sum((int(m.reward_prestigio or 0) for m in generiche), 0)

    korps = list(
        Carriera.objects.filter(tipo_carriera__codice="korp")
        .order_by("nome")
    )
    out = []
    for korp in korps:
        di_korp = [m for m in missioni if m.korp_id == korp.id]
        fattore = fattore_for_korp(korp)
        cr_k = sum((_q2(m.reward_crediti) for m in di_korp), ZERO)
        pr_k = sum((int(m.reward_prestigio or 0) for m in di_korp), 0)
        out.append({
            "korp_id": korp.id,
            "korp_nome": korp.nome,
            "fattore_task": fattore,
            "crediti_korp": _q2(cr_k * fattore),
            "prestigio_korp": int((Decimal(pr_k) * fattore).to_integral_value(rounding=ROUND_HALF_UP)),
            "crediti_non_korp": _q2(cr_gen),
            "prestigio_non_korp": pr_gen,
            "n_task_korp": len(di_korp),
            "n_task_non_korp": len(generiche),
        })
    return out


def annota_missione_per_pg(missione: Missione, personaggio: Personaggio | None, risoluzioni_map: dict) -> dict:
    """Serializzazione arricchita per lista giocatore."""
    view = ricompensa_per_visualizzazione(missione, personaggio, is_primo=True)
    # risoluzioni del PG per eventi collegati
    miei = risoluzioni_map.get(str(missione.id), [])
    svolta = len(miei) > 0
    reclamabile = any(not r["ricompensa_reclamata"] for r in miei)
    return {
        "id": str(missione.id),
        "sync_id": str(missione.sync_id),
        "titolo": missione.titolo,
        "descrizione": missione.descrizione,
        "korp_id": missione.korp_id,
        "korp_nome": missione.korp.nome if missione.korp_id else None,
        "tipo_risoluzione": missione.tipo_risoluzione,
        "premio_solo_primo": missione.premio_solo_primo,
        "attiva": missione.attiva,
        "ordine": missione.ordine,
        "eventi_ids": list(missione.eventi.values_list("id", flat=True)),
        "svolta": svolta,
        "reclamabile": reclamabile,
        "risoluzioni": miei,
        "is_korp_bonus": view["is_korp_bonus"],
        "fattore_applicato": str(view["fattore_applicato"]),
        "reward_crediti": str(view["reward_crediti"]),
        "reward_prestigio": view["reward_prestigio"],
        "reward_crediti_base": str(view["reward_crediti_base"]),
        "reward_prestigio_base": view["reward_prestigio_base"],
    }


def lista_missioni_per_personaggio(personaggio: Personaggio) -> list[dict]:
    missioni = list(
        Missione.objects.filter(attiva=True)
        .select_related("korp")
        .prefetch_related("eventi")
        .order_by("ordine", "titolo")
    )
    risoluzioni = (
        MissioneRisoluzione.objects.filter(personaggio=personaggio, missione__in=missioni)
        .select_related("evento", "missione")
        .order_by("resolved_at")
    )
    rmap: dict[str, list] = {}
    for r in risoluzioni:
        key = str(r.missione_id)
        rmap.setdefault(key, []).append({
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

    rows = [annota_missione_per_pg(m, personaggio, rmap) for m in missioni]
    # KORP del PG in cima, poi altre; svolte in fondo al gruppo
    korp_ids = set(get_active_korp_ids(personaggio))

    def sort_key(row):
        is_mine = row["korp_id"] in korp_ids if row["korp_id"] else False
        return (0 if is_mine else 1, 1 if row["svolta"] else 0, row["ordine"], row["titolo"].lower())

    rows.sort(key=sort_key)
    return rows
