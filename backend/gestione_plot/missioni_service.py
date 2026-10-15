"""
Logica Task/Missioni: ricompense, esclusiva, solo-primo, claim auto + notifica, riepilogo evento.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from personaggi.models import Carriera, Messaggio, Personaggio, get_active_korp_ids

from .models import Evento, Missione, MissioneEvento, MissioneProposta, MissioneRisoluzione

ZERO = Decimal("0.00")


def _q2(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fattore_crediti_for_korp(korp) -> Decimal:
    if not korp:
        return Decimal("1.00")
    valore = getattr(korp, "fattore_task_crediti", None)
    return _q2(Decimal("1.00") if valore is None else valore)


def fattore_prestigio_for_korp(korp) -> Decimal:
    """Moltiplicatore Prestigio della KORP, indipendente da quello dei Crediti."""
    if not korp:
        return Decimal("1.00")
    valore = getattr(korp, "fattore_task_prestigio", None)
    return _q2(Decimal("1.00") if valore is None else valore)


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
) -> tuple[Decimal, int, bool, Decimal, Decimal]:
    """Fattori KORP (Crediti e Prestigio separati) solo se PG membro della KORP della task.

    ``is_bonus`` (sovrapagata) è True se almeno uno dei due fattori è > 1:
    il giocatore non vede il mittente KORP, ma le task della propria KORP
    pagate di più restano evidenziate.
    """
    uno = Decimal("1.00")
    if not missione.korp_id or not personaggio:
        return _q2(cr), int(pr), False, uno, uno
    if not personaggio_ha_korp(personaggio, missione.korp_id):
        return _q2(cr), int(pr), False, uno, uno
    fattore_cr = fattore_crediti_for_korp(missione.korp)
    fattore_pr = fattore_prestigio_for_korp(missione.korp)
    cr2 = _q2(cr * fattore_cr)
    pr2 = int((Decimal(pr) * fattore_pr).to_integral_value(rounding=ROUND_HALF_UP))
    is_bonus = fattore_cr > uno or fattore_pr > uno
    return cr2, pr2, is_bonus, fattore_cr, fattore_pr


def ricompensa_per_visualizzazione(missione, personaggio, *, is_primo=True) -> dict:
    cr, pr = calcola_ricompensa_base(missione, is_primo=is_primo)
    cr2, pr2, is_bonus, fattore_cr, fattore_pr = applica_fattore_korp(missione, personaggio, cr, pr)
    return {
        "reward_crediti": cr2,
        "reward_prestigio": pr2,
        "reward_crediti_base": cr,
        "reward_prestigio_base": pr,
        "is_korp_bonus": is_bonus,
        "fattore_crediti_applicato": fattore_cr,
        "fattore_prestigio_applicato": fattore_pr,
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
        pg.modifica_crediti(cr, f"Task «{titolo}» — ricompensa Crediti", conto="DEPOSITO")
    if pr > 0:
        pg.modifica_prestigio(pr, f"Task «{titolo}» — ricompensa Prestigio")
    allineamento = getattr(risoluzione.missione, "allineamento", None) or Missione.ALLINEAMENTO_GRIGIA
    pg.modifica_punteggio_allineamento(
        allineamento,
        1,
        f"Task «{titolo}» — allineamento {allineamento.lower()}",
    )
    risoluzione.ricompensa_reclamata = True
    risoluzione.reclamata_at = timezone.now()
    risoluzione.save(update_fields=["ricompensa_reclamata", "reclamata_at", "updated_at"])
    if notifica:
        _notifica_ricompensa(risoluzione)
    from personaggi.contratti_service import on_task_reclamata

    on_task_reclamata(risoluzione)
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
    link = MissioneEvento.objects.filter(missione=missione, evento=evento).first()
    if not link:
        raise ValueError("La task non è associata a questo evento.")
    if not missione.attiva:
        raise ValueError("La task è disattivata nel catalogo.")
    if not link.attiva:
        raise ValueError("La task è disattivata per questo evento.")
    if not evento.partecipanti.filter(pk=personaggio.pk).exists():
        raise ValueError("Il personaggio non è iscritto a questo evento.")
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
    cr, pr, _, _, _ = applica_fattore_korp(missione, personaggio, cr, pr)

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


def missioni_attive_evento(evento: Evento) -> list[Missione]:
    """Task che entrano nel conteggio: attive in catalogo e attive per l'evento."""
    return list(
        Missione.objects.filter(
            attiva=True,
            evento_links__evento=evento,
            evento_links__attiva=True,
        )
        .select_related("korp")
        .distinct()
    )


def riepilogo_premi_evento(evento: Evento) -> list[dict]:
    """
    Per KORP X:
    - di Korp = task di X × fattore_crediti_X (Cr) e × fattore_prestigio_X (Pr)
    - non di Korp = generiche + altre KORP non esclusive (senza fattori)
    - totale = quanto incassa un PG di X svolgendo tutte le task che gli sono aperte
    """
    missioni = missioni_attive_evento(evento)
    korps = list(Carriera.objects.filter(tipo_carriera__codice="korp").order_by("nome"))
    out = []
    for korp in korps:
        di_korp = [m for m in missioni if m.korp_id == korp.id]
        non_di_korp = [
            m
            for m in missioni
            if m.korp_id != korp.id and not m.esclusiva
        ]
        fattore_cr = fattore_crediti_for_korp(korp)
        fattore_pr = fattore_prestigio_for_korp(korp)
        cr_k = sum((_q2(m.reward_crediti) for m in di_korp), ZERO)
        pr_k = sum((int(m.reward_prestigio or 0) for m in di_korp), 0)
        cr_n = sum((_q2(m.reward_crediti) for m in non_di_korp), ZERO)
        pr_n = sum((int(m.reward_prestigio or 0) for m in non_di_korp), 0)
        cr_korp = _q2(cr_k * fattore_cr)
        pr_korp = int((Decimal(pr_k) * fattore_pr).to_integral_value(rounding=ROUND_HALF_UP))
        out.append({
            "korp_id": korp.id,
            "korp_nome": korp.nome,
            "fattore_task_crediti": fattore_cr,
            "fattore_task_prestigio": fattore_pr,
            "crediti_korp": cr_korp,
            "prestigio_korp": pr_korp,
            "crediti_non_korp": _q2(cr_n),
            "prestigio_non_korp": pr_n,
            "n_task_korp": len(di_korp),
            "n_task_non_korp": len(non_di_korp),
            "crediti_totale": _q2(cr_korp + cr_n),
            "prestigio_totale": pr_korp + pr_n,
            "n_task_totale": len(di_korp) + len(non_di_korp),
        })
    return out


def totali_task_evento(evento: Evento, righe_korp: list[dict] | None = None) -> dict:
    """Totali complessivi dello specchietto task di un evento (riga «Totale» staff).

    - ``crediti_base`` / ``prestigio_base``: somma dei premi di catalogo delle task
      conteggiate, senza moltiplicatori KORP.
    - ``crediti_max`` / ``prestigio_max``: miglior totale ottenibile da un PG, cioè
      il massimo tra i totali delle singole KORP.
    - i contatori ``n_task_spente_*`` spiegano perché alcune task collegate
      all'evento non entrano nei totali.
    """
    missioni = missioni_attive_evento(evento)
    righe = riepilogo_premi_evento(evento) if righe_korp is None else righe_korp
    links = list(MissioneEvento.objects.filter(evento=evento).select_related("missione"))
    spente_evento = [lk for lk in links if not lk.attiva]
    spente_catalogo = [lk for lk in links if lk.attiva and not lk.missione.attiva]
    return {
        "n_task_collegate": len(links),
        "n_task_attive": len(missioni),
        "n_task_spente_evento": len(spente_evento),
        "n_task_spente_catalogo": len(spente_catalogo),
        "crediti_base": sum((_q2(m.reward_crediti) for m in missioni), ZERO),
        "prestigio_base": sum((int(m.reward_prestigio or 0) for m in missioni), 0),
        "crediti_max": max((_q2(r["crediti_totale"]) for r in righe), default=ZERO),
        "prestigio_max": max((int(r["prestigio_totale"]) for r in righe), default=0),
    }


def riepilogo_task_evento(evento: Evento) -> dict:
    """Specchietto staff completo: righe per KORP + totali dell'evento."""
    righe = riepilogo_premi_evento(evento)
    return {"korps": righe, "totali": totali_task_evento(evento, righe)}


def eventi_attivi_ids():
    """Eventi ufficialmente in corso (Inizia evento senza Termina)."""
    return list(
        Evento.objects.filter(
            started_at__isnull=False,
            ended_at__isnull=True,
            archiviato_at__isnull=True,
        )
        .values_list("id", flat=True)
    )


def eventi_attivi_per_personaggio(personaggio: Personaggio) -> list[int]:
    """Eventi in corso in cui il PG è iscritto come partecipante."""
    attivi = eventi_attivi_ids()
    if not attivi or not personaggio:
        return []
    return list(
        Evento.objects.filter(id__in=attivi, partecipanti=personaggio)
        .values_list("id", flat=True)
    )


def set_missione_attiva_evento(missione: Missione, evento: Evento, attiva: bool) -> MissioneEvento:
    """Attiva/disattiva una task per un evento (stato live, default True)."""
    if evento.archiviato_at:
        raise ValueError("Plot archiviato: sola consultazione.")
    link = MissioneEvento.objects.filter(missione=missione, evento=evento).first()
    if not link:
        raise ValueError("La task non è associata a questo evento.")
    wanted = bool(attiva)
    if link.attiva != wanted:
        link.attiva = wanted
        link.save(update_fields=["attiva", "updated_at"])
    return link


def _proposta_pubblica(proposta: MissioneProposta | None) -> dict | None:
    if proposta is None:
        return None
    return {
        "id": str(proposta.id),
        "stato": proposta.stato,
        "testo": proposta.testo,
        "messaggio_rifiuto": proposta.messaggio_rifiuto or "",
        "evento_id": proposta.evento_id,
        "created_at": proposta.created_at.isoformat() if proposta.created_at else None,
    }


def _scegli_proposta(candidati: list[MissioneProposta]) -> MissioneProposta | None:
    """Preferisce la proposta ancora aperta, altrimenti la più recente."""
    if not candidati:
        return None
    aperte = [p for p in candidati if p.stato == MissioneProposta.STATO_IN_ATTESA]
    pool = aperte or candidati
    return max(pool, key=lambda p: p.created_at or timezone.now())


def lista_missioni_per_personaggio(personaggio: Personaggio) -> list[dict]:
    """
    Visibili al giocatore solo le task legate a eventi ATTIVI in cui il PG
    è iscritto, con link MissioneEvento.attiva e catalogo Missione.attiva,
    non esclusive (oppure esclusive della propria KORP).
    Il payload giocatore non include il mittente KORP né l'allineamento
    (luminosa/oscura/grigia): evidenza solo le task sovrapagate (fattore > 1)
    della propria KORP.

    Una risoluzione non spegne la task per gli altri, salvo ``premio_solo_primo``.
    Le task già risolte dal PG restano nell'elenco (sezione completate) anche
    se il link evento viene spento dopo.
    """
    attivi = set(eventi_attivi_per_personaggio(personaggio))
    if not attivi:
        return []

    visibili = Missione.objects.filter(
        attiva=True,
        evento_links__evento_id__in=attivi,
        evento_links__attiva=True,
    )
    completate_pg = Missione.objects.filter(
        risoluzioni__personaggio=personaggio,
        risoluzioni__evento_id__in=attivi,
        evento_links__evento_id__in=attivi,
    )
    missioni = list(
        (visibili | completate_pg)
        .select_related("korp")
        .prefetch_related("evento_links")
        .distinct()
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

    solo_primo_ids = [m.id for m in missioni if m.premio_solo_primo]
    presi = set()
    if solo_primo_ids:
        for mid, eid in MissioneRisoluzione.objects.filter(
            missione_id__in=solo_primo_ids,
            evento_id__in=attivi,
        ).values_list("missione_id", "evento_id"):
            presi.add((str(mid), eid))

    proposte_per_missione: dict[str, list[MissioneProposta]] = {}
    if missioni:
        for proposta in MissioneProposta.objects.filter(
            personaggio=personaggio,
            missione__in=missioni,
            evento_id__in=attivi,
        ):
            proposte_per_missione.setdefault(str(proposta.missione_id), []).append(proposta)

    rows = []
    for m in missioni:
        if not personaggio_puo_svolgere(m, personaggio):
            continue
        miei_r = [r for r in rmap.get(str(m.id), []) if r["evento_id"] in attivi]
        risolti_eventi = {r["evento_id"] for r in miei_r}
        # Link attivo (catalogo acceso) oppure evento già risolto da questo PG,
        # anche se lo staff ha poi spento il link: la completata resta in elenco.
        eventi_ids = []
        for link in m.evento_links.all():
            if link.evento_id not in attivi:
                continue
            gia_risolta = link.evento_id in risolti_eventi
            if gia_risolta or (m.attiva and link.attiva):
                eventi_ids.append(link.evento_id)
        if not eventi_ids:
            continue
        svolta = len(miei_r) > 0
        effettuabile = False
        evento_soluzione_id = None
        for eid in eventi_ids:
            gia_mia = eid in risolti_eventi
            if gia_mia:
                continue
            if m.premio_solo_primo and (str(m.id), eid) in presi:
                continue
            if not m.attiva:
                continue
            effettuabile = True
            evento_soluzione_id = eid
            break
        # Sparisce per gli altri solo se è «premio solo al primo» e già presa.
        # Una risoluzione ordinaria non toglie la task a chi non l'ha ancora fatta.
        if not effettuabile and not svolta:
            continue

        view = ricompensa_per_visualizzazione(m, personaggio, is_primo=True)
        proposte_m = [
            p for p in proposte_per_missione.get(str(m.id), [])
            if p.evento_id in eventi_ids
        ]
        rows.append({
            "id": str(m.id),
            "sync_id": str(m.sync_id),
            "titolo": m.titolo,
            "descrizione": m.descrizione,
            "tipo_risoluzione": m.tipo_risoluzione,
            "premio_solo_primo": m.premio_solo_primo,
            "attiva": m.attiva,
            "ordine": m.ordine,
            "eventi_ids": eventi_ids,
            "evento_soluzione_id": evento_soluzione_id,
            "svolta": svolta,
            "effettuabile": effettuabile,
            "risoluzioni": miei_r,
            "proposta": _proposta_pubblica(_scegli_proposta(proposte_m)),
            "is_korp_bonus": view["is_korp_bonus"],
            "fattore_crediti_applicato": str(view["fattore_crediti_applicato"]),
            "fattore_prestigio_applicato": str(view["fattore_prestigio_applicato"]),
            "reward_crediti": str(view["reward_crediti"]),
            "reward_prestigio": view["reward_prestigio"],
            "reward_crediti_base": str(view["reward_crediti_base"]),
            "reward_prestigio_base": view["reward_prestigio_base"],
        })

    def sort_key(row):
        return (
            0 if row["is_korp_bonus"] else 1,
            1 if row["svolta"] else 0,
            0 if row["effettuabile"] else 1,
            row["ordine"],
            row["titolo"].lower(),
        )

    rows.sort(key=sort_key)
    return rows


def _evento_aperto_per_soluzione(missione: Missione, evento: Evento, personaggio: Personaggio) -> None:
    """Controlli condivisi prima di accettare una soluzione dal giocatore."""
    if evento.ended_at is not None or evento.started_at is None:
        raise ValueError("La task si può segnare solo mentre l'evento è in corso.")
    if not evento.partecipanti.filter(pk=personaggio.pk).exists():
        raise ValueError("Il personaggio non è iscritto a questo evento.")
    link = MissioneEvento.objects.filter(missione=missione, evento=evento).first()
    if not link:
        raise ValueError("La task non è associata a questo evento.")
    if not missione.attiva or not link.attiva:
        raise ValueError("La task non è attiva per questo evento.")
    if not personaggio_puo_svolgere(missione, personaggio):
        raise ValueError("Non puoi svolgere questa task.")
    if MissioneRisoluzione.objects.filter(
        missione=missione, evento=evento, personaggio=personaggio
    ).exists():
        raise ValueError("Hai già completato questa task.")
    if missione.premio_solo_primo and not _is_primo(missione.id, evento.id):
        raise ValueError("Questa task è già stata risolta da un altro personaggio.")


def serializza_proposta(proposta: MissioneProposta) -> dict:
    missione = proposta.missione
    return {
        "id": str(proposta.id),
        "stato": proposta.stato,
        "testo": proposta.testo,
        "messaggio_rifiuto": proposta.messaggio_rifiuto or "",
        "created_at": proposta.created_at.isoformat() if proposta.created_at else None,
        "updated_at": proposta.updated_at.isoformat() if proposta.updated_at else None,
        "risposta_at": proposta.risposta_at.isoformat() if proposta.risposta_at else None,
        "missione_id": str(proposta.missione_id),
        "missione_titolo": missione.titolo if missione else "",
        "tipo_risoluzione": missione.tipo_risoluzione if missione else "",
        "evento_id": proposta.evento_id,
        "evento_titolo": proposta.evento.titolo if proposta.evento_id else "",
        "personaggio_id": proposta.personaggio_id,
        "personaggio_nome": proposta.personaggio.nome if proposta.personaggio_id else "",
        "risoluzione_id": str(proposta.risoluzione_id) if proposta.risoluzione_id else None,
    }


@transaction.atomic
def invia_soluzione(
    *,
    missione: Missione,
    evento: Evento,
    personaggio: Personaggio,
    testo: str,
) -> MissioneProposta:
    """
    Il giocatore segna la soluzione. Per le task manuali (generali) è l'unico
    canale del personaggio; per quest, tecniche e post è facoltativo.
    Non crea la risoluzione e non accredita il premio.
    """
    testo = (testo or "").strip()
    if not testo:
        raise ValueError("Scrivi la soluzione prima di inviarla.")
    if len(testo) > 4000:
        raise ValueError("La soluzione è troppo lunga.")
    _evento_aperto_per_soluzione(missione, evento, personaggio)
    esistente = (
        MissioneProposta.objects.select_for_update()
        .filter(
            missione=missione,
            evento=evento,
            personaggio=personaggio,
            stato=MissioneProposta.STATO_IN_ATTESA,
        )
        .first()
    )
    if esistente:
        esistente.testo = testo
        esistente.save(update_fields=["testo", "updated_at"])
        return esistente
    return MissioneProposta.objects.create(
        missione=missione,
        evento=evento,
        personaggio=personaggio,
        testo=testo,
        stato=MissioneProposta.STATO_IN_ATTESA,
    )


def lista_proposte(*, stato: str | None = None, evento_id=None) -> list[dict]:
    qs = MissioneProposta.objects.select_related("missione", "evento", "personaggio")
    if stato:
        qs = qs.filter(stato=stato)
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    return [serializza_proposta(p) for p in qs.order_by("-created_at")[:200]]


def _notifica_rifiuto(proposta: MissioneProposta, messaggio: str, mittente) -> None:
    pg = proposta.personaggio
    titolo = proposta.missione.titolo
    Messaggio.objects.create(
        mittente=mittente,
        tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
        destinatario_personaggio=pg,
        titolo=f"Soluzione non accettata: {titolo}"[:150],
        testo=(
            f"La soluzione inviata per la task «{titolo}» non è stata accettata.\n\n"
            f"{messaggio.strip()}"
        ),
        campagna=pg.campagna,
        is_staff_message=True,
    )


@transaction.atomic
def accetta_proposta(proposta: MissioneProposta, *, utente) -> MissioneProposta:
    proposta = (
        MissioneProposta.objects.select_for_update()
        .select_related("missione", "evento", "personaggio")
        .get(pk=proposta.pk)
    )
    if proposta.stato != MissioneProposta.STATO_IN_ATTESA:
        raise ValueError("Questa soluzione è già stata gestita.")
    ris = assegna_risoluzione(
        missione=proposta.missione,
        evento=proposta.evento,
        personaggio=proposta.personaggio,
        note=proposta.testo,
        auto_claim=True,
    )
    proposta.stato = MissioneProposta.STATO_ACCETTATA
    proposta.risoluzione = ris
    proposta.risposta_at = timezone.now()
    proposta.risposta_da = utente
    proposta.save(update_fields=[
        "stato", "risoluzione", "risposta_at", "risposta_da", "updated_at",
    ])
    return proposta


@transaction.atomic
def rifiuta_proposta(proposta: MissioneProposta, *, utente, messaggio: str) -> MissioneProposta:
    messaggio = (messaggio or "").strip()
    if not messaggio:
        raise ValueError("Scrivi il messaggio da inviare al giocatore.")
    if len(messaggio) > 2000:
        raise ValueError("Il messaggio è troppo lungo.")
    proposta = (
        MissioneProposta.objects.select_for_update()
        .select_related("missione", "evento", "personaggio")
        .get(pk=proposta.pk)
    )
    if proposta.stato != MissioneProposta.STATO_IN_ATTESA:
        raise ValueError("Questa soluzione è già stata gestita.")
    proposta.stato = MissioneProposta.STATO_RIFIUTATA
    proposta.messaggio_rifiuto = messaggio
    proposta.risposta_at = timezone.now()
    proposta.risposta_da = utente
    proposta.save(update_fields=[
        "stato", "messaggio_rifiuto", "risposta_at", "risposta_da", "updated_at",
    ])
    _notifica_rifiuto(proposta, messaggio, utente)
    return proposta
