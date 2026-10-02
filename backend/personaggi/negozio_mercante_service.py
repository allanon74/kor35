"""
Acquisti, vendite e listino negozi mercante.
"""
from __future__ import annotations

import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from personaggi.negozio_mercante_apertura import negozio_e_aperto
from personaggi.negozio_mercante_models import (
    STOCK_DISPONIBILE,
    STOCK_VENDUTO,
    VOCE_ABILITA,
    VOCE_CERIMONIALE,
    VOCE_CONSUMABILE,
    VOCE_INFUSIONE,
    VOCE_OGGETTO,
    VOCE_OGGETTO_BASE,
    VOCE_SERIE,
    VOCE_TESSITURA,
    NegozioMercante,
    NegozioMercanteBundle,
    NegozioMercanteMovimento,
    NegozioMercantePrestito,
    NegozioMercanteStock,
    NegozioMercanteVoce,
    NEGOZIO_TIPO_CORPORATIVO,
    PRESTITO_ATTIVO,
    PRESTITO_RESTITUITO,
)
from personaggi.models import (
    SCELTA_RISULTATO_AUMENTO,
    SLOT_CORPO_CHOICES,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MUTAZIONE,
    ConsumabilePersonaggio,
    Oggetto,
    Personaggio,
    PersonaggioAbilita,
    PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
)


def _registra_movimento(
    negozio, *, tipo, importo, personaggio=None, voce=None, stock=None, bundle=None, nota=""
):
    NegozioMercanteMovimento.objects.create(
        negozio=negozio,
        personaggio=personaggio,
        tipo=tipo,
        importo=Decimal(importo),
        saldo_dopo=negozio.saldo_crediti,
        nota=nota[:255],
        riferimento_voce=voce,
        riferimento_stock=stock,
        riferimento_bundle=bundle,
    )


def _aggiorna_saldo(
    negozio, delta: Decimal, *, tipo, personaggio=None, voce=None, stock=None, bundle=None, nota=""
):
    negozio.saldo_crediti = (negozio.saldo_crediti or Decimal("0")) + delta
    negozio.save(update_fields=["saldo_crediti", "updated_at"])
    _registra_movimento(
        negozio,
        tipo=tipo,
        importo=delta,
        personaggio=personaggio,
        voce=voce,
        stock=stock,
        bundle=bundle,
        nota=nota,
    )


def _config(negozio) -> dict:
    return negozio.get_config_economia()


MSG_NON_DISPONIBILE_LISTINO = "Non più disponibile."
MSG_ESAURITO_LISTINO = "Esaurito."
MSG_USATO_LISTINO = "Usato — prezzo di rivendita."
MSG_PRESTITO_NON_AMMESSO = (
    "Questo articolo non è prestabile in questo negozio "
    "(ammessi: oggetti, abilità, infusioni, tessiture, cerimoniali)."
)
MSG_LIMITE_PRESTITI = (
    "Hai già raggiunto il limite di oggetti in prestito da questo negozio. "
    "Restituiscili a fine evento prima di prenderne altri."
)
MSG_OGGETTO_IN_PRESTITO = "Questo oggetto è in prestito e non può essere ceduto o venduto."
MSG_NEGOZIO_SOLO_PRESTITI = "Questo negozio opera solo in modalità prestito: non acquista oggetti dai PG."


def voce_e_prestabile(voce: NegozioMercanteVoce) -> bool:
    """
    Prestiti ammessi: oggetti fisici (OGB/OGG/INF-istanza) oppure tecniche
    temporanee (ABL / INF ricetta / TES / CER). Esclusi consumabili, serie, bundle.
    """
    if voce.tipo_voce in (VOCE_OGGETTO_BASE, VOCE_OGGETTO, VOCE_ABILITA, VOCE_TESSITURA, VOCE_CERIMONIALE):
        return True
    if voce.tipo_voce == VOCE_INFUSIONE:
        return True
    return False


def prestito_attivo_per_oggetto(oggetto_id) -> NegozioMercantePrestito | None:
    if not oggetto_id:
        return None
    return (
        NegozioMercantePrestito.objects.filter(oggetto_id=oggetto_id, stato=PRESTITO_ATTIVO)
        .select_related("negozio")
        .first()
    )


def assert_oggetto_non_in_prestito(oggetto) -> None:
    if prestito_attivo_per_oggetto(getattr(oggetto, "pk", oggetto)):
        raise ValidationError(MSG_OGGETTO_IN_PRESTITO)


def conta_prestiti_attivi(negozio, personaggio) -> int:
    return NegozioMercantePrestito.objects.filter(
        negozio=negozio,
        personaggio=personaggio,
        stato=PRESTITO_ATTIVO,
    ).count()


def assert_limite_prestiti(negozio, personaggio, *, qty: int = 1) -> None:
    if not negozio.negozio_prestiti:
        return
    limite = max(1, int(negozio.limite_prestiti_per_personaggio or 1))
    if conta_prestiti_attivi(negozio, personaggio) + qty > limite:
        raise ValidationError(MSG_LIMITE_PRESTITI)


def registra_prestito(
    negozio,
    personaggio,
    *,
    oggetto=None,
    abilita=None,
    infusione=None,
    tessitura=None,
    cerimoniale=None,
    costo_noleggio: int = 0,
    voce=None,
    stock=None,
) -> NegozioMercantePrestito:
    if not any([oggetto, abilita, infusione, tessitura, cerimoniale]):
        raise ValidationError("Prestito incompleto: manca oggetto o tecnica.")
    return NegozioMercantePrestito.objects.create(
        negozio=negozio,
        personaggio=personaggio,
        oggetto=oggetto,
        abilita=abilita,
        infusione=infusione,
        tessitura=tessitura,
        cerimoniale=cerimoniale,
        voce=voce,
        stock=stock,
        costo_noleggio=max(0, int(costo_noleggio or 0)),
        stato=PRESTITO_ATTIVO,
        prestato_at=timezone.now(),
    )


def _smonta_se_necessario(oggetto, personaggio) -> None:
    """
    Prima della restituzione: libera montaggio (innesto/mutazione equipaggiato)
    e eventuale socketing (ospitato_su).
    """
    if oggetto is None:
        return
    update_fields = []
    if getattr(oggetto, "is_equipaggiato", False) or getattr(oggetto, "slot_corpo", None):
        oggetto.is_equipaggiato = False
        oggetto.slot_corpo = None
        update_fields.extend(["is_equipaggiato", "slot_corpo"])
    if getattr(oggetto, "ospitato_su_id", None):
        oggetto.ospitato_su = None
        update_fields.append("ospitato_su")
    if update_fields:
        update_fields.append("updated_at")
        oggetto.save(update_fields=update_fields)


def _revoca_tecnica_prestito(prestito) -> None:
    """Rimuove la tecnica temporanea assegnata col prestito."""
    pg = prestito.personaggio
    if prestito.abilita_id:
        from personaggi.models import PersonaggioAbilita

        PersonaggioAbilita.objects.filter(
            personaggio=pg, abilita_id=prestito.abilita_id
        ).delete()
    elif prestito.infusione_id:
        pg.infusioni_possedute.remove(prestito.infusione_id)
    elif prestito.tessitura_id:
        pg.tessiture_possedute.remove(prestito.tessitura_id)
    elif prestito.cerimoniale_id:
        pg.cerimoniali_posseduti.remove(prestito.cerimoniale_id)


@transaction.atomic
def restituisci_prestito(
    prestito: NegozioMercantePrestito,
    *,
    nota: str = "",
    forzato: bool = False,
) -> dict:
    """
    Restituisce un prestito attivo: smonta/riporta oggetto in magazzino
    oppure revoca la tecnica temporanea.
    """
    prestito = (
        NegozioMercantePrestito.objects.select_for_update(of=("self",))
        .select_related(
            "negozio",
            "oggetto",
            "voce",
            "stock",
            "personaggio",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
        )
        .get(pk=prestito.pk)
    )
    if prestito.stato != PRESTITO_ATTIVO:
        raise ValidationError("Questo prestito è già stato restituito.")

    negozio = prestito.negozio
    oggetto = prestito.oggetto
    personaggio = prestito.personaggio
    label = prestito.etichetta_prestito()

    if oggetto is not None:
        _smonta_se_necessario(oggetto, personaggio)
        if negozio.inventario_id:
            oggetto.sposta_in_inventario(negozio.inventario)

        if prestito.stock_id:
            stock = NegozioMercanteStock.objects.select_for_update(of=("self",)).get(
                pk=prestito.stock_id
            )
            stock.stato = STOCK_DISPONIBILE
            stock.save(update_fields=["stato", "updated_at"])
        elif prestito.voce_id and prestito.voce and prestito.voce.tipo_voce == VOCE_OGGETTO:
            voce = NegozioMercanteVoce.objects.select_for_update(of=("self",)).get(
                pk=prestito.voce_id
            )
            voce.oggetto = oggetto
            voce.attivo = True
            voce.save(update_fields=["oggetto", "attivo", "updated_at"])
        else:
            config = _config(negozio)
            val_ref = valore_riferimento_oggetto(oggetto, config)
            prezzo = max(0, int(prestito.costo_noleggio or 0)) or max(1, val_ref)
            NegozioMercanteStock.objects.create(
                negozio=negozio,
                oggetto=oggetto,
                prezzo_rivendita=prezzo,
                valore_riferimento=val_ref,
                stato=STOCK_DISPONIBILE,
            )
    else:
        _revoca_tecnica_prestito(prestito)

    now = timezone.now()
    prestito.stato = PRESTITO_RESTITUITO
    prestito.restituito_at = now
    prestito.nota_restituzione = (nota or ("restituzione forzata" if forzato else ""))[:255]
    prestito.save(
        update_fields=["stato", "restituito_at", "nota_restituzione", "updated_at"]
    )

    personaggio.aggiungi_log(
        f"Restituito «{label}» al negozio di prestiti «{negozio.nome}»."
    )
    return {
        "status": "success",
        "prestito_id": str(prestito.id),
        "oggetto_id": oggetto.id if oggetto is not None else None,
        "negozio_id": str(negozio.id),
    }


@transaction.atomic
def restituisci_prestito_oggetto(negozio, personaggio, oggetto_id, *, nota: str = "") -> dict:
    prestito = (
        NegozioMercantePrestito.objects.select_for_update(of=("self",))
        .filter(
            negozio=negozio,
            personaggio=personaggio,
            oggetto_id=oggetto_id,
            stato=PRESTITO_ATTIVO,
        )
        .first()
    )
    if not prestito:
        raise ValidationError("Nessun prestito attivo per questo oggetto in questo negozio.")
    return restituisci_prestito(prestito, nota=nota)


@transaction.atomic
def restituisci_prestito_da_id(negozio, personaggio, prestito_id, *, nota: str = "") -> dict:
    prestito = (
        NegozioMercantePrestito.objects.select_for_update(of=("self",))
        .filter(
            pk=prestito_id,
            negozio=negozio,
            personaggio=personaggio,
            stato=PRESTITO_ATTIVO,
        )
        .first()
    )
    if not prestito:
        raise ValidationError("Nessun prestito attivo trovato.")
    return restituisci_prestito(prestito, nota=nota)


@transaction.atomic
def restituisci_tutti_prestiti_attivi(*, negozio=None, nota: str = "fine evento") -> dict:
    """Restituisce tutti i prestiti attivi (opzionalmente filtrati per negozio)."""
    qs = NegozioMercantePrestito.objects.filter(stato=PRESTITO_ATTIVO).select_related(
        "negozio", "oggetto", "voce", "stock", "personaggio"
    )
    if negozio is not None:
        qs = qs.filter(negozio=negozio)
    restituiti = 0
    errori = []
    for prestito in list(qs):
        try:
            restituisci_prestito(prestito, nota=nota, forzato=True)
            restituiti += 1
        except ValidationError as exc:
            msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            errori.append({"prestito_id": str(prestito.id), "errore": msg})
    return {"restituiti": restituiti, "errori": errori}


def serializza_prestiti_attivi(negozio, personaggio=None) -> list[dict]:
    qs = (
        NegozioMercantePrestito.objects.filter(negozio=negozio, stato=PRESTITO_ATTIVO)
        .select_related(
            "oggetto",
            "personaggio",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
        )
        .order_by("-prestato_at")
    )
    if personaggio is not None:
        qs = qs.filter(personaggio=personaggio)
    return [
        {
            "id": str(p.id),
            "oggetto_id": p.oggetto_id,
            "oggetto_nome": p.etichetta_prestito(),
            "personaggio_id": p.personaggio_id,
            "personaggio_nome": p.personaggio.nome if p.personaggio_id else "",
            "costo_noleggio": p.costo_noleggio,
            "prestato_at": p.prestato_at.isoformat() if p.prestato_at else None,
            "tipo": (
                "oggetto"
                if p.oggetto_id
                else "abilita"
                if p.abilita_id
                else "infusione"
                if p.infusione_id
                else "tessitura"
                if p.tessitura_id
                else "cerimoniale"
                if p.cerimoniale_id
                else "altro"
            ),
        }
        for p in qs
    ]


def _inventario_corrente_pk(oggetto) -> int | None:
    inv = oggetto.inventario_corrente
    return inv.pk if inv else None


def valore_riferimento_oggetto(oggetto, config: dict) -> int:
    livello = max(0, int(getattr(oggetto, "livello", 0) or 0))
    base = int(config.get("cr_per_livello_oggetto") or 200)
    stored = int(getattr(oggetto, "costo_acquisto", 0) or 0)
    if stored > 0:
        return stored
    return max(base, livello * base) if livello else base


def _random_pct(config: dict, min_key: str, max_key: str) -> float:
    lo = float(config.get(min_key) or 0)
    hi = float(config.get(max_key) or lo)
    if hi < lo:
        lo, hi = hi, lo
    return random.uniform(lo, hi) / 100.0


def _voce_entita(voce: NegozioMercanteVoce):
    mapping = {
        VOCE_OGGETTO_BASE: voce.oggetto_base,
        VOCE_OGGETTO: voce.oggetto,
        VOCE_ABILITA: voce.abilita,
        VOCE_INFUSIONE: voce.infusione,
        VOCE_TESSITURA: voce.tessitura,
        VOCE_CERIMONIALE: voce.cerimoniale,
        VOCE_SERIE: voce.serie,
    }
    return mapping.get(voce.tipo_voce)


def _quantita_effettiva_serie(voce: NegozioMercanteVoce) -> int | None:
    """
    Disponibilità listino per voce SER.
    Con ammetti_duplicati: solo quantita_residua (None = illimitato).
    Altrimenti: min(quantita_residua, pezzi_rimanenti) oppure solo pezzi_rimanenti.
    """
    serie = voce.serie
    if serie is None:
        return 0
    pezzi = serie.pezzi_rimanenti  # None se ammetti_duplicati
    if pezzi is None:
        return voce.quantita_residua
    if voce.quantita_residua is None:
        return pezzi
    return min(int(voce.quantita_residua), int(pezzi))


def _assert_voce_globally_vendibile(entita) -> None:
    if entita is None:
        raise ValidationError("Voce catalogo incompleta.")
    if getattr(entita, "non_vendibile", False):
        raise ValidationError("Questo contenuto non è vendibile.")


def _tecnica_listino_extra(personaggio, tecnica) -> dict:
    from personaggi.models import Infusione, Tessitura, Cerimoniale

    if not isinstance(tecnica, (Infusione, Tessitura, Cerimoniale)):
        return {}
    ok, msg = personaggio.valida_acquisto_tecnica(tecnica)
    gia = False
    if isinstance(tecnica, Infusione):
        gia = personaggio.infusioni_possedute.filter(pk=tecnica.pk).exists()
    elif isinstance(tecnica, Tessitura):
        gia = personaggio.tessiture_possedute.filter(pk=tecnica.pk).exists()
    else:
        gia = personaggio.cerimoniali_posseduti.filter(pk=tecnica.pk).exists()
    return {
        "acquistabile": ok and not gia,
        "messaggio_usabilita": msg if not ok else ("" if not gia else "Già posseduta."),
        "gia_posseduta": gia,
    }


def _slot_permessi_codes(infusione) -> set[str] | None:
    if not infusione or not getattr(infusione, "slot_corpo_permessi", None):
        return None
    permessi = {
        s.strip()
        for s in infusione.slot_corpo_permessi.split(",")
        if s.strip()
    }
    return permessi or None


def _voce_consegna_istanza(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce != VOCE_INFUSIONE or voce.infusione_id is None:
        return False
    if voce.consegna_istanza:
        return True
    return voce.infusione.tipo_risultato == SCELTA_RISULTATO_AUMENTO


def _oggetto_e_aumento(oggetto) -> bool:
    return bool(oggetto) and oggetto.tipo_oggetto in (
        TIPO_OGGETTO_INNESTO,
        TIPO_OGGETTO_MUTAZIONE,
    )


def _e_innesto_corporeo(*, infusione=None, oggetto=None) -> bool:
    """Innesto (ATE) vs mutazione: tipo oggetto vince sulla classificazione infusione."""
    if oggetto is not None and oggetto.tipo_oggetto == TIPO_OGGETTO_INNESTO:
        return True
    if infusione is None:
        return False
    from personaggi.services import GestioneCraftingService

    return GestioneCraftingService._classifica_risultato_infusione(infusione) == "INNESTO"


def _voce_richiede_montaggio(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce == VOCE_OGGETTO:
        return _oggetto_e_aumento(voce.oggetto)
    if voce.tipo_voce == VOCE_INFUSIONE and voce.infusione_id:
        return voce.infusione.tipo_risultato == SCELTA_RISULTATO_AUMENTO
    return False


def _voce_permette_quantita_multipla(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce in (VOCE_OGGETTO_BASE, VOCE_CONSUMABILE, VOCE_SERIE):
        return True
    if voce.tipo_voce == VOCE_INFUSIONE and _voce_consegna_istanza(voce):
        # Aumenti corporei: una sola unità (montaggio unico).
        return voce.infusione.tipo_risultato != SCELTA_RISULTATO_AUMENTO
    return False


def _nome_voce_catalogo(voce: NegozioMercanteVoce) -> str:
    ent = _voce_entita(voce)
    return getattr(ent, "nome", None) or voce.consumabile_nome or "Articolo"


def _assert_stock_voce(voce: NegozioMercanteVoce, qty: int) -> None:
    if qty < 1:
        raise ValidationError("Quantità non valida.")
    if voce.quantita_residua is not None and voce.quantita_residua < qty:
        raise ValidationError(MSG_ESAURITO_LISTINO)


def _decrementa_stock_voce(voce: NegozioMercanteVoce, qty: int) -> None:
    _assert_stock_voce(voce, qty)
    if voce.quantita_residua is None:
        return
    voce.quantita_residua -= qty
    voce.save(update_fields=["quantita_residua", "updated_at"])


def _motivo_voce_non_acquistabile(voce: NegozioMercanteVoce, personaggio, *, qty: int = 1) -> str | None:
    """Messaggio se la voce non può essere consegnata (qty unità); None se ok."""
    if not voce.attivo:
        return MSG_NON_DISPONIBILE_LISTINO
    if voce.quantita_residua is not None and voce.quantita_residua < qty:
        return MSG_ESAURITO_LISTINO
    if qty > 1 and not _voce_permette_quantita_multipla(voce):
        return "Questa voce non supporta quantità multiple."

    if voce.tipo_voce == VOCE_OGGETTO:
        if not voce.oggetto_id:
            return MSG_NON_DISPONIBILE_LISTINO
        if _inventario_corrente_pk(voce.oggetto) != voce.negozio.inventario_id:
            return MSG_NON_DISPONIBILE_LISTINO
        if qty != 1:
            return "Gli oggetti unici si acquistano uno alla volta."
        return None

    if voce.tipo_voce == VOCE_SERIE:
        if not voce.serie_id:
            return "Voce catalogo incompleta."
        disponibili = _quantita_effettiva_serie(voce)
        if disponibili is not None and disponibili < qty:
            return MSG_ESAURITO_LISTINO
        return None

    if voce.tipo_voce == VOCE_ABILITA:
        if personaggio.abilita_possedute.filter(pk=voce.abilita_id).exists():
            return "Abilità già posseduta."
        return None

    if voce.tipo_voce in (VOCE_INFUSIONE, VOCE_TESSITURA, VOCE_CERIMONIALE):
        if voce.tipo_voce == VOCE_INFUSIONE and _voce_consegna_istanza(voce):
            return None
        ent = _voce_entita(voce)
        ok_u, msg_u = personaggio.valida_acquisto_tecnica(ent)
        if not ok_u:
            return msg_u or "Tecnica non acquistabile."
        if voce.tipo_voce == VOCE_INFUSIONE:
            if personaggio.infusioni_possedute.filter(pk=ent.pk).exists():
                return "Infusione già posseduta."
        elif voce.tipo_voce == VOCE_TESSITURA:
            if personaggio.tessiture_possedute.filter(pk=ent.pk).exists():
                return "Tessitura già posseduta."
        else:
            if personaggio.cerimoniali_posseduti.filter(pk=ent.pk).exists():
                return "Cerimoniale già posseduto."
        return None

    if voce.tipo_voce != VOCE_CONSUMABILE:
        ent = _voce_entita(voce)
        if ent is None and voce.tipo_voce != VOCE_CONSUMABILE:
            return "Voce catalogo incompleta."
        if voce.tipo_voce != VOCE_CONSUMABILE and getattr(ent, "non_vendibile", False):
            return "Questo contenuto non è vendibile."
    return None


def _consegna_unita_voce(
    negozio: NegozioMercante,
    voce: NegozioMercanteVoce,
    personaggio,
    *,
    slot_corpo: str | None = None,
    destinatario=None,
):
    """Consegna una singola unità della voce. Ritorna eventuale entità creata."""
    from datetime import timedelta

    from personaggi.services import GestioneCraftingService, GestioneOggettiService

    destinatario = destinatario or personaggio
    richiede_montaggio = _voce_richiede_montaggio(voce)
    consegna_istanza = _voce_consegna_istanza(voce)
    entita_creata = None

    if voce.tipo_voce == VOCE_OGGETTO_BASE:
        ob = voce.oggetto_base
        _assert_voce_globally_vendibile(ob)
        entita_creata = GestioneCraftingService.crea_istanza_da_oggetto_base(
            ob, personaggio, costo_acquisto=int(voce.prezzo_crediti)
        )
    elif voce.tipo_voce == VOCE_OGGETTO:
        og = voce.oggetto
        _assert_voce_globally_vendibile(og)
        if _inventario_corrente_pk(og) != negozio.inventario_id:
            raise ValidationError("Oggetto non più in vendita.")
        if richiede_montaggio:
            _monta_aumento_o_annulla(destinatario, og, slot_corpo)
        else:
            og.sposta_in_inventario(personaggio)
        voce.oggetto = None
        voce.attivo = False
        voce.save(update_fields=["oggetto", "attivo", "updated_at"])
        entita_creata = og
    elif voce.tipo_voce == VOCE_ABILITA:
        ab = voce.abilita
        _assert_voce_globally_vendibile(ab)
        if personaggio.abilita_possedute.filter(pk=ab.pk).exists():
            raise ValidationError("Abilità già posseduta.")
        PersonaggioAbilita.objects.create(
            personaggio=personaggio,
            abilita=ab,
            origine=PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
        )
    elif voce.tipo_voce == VOCE_INFUSIONE:
        t = voce.infusione
        _assert_voce_globally_vendibile(t)
        if consegna_istanza:
            entita_creata = GestioneOggettiService.crea_oggetto_da_infusione(
                t, destinatario if richiede_montaggio else personaggio
            )
            if richiede_montaggio:
                _monta_aumento_o_annulla(destinatario, entita_creata, slot_corpo)
        else:
            ok_u, msg_u = personaggio.valida_acquisto_tecnica(t)
            if not ok_u:
                raise ValidationError(msg_u)
            if personaggio.infusioni_possedute.filter(pk=t.pk).exists():
                raise ValidationError("Infusione già posseduta.")
            personaggio.infusioni_possedute.add(t)
    elif voce.tipo_voce == VOCE_TESSITURA:
        t = voce.tessitura
        _assert_voce_globally_vendibile(t)
        ok_u, msg_u = personaggio.valida_acquisto_tecnica(t)
        if not ok_u:
            raise ValidationError(msg_u)
        if personaggio.tessiture_possedute.filter(pk=t.pk).exists():
            raise ValidationError("Tessitura già posseduta.")
        personaggio.tessiture_possedute.add(t)
    elif voce.tipo_voce == VOCE_CERIMONIALE:
        t = voce.cerimoniale
        _assert_voce_globally_vendibile(t)
        ok_u, msg_u = personaggio.valida_acquisto_tecnica(t)
        if not ok_u:
            raise ValidationError(msg_u)
        if personaggio.cerimoniali_posseduti.filter(pk=t.pk).exists():
            raise ValidationError("Cerimoniale già posseduto.")
        personaggio.cerimoniali_posseduti.add(t)
    elif voce.tipo_voce == VOCE_SERIE:
        serie = voce.serie
        if serie is None:
            raise ValidationError("Voce catalogo incompleta.")
        from personaggi.qr_random_pool import applica_serie

        payload, err, override = applica_serie(
            personaggio=personaggio,
            serie=serie,
            qr_code=None,
        )
        if err:
            raise ValidationError(err)
        if override == "serie_esaurita":
            raise ValidationError(
                (payload or {}).get("messaggio") or MSG_ESAURITO_LISTINO
            )
        oggetto_id = (payload or {}).get("oggetto_id")
        if oggetto_id:
            entita_creata = Oggetto.objects.filter(pk=oggetto_id).first()
    elif voce.tipo_voce == VOCE_CONSUMABILE:
        tess = voce.consumabile_tessitura
        nome = voce.consumabile_nome or (tess.nome if tess else "Consumabile")
        livello = max(1, int(voce.consumabile_livello or 1))
        ConsumabilePersonaggio.objects.create(
            personaggio=personaggio,
            tessitura=tess,
            nome=nome,
            descrizione=(tess.testo if tess else "") or "",
            formula=(tess.formula if tess else "") or "",
            utilizzi_rimanenti=livello,
            data_scadenza=timezone.now().date() + timedelta(days=30),
        )
    else:
        raise ValidationError("Tipo voce non supportato.")
    return entita_creata


def _prepara_montaggio_voce(voce, personaggio, *, slot_corpo, destinatario_id):
    """Valida e ritorna (destinatario, slot) se la voce richiede montaggio."""
    if not _voce_richiede_montaggio(voce):
        return personaggio, None
    destinatario = _risolve_destinatario_montaggio(personaggio, destinatario_id)
    if not slot_corpo:
        raise ValidationError(
            "Per innesti e mutazioni indica lo slot corpo e, se diverso da te, "
            "il destinatario del montaggio."
        )
    inf_ref = voce.infusione
    if voce.tipo_voce == VOCE_OGGETTO and voce.oggetto_id:
        inf_ref = voce.oggetto.infusione_generatrice
    liberi = {
        s["code"]
        for s in slot_aumento_disponibili(
            destinatario, infusione=inf_ref, oggetto=voce.oggetto
        )
    }
    if slot_corpo not in liberi:
        raise ValidationError(
            "Montaggio non possibile: slot occupato o non consentito. Acquisto annullato."
        )
    return destinatario, slot_corpo


def _righe_bundle_qs(bundle: NegozioMercanteBundle):
    return bundle.righe.select_related(
        "voce",
        "voce__negozio",
        "voce__oggetto_base",
        "voce__oggetto",
        "voce__oggetto__infusione_generatrice",
        "voce__abilita",
        "voce__infusione",
        "voce__tessitura",
        "voce__cerimoniale",
        "voce__consumabile_tessitura",
        "voce__serie",
    ).order_by("ordine", "created_at")


def _stock_disponibile_voce(voce: NegozioMercanteVoce) -> int | None:
    """Unità rimanenti della voce (None = illimitato)."""
    if voce.tipo_voce == VOCE_SERIE:
        return _quantita_effettiva_serie(voce)
    return voce.quantita_residua


def _bundle_disponibilita(bundle: NegozioMercanteBundle, personaggio) -> tuple[bool, str, int | None]:
    """
    Ritorna (acquistabile, messaggio, quantita_effettiva).
    quantita_effettiva = minimo stock componenti limitati (None = illimitato).
    """
    righe = list(_righe_bundle_qs(bundle))
    if not righe:
        return False, "Bundle vuoto.", 0
    qty_eff = None
    for riga in righe:
        voce = riga.voce
        if voce.negozio_id != bundle.negozio_id:
            return False, "Bundle non valido.", 0
        if not voce.attivo:
            return False, MSG_NON_DISPONIBILE_LISTINO, 0
        motivo = _motivo_voce_non_acquistabile(voce, personaggio, qty=riga.quantita)
        if motivo:
            return False, motivo, 0
        stock = _stock_disponibile_voce(voce)
        if stock is not None:
            disponibili = stock // max(1, riga.quantita)
            qty_eff = disponibili if qty_eff is None else min(qty_eff, disponibili)
    if qty_eff is not None and qty_eff <= 0:
        return False, MSG_ESAURITO_LISTINO, 0
    return True, "", qty_eff


def serializza_bundle_listino(bundle: NegozioMercanteBundle, personaggio, *, prezzi_ctx=None) -> dict:
    from personaggi.economia_crediti import CATEGORIA_NEGOZIO, prezzi_duali

    campagna = getattr(personaggio, "campagna", None)
    if prezzi_ctx:
        duali = prezzi_duali(
            bundle.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
            cfg=prezzi_ctx.get("cfg"),
            deposito_ammesso=prezzi_ctx.get("deposito_ammesso"),
        )
    else:
        duali = prezzi_duali(
            bundle.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
        )
    acquistabile, msg, qty_eff = _bundle_disponibilita(bundle, personaggio)
    componenti = []
    montaggio_count = 0
    montaggio_meta = None
    for riga in _righe_bundle_qs(bundle):
        voce = riga.voce
        componenti.append(
            {
                "voce_id": str(voce.id),
                "nome": _nome_voce_catalogo(voce),
                "tipo_voce": voce.tipo_voce,
                "quantita": riga.quantita,
            }
        )
        if _voce_richiede_montaggio(voce):
            montaggio_count += riga.quantita
            if montaggio_meta is None:
                montaggio_meta = {}
                if voce.tipo_voce == VOCE_OGGETTO:
                    _applica_avvisi_montaggio_listino(
                        montaggio_meta, personaggio, oggetto=voce.oggetto
                    )
                else:
                    _applica_avvisi_montaggio_listino(
                        montaggio_meta, personaggio, infusione=voce.infusione
                    )
    richiede_montaggio = montaggio_count == 1
    payload = {
        "id": str(bundle.id),
        "tipo": "bundle",
        "tipo_voce": "BND",
        "nome": bundle.nome,
        "descrizione": bundle.descrizione or "",
        "prezzo_crediti": bundle.prezzo_crediti,
        "prezzo_corrente": duali["prezzo_corrente"],
        "prezzo_deposito": duali["prezzo_deposito"],
        "deposito_ammesso": duali["deposito_ammesso"],
        "quantita_residua": qty_eff,
        "acquistabile": acquistabile and (montaggio_count <= 1),
        "messaggio_usabilita": msg
        if montaggio_count <= 1
        else "Il pacchetto contiene più innesti/mutazioni: non acquistabile insieme.",
        "componenti": componenti,
        "richiede_montaggio": richiede_montaggio,
        "consegna_istanza": False,
        "prestabile": False,
    }
    if bundle.negozio.negozio_prestiti:
        payload["acquistabile"] = False
        payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
            payload.get("messaggio_usabilita"),
            "I pacchetti non sono disponibili nei negozi di prestiti.",
        )
    if richiede_montaggio and montaggio_meta:
        for key in (
            "infusione_id",
            "tipo_risultato",
            "slot_corpo_permessi",
            "slot_disponibili",
            "richiede_ate",
        ):
            if key in montaggio_meta:
                payload[key] = montaggio_meta[key]
        payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
            payload.get("messaggio_usabilita"),
            montaggio_meta.get("messaggio_usabilita"),
        )
        if richiede_montaggio and not payload.get("slot_disponibili"):
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), MSG_SLOT_PIENO_LISTINO
            )
    return payload


def slot_aumento_disponibili(personaggio, *, infusione=None, oggetto=None) -> list:
    """Slot corpo liberi sul personaggio, eventualmente filtrati dall'infusione."""
    inf = infusione
    if oggetto is not None:
        if not _oggetto_e_aumento(oggetto) and not (
            inf and getattr(inf, "tipo_risultato", None) == SCELTA_RISULTATO_AUMENTO
        ):
            return []
        inf = inf or oggetto.infusione_generatrice
    elif inf is None or inf.tipo_risultato != SCELTA_RISULTATO_AUMENTO:
        return []
    permessi = _slot_permessi_codes(inf)
    liberi = []
    for code, label in SLOT_CORPO_CHOICES:
        if permessi and code not in permessi:
            continue
        occupante = Oggetto.objects.filter(
            tracciamento_inventario__inventario=personaggio,
            tracciamento_inventario__data_fine__isnull=True,
            slot_corpo=code,
            is_equipaggiato=True,
        ).exists()
        if not occupante:
            liberi.append({"code": code, "label": label})
    return liberi


def _risolve_destinatario_montaggio(acquirente, destinatario_id):
    if not destinatario_id or str(destinatario_id) == str(acquirente.id):
        return acquirente
    try:
        dest = Personaggio.objects.get(pk=destinatario_id)
    except (Personaggio.DoesNotExist, ValueError, TypeError) as exc:
        raise ValidationError("Destinatario del montaggio non trovato.") from exc
    if dest.eliminato_at:
        raise ValidationError("Il destinatario non è più disponibile.")
    if dest.campagna_id != acquirente.campagna_id:
        raise ValidationError("Il destinatario deve appartenere alla stessa campagna.")
    return dest


def _motivo_impedimento_montaggio_negozio(destinatario, *, infusione=None, oggetto=None):
    """
    Requisiti per montare un aumento già prodotto dal negozio.

    Mutazione: nessuno (basta lo slot libero).
    Innesto: Aura Tecnologica del destinatario > 0.
    Aura/mattoni della scheda tecnica restano requisiti di *acquisto ricetta*,
    non di montaggio istanza.
    """
    if not _e_innesto_corporeo(infusione=infusione, oggetto=oggetto):
        return None
    if destinatario.get_valore_aura_per_sigla("ATE") < 1:
        return (
            f"{destinatario.nome} non può sostenere innesti: "
            "serve almeno 1 punto di Aura Tecnologica."
        )
    return None


def _avviso_ate_listino(personaggio, *, infusione=None, oggetto=None) -> str:
    if not _e_innesto_corporeo(infusione=infusione, oggetto=oggetto):
        return ""
    if personaggio.get_valore_aura_per_sigla("ATE") >= 1:
        return ""
    return (
        "Tu non hai Aura Tecnologica (serve almeno 1 per gli innesti). "
        "Puoi montarlo su un altro personaggio."
    )


MSG_SLOT_PIENO_LISTINO = (
    "Nessuno slot libero sul tuo corpo: scegli un altro destinatario "
    "oppure libera una locazione."
)


def _unisci_messaggi_usabilita(*parti) -> str:
    """Concatena vincoli di usabilità senza duplicati e senza sovrascriverli."""
    visti = []
    for parte in parti:
        testo = (parte or "").strip()
        if not testo or testo in visti:
            continue
        visti.append(testo)
    return " ".join(visti)


def _applica_avvisi_montaggio_listino(
    payload, personaggio, *, infusione=None, oggetto=None
):
    precedente = payload.get("messaggio_usabilita") or ""
    meta = _meta_montaggio_listino(
        personaggio, infusione=infusione, oggetto=oggetto
    )
    meta_msg = meta.pop("messaggio_usabilita", "") or ""
    payload.update(meta)
    slot_msg = ""
    if payload.get("richiede_montaggio") and not payload.get("slot_disponibili"):
        slot_msg = MSG_SLOT_PIENO_LISTINO
    payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
        precedente, meta_msg, slot_msg
    )


def _monta_aumento_o_annulla(destinatario, oggetto, slot_corpo):
    """
    Installa innesto/mutazione sul destinatario.
    Qualsiasi fallimento alza ValidationError: in transazione atomica
    l'acquisto intero viene annullato.
    """
    from personaggi.services import GestioneOggettiService

    if not slot_corpo:
        raise ValidationError(
            "Per innesti e mutazioni indica lo slot corpo su cui montare l'aumento."
        )
    inf = oggetto.infusione_generatrice
    motivo = _motivo_impedimento_montaggio_negozio(
        destinatario, infusione=inf, oggetto=oggetto
    )
    if motivo:
        raise ValidationError(motivo)
    if _inventario_corrente_pk(oggetto) != destinatario.id:
        oggetto.sposta_in_inventario(destinatario)
    GestioneOggettiService.installa_innesto(destinatario, oggetto, slot_corpo)


def _meta_montaggio_listino(personaggio, *, infusione=None, oggetto=None) -> dict:
    inf = infusione or (oggetto.infusione_generatrice if oggetto else None)
    richiede = _oggetto_e_aumento(oggetto) or (
        inf is not None and inf.tipo_risultato == SCELTA_RISULTATO_AUMENTO
    )
    if not richiede:
        return {
            "richiede_montaggio": False,
            "infusione_id": str(inf.id) if inf else None,
            "tipo_risultato": getattr(inf, "tipo_risultato", None),
        }
    permessi = _slot_permessi_codes(inf)
    ate_msg = _avviso_ate_listino(personaggio, infusione=inf, oggetto=oggetto)
    meta = {
        "richiede_montaggio": True,
        "infusione_id": str(inf.id) if inf else None,
        "tipo_risultato": getattr(inf, "tipo_risultato", None),
        "slot_corpo_permessi": sorted(permessi) if permessi else [
            code for code, _label in SLOT_CORPO_CHOICES
        ],
        "slot_disponibili": slot_aumento_disponibili(
            personaggio, infusione=inf, oggetto=oggetto
        ),
        "richiede_ate": _e_innesto_corporeo(infusione=inf, oggetto=oggetto),
    }
    if ate_msg:
        meta["messaggio_usabilita"] = ate_msg
    return meta


def _descrizione_entita_listino(ent, personaggio=None) -> dict:
    """Testo grezzo + formattato (placeholder risolti) per una voce di listino."""
    if ent is None:
        return {"descrizione": "", "testo_formattato": ""}
    raw = (getattr(ent, "testo", None) or getattr(ent, "descrizione", None) or "") or ""
    formatted = ""
    if personaggio is not None and hasattr(personaggio, "get_testo_formattato_per_item"):
        try:
            formatted = personaggio.get_testo_formattato_per_item(ent) or ""
        except Exception:
            formatted = ""
    if not formatted:
        try:
            formatted = getattr(ent, "TestoFormattato", None) or ""
        except Exception:
            formatted = ""
    if not formatted:
        formatted = raw
    return {
        "descrizione": raw,
        "testo_formattato": formatted,
    }


def serializza_voce_listino(voce: NegozioMercanteVoce, personaggio, *, prezzi_ctx=None) -> dict:
    from personaggi.economia_crediti import CATEGORIA_NEGOZIO, prezzi_duali

    ent = _voce_entita(voce)
    nome = getattr(ent, "nome", voce.consumabile_nome or "Consumabile")
    desc = _descrizione_entita_listino(ent, personaggio)
    campagna = getattr(personaggio, "campagna", None)
    if prezzi_ctx:
        duali = prezzi_duali(
            voce.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
            cfg=prezzi_ctx.get("cfg"),
            deposito_ammesso=prezzi_ctx.get("deposito_ammesso"),
        )
    else:
        duali = prezzi_duali(
            voce.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
        )
    consegna_istanza = _voce_consegna_istanza(voce)
    payload = {
        "id": str(voce.id),
        "tipo": "voce",
        "tipo_voce": voce.tipo_voce,
        "nome": nome,
        "descrizione": desc["descrizione"],
        "testo_formattato": desc["testo_formattato"],
        "prezzo_crediti": voce.prezzo_crediti,
        "prezzo_corrente": duali["prezzo_corrente"],
        "prezzo_deposito": duali["prezzo_deposito"],
        "deposito_ammesso": duali["deposito_ammesso"],
        "quantita_residua": voce.quantita_residua,
        "acquistabile": True,
        "messaggio_usabilita": "",
        "consegna_istanza": consegna_istanza,
        "richiede_montaggio": False,
        "prestabile": voce_e_prestabile(voce),
    }
    if voce.negozio.negozio_prestiti and not payload["prestabile"]:
        payload["acquistabile"] = False
        payload["messaggio_usabilita"] = MSG_PRESTITO_NON_AMMESSO
    if voce.tipo_voce in (VOCE_INFUSIONE, VOCE_TESSITURA, VOCE_CERIMONIALE):
        if voce.tipo_voce == VOCE_INFUSIONE and consegna_istanza:
            _applica_avvisi_montaggio_listino(
                payload, personaggio, infusione=voce.infusione
            )
        else:
            payload.update(_tecnica_listino_extra(personaggio, ent))
    elif voce.tipo_voce == VOCE_ABILITA:
        if personaggio.abilita_possedute.filter(pk=ent.pk).exists():
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), "Abilità già posseduta."
            )
            payload["gia_posseduta"] = True
        else:
            payload["gia_posseduta"] = False
    elif voce.tipo_voce == VOCE_OGGETTO:
        _applica_avvisi_montaggio_listino(
            payload, personaggio, oggetto=voce.oggetto
        )
        if voce.oggetto_id and _inventario_corrente_pk(voce.oggetto) != voce.negozio.inventario_id:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), MSG_NON_DISPONIBILE_LISTINO
            )
    elif voce.tipo_voce == VOCE_SERIE:
        disponibili = _quantita_effettiva_serie(voce)
        payload["quantita_residua"] = disponibili
        if disponibili is not None and disponibili <= 0:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), MSG_ESAURITO_LISTINO
            )
    if voce.tipo_voce != VOCE_SERIE and voce.quantita_residua is not None and voce.quantita_residua <= 0:
        payload["acquistabile"] = False
        payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
            payload.get("messaggio_usabilita"), MSG_ESAURITO_LISTINO
        )
    return payload


def serializza_stock_listino(stock: NegozioMercanteStock, personaggio=None, *, prezzi_ctx=None) -> dict:
    from personaggi.economia_crediti import CATEGORIA_NEGOZIO, prezzi_duali

    campagna = getattr(personaggio, "campagna", None) if personaggio else None
    if prezzi_ctx:
        duali = prezzi_duali(
            stock.prezzo_rivendita,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
            cfg=prezzi_ctx.get("cfg"),
            deposito_ammesso=prezzi_ctx.get("deposito_ammesso"),
        )
    else:
        duali = prezzi_duali(stock.prezzo_rivendita, campagna, categoria=CATEGORIA_NEGOZIO)
    payload = {
        "id": str(stock.id),
        "tipo": "stock",
        "tipo_voce": VOCE_OGGETTO,
        "nome": stock.oggetto.nome,
        **_descrizione_entita_listino(stock.oggetto, personaggio),
        "prezzo_crediti": stock.prezzo_rivendita,
        "prezzo_corrente": duali["prezzo_corrente"],
        "prezzo_deposito": duali["prezzo_deposito"],
        "deposito_ammesso": duali["deposito_ammesso"],
        "acquistabile": stock.stato == STOCK_DISPONIBILE,
        "messaggio_usabilita": (
            MSG_USATO_LISTINO if stock.stato == STOCK_DISPONIBILE else ""
        ),
        "usato": True,
        "consegna_istanza": True,
        "richiede_montaggio": False,
        "prestabile": True,
    }
    if personaggio is not None:
        _applica_avvisi_montaggio_listino(
            payload, personaggio, oggetto=stock.oggetto
        )
    return payload


def build_listino(negozio: NegozioMercante, personaggio) -> dict:
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        categoria_ammessa_deposito,
        get_economia_config,
        modulo_conto_deposito_attivo,
        saldo_corrente,
        saldo_deposito,
    )

    ok, msg = negozio_e_aperto(negozio, personaggio)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna) if campagna is not None else None
    prezzi_ctx = None
    if cfg is not None:
        prezzi_ctx = {
            "cfg": cfg,
            "deposito_ammesso": categoria_ammessa_deposito(
                CATEGORIA_NEGOZIO, campagna, cfg=cfg
            ),
        }
    voci = []
    for voce in negozio.voci.filter(attivo=True, non_vendibile=False).select_related(
        "negozio",
        "oggetto_base",
        "oggetto",
        "oggetto__infusione_generatrice",
        "abilita",
        "infusione",
        "tessitura",
        "cerimoniale",
        "consumabile_tessitura",
        "serie",
    ):
        try:
            ent = _voce_entita(voce)
            if voce.tipo_voce != VOCE_CONSUMABILE:
                _assert_voce_globally_vendibile(ent)
        except ValidationError:
            continue
        payload = serializza_voce_listino(voce, personaggio, prezzi_ctx=prezzi_ctx)
        if not ok:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                msg or "Negozio chiuso.",
                payload.get("messaggio_usabilita"),
            )
        voci.append(payload)
    for bundle in (
        NegozioMercanteBundle.objects.filter(negozio=negozio, attivo=True)
        .select_related("negozio")
        .prefetch_related("righe__voce")
        .order_by("ordine", "created_at")
    ):
        if not bundle.righe.exists():
            continue
        payload = serializza_bundle_listino(bundle, personaggio, prezzi_ctx=prezzi_ctx)
        if not ok:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                msg or "Negozio chiuso.",
                payload.get("messaggio_usabilita"),
            )
        voci.append(payload)
    for stock in negozio.stock.filter(stato=STOCK_DISPONIBILE).select_related(
        "oggetto", "oggetto__infusione_generatrice", "negozio"
    ):
        payload = serializza_stock_listino(stock, personaggio, prezzi_ctx=prezzi_ctx)
        if not ok:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                msg or "Negozio chiuso.",
                payload.get("messaggio_usabilita"),
            )
        voci.append(payload)
    return {
        "negozio_id": str(negozio.id),
        "nome": negozio.nome,
        "descrizione": negozio.descrizione,
        "descrizione_immersiva": negozio.descrizione_immersiva or negozio.descrizione or "",
        "tipo_negozio": negozio.tipo_negozio,
        "negozio_prestiti": bool(negozio.negozio_prestiti),
        "limite_prestiti_per_personaggio": int(negozio.limite_prestiti_per_personaggio or 1),
        "prestiti_attivi_personaggio": (
            conta_prestiti_attivi(negozio, personaggio) if negozio.negozio_prestiti else 0
        ),
        "prestiti_attivi": (
            serializza_prestiti_attivi(negozio, personaggio)
            if negozio.negozio_prestiti
            else []
        ),
        "aperto": ok,
        "messaggio_accesso": msg,
        "saldo_crediti": float(negozio.saldo_crediti or 0),
        "voci": voci,
        "economia": {
            "modulo_attivo": modulo_conto_deposito_attivo(personaggio),
            "crediti_corrente": str(saldo_corrente(personaggio)),
            "crediti_deposito": str(saldo_deposito(personaggio)),
        },
    }


def _voce_anteprima_staff(voce: NegozioMercanteVoce) -> dict | None:
    """Voce di listino senza personaggio: solo dati vetrina (nessun check PG)."""
    ent = _voce_entita(voce)
    if voce.tipo_voce != VOCE_CONSUMABILE and ent is None:
        return None
    desc = _descrizione_entita_listino(ent)
    quantita = (
        _quantita_effettiva_serie(voce)
        if voce.tipo_voce == VOCE_SERIE
        else voce.quantita_residua
    )
    return {
        "id": str(voce.id),
        "tipo": "voce",
        "tipo_voce": voce.tipo_voce,
        "nome": getattr(ent, "nome", None) or voce.consumabile_nome or "Consumabile",
        "descrizione": desc["descrizione"],
        "testo_formattato": desc["testo_formattato"],
        "prezzo_crediti": voce.prezzo_crediti,
        "quantita_residua": quantita,
        "non_vendibile": bool(voce.non_vendibile),
        "richiede_montaggio": _voce_richiede_montaggio(voce),
        "consegna_istanza": _voce_consegna_istanza(voce),
        "prestabile": voce_e_prestabile(voce),
        "acquistabile": False,
    }


def build_listino_anteprima(negozio: NegozioMercante) -> dict:
    """
    Vetrina del negozio senza personaggio: anteprima staff.

    Mostra gli stessi nomi/descrizioni/prezzi base che vedrebbe un giocatore, ma
    senza regole di apertura, visibilità, prezzi duali o disponibilità legate a
    un PG: nulla è acquistabile da qui.
    """
    voci = []
    for voce in negozio.voci.filter(attivo=True).select_related(
        "negozio",
        "oggetto_base",
        "oggetto",
        "oggetto__infusione_generatrice",
        "abilita",
        "infusione",
        "tessitura",
        "cerimoniale",
        "consumabile_tessitura",
        "serie",
    ):
        payload = _voce_anteprima_staff(voce)
        if payload is not None:
            voci.append(payload)

    for bundle in (
        NegozioMercanteBundle.objects.filter(negozio=negozio, attivo=True)
        .prefetch_related("righe__voce")
        .order_by("ordine", "created_at")
    ):
        righe = list(_righe_bundle_qs(bundle))
        if not righe:
            continue
        voci.append(
            {
                "id": str(bundle.id),
                "tipo": "bundle",
                "tipo_voce": "BND",
                "nome": bundle.nome,
                "descrizione": bundle.descrizione or "",
                "testo_formattato": "",
                "prezzo_crediti": bundle.prezzo_crediti,
                "quantita_residua": None,
                "componenti": [
                    {
                        "voce_id": str(riga.voce_id),
                        "nome": _nome_voce_catalogo(riga.voce),
                        "tipo_voce": riga.voce.tipo_voce,
                        "quantita": riga.quantita,
                    }
                    for riga in righe
                ],
                "acquistabile": False,
            }
        )

    for stock in negozio.stock.filter(stato=STOCK_DISPONIBILE).select_related(
        "oggetto", "oggetto__infusione_generatrice"
    ):
        desc = _descrizione_entita_listino(stock.oggetto)
        voci.append(
            {
                "id": str(stock.id),
                "tipo": "stock",
                "tipo_voce": VOCE_OGGETTO,
                "nome": stock.oggetto.nome,
                "descrizione": desc["descrizione"],
                "testo_formattato": desc["testo_formattato"],
                "prezzo_crediti": stock.prezzo_rivendita,
                "quantita_residua": 1,
                "usato": True,
                "messaggio_usabilita": MSG_USATO_LISTINO,
                "acquistabile": False,
            }
        )

    return {
        "negozio_id": str(negozio.id),
        "nome": negozio.nome,
        "descrizione": negozio.descrizione,
        "descrizione_immersiva": negozio.descrizione_immersiva or negozio.descrizione or "",
        "tipo_negozio": negozio.tipo_negozio,
        "negozio_prestiti": bool(negozio.negozio_prestiti),
        "limite_prestiti_per_personaggio": int(negozio.limite_prestiti_per_personaggio or 1),
        "aperto": bool(negozio.attivo),
        "messaggio_accesso": "" if negozio.attivo else "Negozio non attivo.",
        "saldo_crediti": float(negozio.saldo_crediti or 0),
        "anteprima": True,
        "voci": voci,
    }


def slot_innesto_disponibili(personaggio, oggetto) -> list:
    """Alias storico: slot liberi per un oggetto innesto/mutazione già esistente."""
    return slot_aumento_disponibili(personaggio, oggetto=oggetto)


@transaction.atomic
def acquista_voce(
    negozio: NegozioMercante,
    personaggio,
    voce_id,
    *,
    slot_corpo: str | None = None,
    conto: str = "CORRENTE",
    destinatario_id=None,
) -> dict:
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        CONTO_DEPOSITO,
        addebita_bene,
        get_economia_config,
        normalize_conto,
        prepara_addebito_bene,
        saldo_conto,
        saldo_spendibile,
    )

    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    conto = normalize_conto(conto)
    voce = (
        NegozioMercanteVoce.objects.select_for_update(of=("self",))
        .select_related(
            "negozio",
            "oggetto_base",
            "oggetto",
            "oggetto__infusione_generatrice",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
            "consumabile_tessitura",
            "serie",
        )
        .get(pk=voce_id, negozio=negozio, attivo=True)
    )
    if voce.non_vendibile:
        raise ValidationError(
            "Questo articolo è vendibile solo all'interno di un pacchetto (bundle)."
        )

    is_prestito = bool(negozio.negozio_prestiti)
    if is_prestito:
        if not voce_e_prestabile(voce):
            raise ValidationError(MSG_PRESTITO_NON_AMMESSO)
        assert_limite_prestiti(negozio, personaggio, qty=1)

    destinatario, slot_eff = _prepara_montaggio_voce(
        voce, personaggio, slot_corpo=slot_corpo, destinatario_id=destinatario_id
    )
    richiede_montaggio = _voce_richiede_montaggio(voce)

    prezzo = int(voce.prezzo_crediti)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    da_pagare = prepara_addebito_bene(
        prezzo,
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=campagna,
        personaggio=personaggio,
        cfg=cfg,
    )
    if prezzo > 0:
        if conto == CONTO_DEPOSITO:
            if saldo_conto(personaggio, CONTO_DEPOSITO) < da_pagare:
                raise ValidationError(f"Deposito insufficiente. Servono {da_pagare} CR.")
        elif saldo_spendibile(personaggio) < da_pagare:
            raise ValidationError(f"Crediti insufficienti. Servono {da_pagare} CR.")

    motivo = _motivo_voce_non_acquistabile(voce, personaggio, qty=1)
    if motivo:
        raise ValidationError(motivo)

    _decrementa_stock_voce(voce, 1)
    entita_creata = _consegna_unita_voce(
        negozio,
        voce,
        personaggio,
        slot_corpo=slot_eff,
        destinatario=destinatario,
    )

    pagato = 0
    if prezzo > 0:
        descrizione_addebito = (
            f"Noleggio presso {negozio.nome}"
            if is_prestito
            else f"Acquisto presso {negozio.nome}"
        )
        pagato = addebita_bene(
            personaggio,
            prezzo,
            descrizione_addebito,
            conto=conto,
            categoria=CATEGORIA_NEGOZIO,
            campagna=getattr(personaggio, "campagna", None),
            importo_gia_calcolato=da_pagare,
            cfg=cfg,
        )
        if negozio.incassa_acquisti_catalogo:
            _aggiorna_saldo(
                negozio,
                Decimal(prezzo),
                tipo="incasso_noleggio" if is_prestito else "incasso_acquisto",
                personaggio=personaggio,
                voce=voce,
                nota=(
                    f"Noleggio: {voce}" if is_prestito else f"Acquisto: {voce}"
                ),
            )

    if is_prestito:
        kwargs_prestito = {
            "costo_noleggio": prezzo,
            "voce": voce,
        }
        if entita_creata is not None and hasattr(entita_creata, "id"):
            # Oggetto fisico (OGB / OGG / INF-istanza)
            kwargs_prestito["oggetto"] = entita_creata
        elif voce.tipo_voce == VOCE_ABILITA:
            kwargs_prestito["abilita"] = voce.abilita
        elif voce.tipo_voce == VOCE_INFUSIONE:
            kwargs_prestito["infusione"] = voce.infusione
        elif voce.tipo_voce == VOCE_TESSITURA:
            kwargs_prestito["tessitura"] = voce.tessitura
        elif voce.tipo_voce == VOCE_CERIMONIALE:
            kwargs_prestito["cerimoniale"] = voce.cerimoniale
        else:
            raise ValidationError(
                "Prestito fallito: tipo voce non supportato per il prestito."
            )
        registra_prestito(negozio, personaggio, **kwargs_prestito)
        personaggio.aggiungi_log(
            f"Prestito al negozio «{negozio.nome}»"
            + (f" (noleggio {pagato} CR da {conto.lower()})." if prezzo > 0 else " (gratuito).")
        )
    else:
        personaggio.aggiungi_log(
            f"Acquisto al negozio «{negozio.nome}» ({pagato} CR da {conto.lower()})."
        )
    result = {
        "status": "success",
        "prezzo": prezzo,
        "prezzo_pagato": str(pagato),
        "conto": conto,
        "prestito": is_prestito,
    }
    if richiede_montaggio:
        result["montato_su"] = destinatario.id
        result["slot_corpo"] = slot_eff
    if entita_creata and hasattr(entita_creata, "id"):
        result["oggetto_id"] = entita_creata.id
    return result


@transaction.atomic
def acquista_bundle(
    negozio: NegozioMercante,
    personaggio,
    bundle_id,
    *,
    slot_corpo: str | None = None,
    conto: str = "CORRENTE",
    destinatario_id=None,
) -> dict:
    """Acquista un bundle: scala stock delle componenti e consegna tutto atomicamente."""
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        CONTO_DEPOSITO,
        addebita_bene,
        get_economia_config,
        normalize_conto,
        prepara_addebito_bene,
        saldo_conto,
        saldo_spendibile,
    )

    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    if negozio.negozio_prestiti:
        raise ValidationError(
            "I pacchetti non sono disponibili nei negozi di prestiti."
        )

    conto = normalize_conto(conto)
    bundle = (
        NegozioMercanteBundle.objects.select_for_update(of=("self",))
        .select_related("negozio")
        .get(pk=bundle_id, negozio=negozio, attivo=True)
    )
    righe = list(_righe_bundle_qs(bundle))
    if not righe:
        raise ValidationError("Bundle vuoto.")

    voce_ids = [r.voce_id for r in righe]
    locked = {
        v.id: v
        for v in NegozioMercanteVoce.objects.select_for_update(of=("self",))
        .select_related(
            "negozio",
            "oggetto_base",
            "oggetto",
            "oggetto__infusione_generatrice",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
            "consumabile_tessitura",
            "serie",
        )
        .filter(pk__in=voce_ids, negozio=negozio)
    }
    if len(locked) != len(voce_ids):
        raise ValidationError("Una o più componenti del bundle non sono più disponibili.")

    montaggio_righe = []
    for riga in righe:
        voce = locked[riga.voce_id]
        if voce.negozio_id != negozio.id:
            raise ValidationError("Bundle non valido.")
        if not voce.attivo:
            raise ValidationError(MSG_NON_DISPONIBILE_LISTINO)
        if riga.quantita > 1 and not _voce_permette_quantita_multipla(voce):
            raise ValidationError(
                f"La voce «{_nome_voce_catalogo(voce)}» non supporta quantità multiple."
            )
        motivo = _motivo_voce_non_acquistabile(voce, personaggio, qty=riga.quantita)
        if motivo:
            raise ValidationError(motivo)
        if _voce_richiede_montaggio(voce):
            montaggio_righe.append((riga, voce))

    if len(montaggio_righe) > 1 or (
        len(montaggio_righe) == 1 and montaggio_righe[0][0].quantita != 1
    ):
        raise ValidationError(
            "Il pacchetto contiene più innesti/mutazioni: non acquistabile insieme."
        )

    destinatario = personaggio
    slot_eff = None
    if montaggio_righe:
        _riga_m, voce_m = montaggio_righe[0]
        destinatario, slot_eff = _prepara_montaggio_voce(
            voce_m, personaggio, slot_corpo=slot_corpo, destinatario_id=destinatario_id
        )

    prezzo = int(bundle.prezzo_crediti)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    da_pagare = prepara_addebito_bene(
        prezzo,
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=campagna,
        personaggio=personaggio,
        cfg=cfg,
    )
    if conto == CONTO_DEPOSITO:
        if saldo_conto(personaggio, CONTO_DEPOSITO) < da_pagare:
            raise ValidationError(f"Deposito insufficiente. Servono {da_pagare} CR.")
    elif saldo_spendibile(personaggio) < da_pagare:
        raise ValidationError(f"Crediti insufficienti. Servono {da_pagare} CR.")

    for riga in righe:
        _decrementa_stock_voce(locked[riga.voce_id], riga.quantita)

    ultima_entita = None
    for riga in righe:
        voce = locked[riga.voce_id]
        for _ in range(riga.quantita):
            # Ricarica OGG dopo eventuale disattivazione (qty sempre 1).
            if voce.tipo_voce == VOCE_OGGETTO:
                voce.refresh_from_db()
            ultima_entita = _consegna_unita_voce(
                negozio,
                voce,
                personaggio,
                slot_corpo=slot_eff if _voce_richiede_montaggio(voce) else None,
                destinatario=destinatario if _voce_richiede_montaggio(voce) else personaggio,
            )

    pagato = addebita_bene(
        personaggio,
        prezzo,
        f"Acquisto bundle «{bundle.nome}» presso {negozio.nome}",
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=getattr(personaggio, "campagna", None),
        importo_gia_calcolato=da_pagare,
        cfg=cfg,
    )
    if negozio.incassa_acquisti_catalogo:
        _aggiorna_saldo(
            negozio,
            Decimal(prezzo),
            tipo="incasso_bundle",
            personaggio=personaggio,
            bundle=bundle,
            nota=f"Bundle: {bundle.nome}",
        )

    personaggio.aggiungi_log(
        f"Acquisto bundle «{bundle.nome}» al negozio «{negozio.nome}» "
        f"({pagato} CR da {conto.lower()})."
    )
    result = {
        "status": "success",
        "prezzo": prezzo,
        "prezzo_pagato": str(pagato),
        "conto": conto,
        "bundle_id": str(bundle.id),
    }
    if montaggio_righe:
        result["montato_su"] = destinatario.id
        result["slot_corpo"] = slot_eff
    if ultima_entita and hasattr(ultima_entita, "id"):
        result["oggetto_id"] = ultima_entita.id
    return result


@transaction.atomic
def acquista_stock(
    negozio,
    personaggio,
    stock_id,
    *,
    slot_corpo=None,
    conto: str = "CORRENTE",
    destinatario_id=None,
) -> dict:
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        CONTO_DEPOSITO,
        addebita_bene,
        get_economia_config,
        normalize_conto,
        prepara_addebito_bene,
        saldo_conto,
        saldo_spendibile,
    )

    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    is_prestito = bool(negozio.negozio_prestiti)
    if is_prestito:
        assert_limite_prestiti(negozio, personaggio, qty=1)

    stock = (
        NegozioMercanteStock.objects.select_for_update(of=("self",))
        .select_related("oggetto", "negozio")
        .get(pk=stock_id, negozio=negozio, stato=STOCK_DISPONIBILE)
    )
    og = stock.oggetto
    richiede_montaggio = _oggetto_e_aumento(og)
    destinatario = personaggio
    if richiede_montaggio:
        destinatario = _risolve_destinatario_montaggio(personaggio, destinatario_id)
        if not slot_corpo:
            raise ValidationError(
                "Per innesti e mutazioni indica lo slot corpo e, se diverso da te, "
                "il destinatario del montaggio."
            )
        inf_ref = og.infusione_generatrice
        liberi = {
            s["code"]
            for s in slot_aumento_disponibili(destinatario, infusione=inf_ref, oggetto=og)
        }
        if slot_corpo not in liberi:
            raise ValidationError(
                "Montaggio non possibile: slot occupato o non consentito. Acquisto annullato."
            )

    prezzo = int(stock.prezzo_rivendita)
    conto = normalize_conto(conto)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    da_pagare = prepara_addebito_bene(
        prezzo,
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=campagna,
        personaggio=personaggio,
        cfg=cfg,
    )
    if prezzo > 0:
        if conto == CONTO_DEPOSITO:
            if saldo_conto(personaggio, CONTO_DEPOSITO) < da_pagare:
                raise ValidationError(f"Deposito insufficiente. Servono {da_pagare} CR.")
        elif saldo_spendibile(personaggio) < da_pagare:
            raise ValidationError(f"Crediti insufficienti. Servono {da_pagare} CR.")

    if richiede_montaggio:
        _monta_aumento_o_annulla(destinatario, og, slot_corpo)
    else:
        og.sposta_in_inventario(personaggio)

    stock.stato = STOCK_VENDUTO
    stock.save(update_fields=["stato", "updated_at"])

    pagato = 0
    if prezzo > 0:
        pagato = addebita_bene(
            personaggio,
            prezzo,
            (
                f"Noleggio usato da {negozio.nome}"
                if is_prestito
                else f"Riacquisto usato da {negozio.nome}"
            ),
            conto=conto,
            categoria=CATEGORIA_NEGOZIO,
            campagna=getattr(personaggio, "campagna", None),
            importo_gia_calcolato=da_pagare,
            cfg=cfg,
        )
        _aggiorna_saldo(
            negozio,
            Decimal(prezzo),
            tipo="incasso_noleggio" if is_prestito else "incasso_rivendita",
            personaggio=personaggio,
            stock=stock,
        )

    if is_prestito:
        registra_prestito(
            negozio,
            personaggio,
            oggetto=og,
            costo_noleggio=prezzo,
            stock=stock,
        )
        personaggio.aggiungi_log(
            f"Prestito usato al negozio «{negozio.nome}»"
            + (
                f" (noleggio {pagato} CR da {conto.lower()})."
                if prezzo > 0
                else " (gratuito)."
            )
        )
    else:
        personaggio.aggiungi_log(
            f"Riacquisto al negozio «{negozio.nome}» ({pagato} CR da {conto.lower()})."
        )
    result = {
        "status": "success",
        "prezzo": prezzo,
        "prezzo_pagato": str(pagato),
        "conto": conto,
        "oggetto_id": og.id,
        "prestito": is_prestito,
    }
    if richiede_montaggio:
        result["montato_su"] = destinatario.id
        result["slot_corpo"] = slot_corpo
    return result


def preview_vendita_oggetto(negozio, personaggio, oggetto_id) -> dict:
    """Stima fascia offerta (percentuali config) senza effettuare la vendita."""
    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    try:
        og = Oggetto.objects.select_related("infusione_generatrice").get(pk=oggetto_id)
    except Oggetto.DoesNotExist:
        raise ValidationError("Oggetto non trovato.")

    if _inventario_corrente_pk(og) != personaggio.id:
        raise ValidationError("Oggetto non nel tuo inventario.")
    if og.ospitato_su_id:
        raise ValidationError("Smonta l'oggetto prima di venderlo.")

    config = _config(negozio)
    val_ref = valore_riferimento_oggetto(og, config)
    lo = float(config.get("pct_vendita_min") or 20) / 100.0
    hi = float(config.get("pct_vendita_max") or 80) / 100.0
    if hi < lo:
        lo, hi = hi, lo
    offerta_min = max(1, int(round(val_ref * lo)))
    offerta_max = max(1, int(round(val_ref * hi)))
    saldo = negozio.saldo_crediti or Decimal("0")

    return {
        "oggetto_id": str(og.id),
        "nome": og.nome,
        "valore_riferimento": val_ref,
        "offerta_min": offerta_min,
        "offerta_max": offerta_max,
        "cassa_sufficiente": saldo >= offerta_max,
        "saldo_negozio": int(saldo),
    }


@transaction.atomic
def vendi_oggetto_a_negozio(negozio, personaggio, oggetto_id) -> dict:
    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    if negozio.negozio_prestiti:
        raise ValidationError(MSG_NEGOZIO_SOLO_PRESTITI)

    og = Oggetto.objects.select_related("infusione_generatrice").get(pk=oggetto_id)
    if _inventario_corrente_pk(og) != personaggio.id:
        raise ValidationError("Oggetto non nel tuo inventario.")
    if og.ospitato_su_id:
        raise ValidationError("Smonta l'oggetto prima di venderlo.")
    assert_oggetto_non_in_prestito(og)

    config = _config(negozio)
    val_ref = valore_riferimento_oggetto(og, config)
    pct = _random_pct(config, "pct_vendita_min", "pct_vendita_max")
    offerta = max(1, int(round(val_ref * pct)))

    if negozio.saldo_crediti < offerta:
        raise ValidationError("Il mercante non ha fondi sufficienti per l'acquisto.")

    pct_r = _random_pct(config, "pct_rivendita_min", "pct_rivendita_max")
    prezzo_riv = max(1, int(round(val_ref * pct_r)))

    og.sposta_in_inventario(negozio.inventario)
    stock = NegozioMercanteStock.objects.create(
        negozio=negozio,
        oggetto=og,
        prezzo_rivendita=prezzo_riv,
        valore_riferimento=val_ref,
        venduto_da=personaggio,
        stato=STOCK_DISPONIBILE,
    )

    personaggio.modifica_crediti(offerta, f"Vendita a {negozio.nome}", conto="DEPOSITO")
    _aggiorna_saldo(
        negozio,
        Decimal(-offerta),
        tipo="pagamento_vendita_pg",
        personaggio=personaggio,
        stock=stock,
        nota=f"Acquisto usato {og.nome}",
    )
    personaggio.aggiungi_log(f"Venduto «{og.nome}» al negozio «{negozio.nome}» per {offerta} CR.")
    return {
        "status": "success",
        "offerta_crediti": offerta,
        "prezzo_rivendita": prezzo_riv,
        "stock_id": str(stock.id),
    }


def negozi_corporativi_per_personaggio(personaggio, campagna=None):
    qs = NegozioMercante.objects.filter(
        attivo=True,
        tipo_negozio=NEGOZIO_TIPO_CORPORATIVO,
    )
    if campagna:
        qs = qs.filter(campagna=campagna)
    elif personaggio.campagna_id:
        qs = qs.filter(campagna_id=personaggio.campagna_id)
    out = []
    for n in qs:
        ok, _ = personaggio_puo_vedere_negozio_corporativo(n, personaggio)
        if ok:
            out.append(n)
    return out


def personaggio_puo_vedere_negozio_corporativo(negozio, personaggio):
    from personaggi.negozio_mercante_apertura import personaggio_puo_vedere_negozio_corporativo as _vis

    return _vis(negozio, personaggio)
