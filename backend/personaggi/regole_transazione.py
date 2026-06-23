"""
Valutazione regole staff per scambi tra giocatori (RegolaTransazioneCategoria).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional, Tuple

from personaggi.accademia_catalogo import (
    oggetto_in_catalogo_accademia_ufficiale,
    tecnica_in_catalogo_accademia_ufficiale,
)
from personaggi.requisiti_accesso import personaggio_soddisfa_requisiti_gruppo

from .models import (
    REGOLA_TX_CODICE_CERIMONIALI,
    REGOLA_TX_CODICE_CONSUMABILI,
    REGOLA_TX_CODICE_CREDITI,
    REGOLA_TX_CODICE_INFUSIONI,
    REGOLA_TX_CODICE_INNESTI,
    REGOLA_TX_CODICE_MATERIA,
    REGOLA_TX_CODICE_MOD,
    REGOLA_TX_CODICE_MUTAZIONI,
    REGOLA_TX_CODICE_OGGETTI,
    REGOLA_TX_CODICE_TESSITURE,
    REGOLA_TX_CODICI_DEFAULT,
    REGOLA_TX_CODICE_CHOICES,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MOD,
    TIPO_OGGETTO_MUTAZIONE,
    TIPO_OGGETTO_POTENZIAMENTO,
    TIPO_OGGETTO_AUMENTO,
    Campagna,
    ConsumabilePersonaggio,
    Oggetto,
    Personaggio,
    RegolaTransazioneCategoria,
)

TIPO_OGGETTO_A_CATEGORIA = {
    TIPO_OGGETTO_FISICO: REGOLA_TX_CODICE_OGGETTI,
    TIPO_OGGETTO_POTENZIAMENTO: REGOLA_TX_CODICE_OGGETTI,
    TIPO_OGGETTO_AUMENTO: REGOLA_TX_CODICE_OGGETTI,
    TIPO_OGGETTO_MATERIA: REGOLA_TX_CODICE_MATERIA,
    TIPO_OGGETTO_MOD: REGOLA_TX_CODICE_MOD,
    TIPO_OGGETTO_INNESTO: REGOLA_TX_CODICE_INNESTI,
    TIPO_OGGETTO_MUTAZIONE: REGOLA_TX_CODICE_MUTAZIONI,
}

NOMI_CATEGORIA = dict(REGOLA_TX_CODICE_CHOICES)

# Tessiture / infusioni / cerimoniali: blocco catalogo Accademia sempre attivo (copyright).
REGOLA_TX_CODICI_CATALOGO_OBBLIGATORIO = frozenset({
    REGOLA_TX_CODICE_INFUSIONI,
    REGOLA_TX_CODICE_TESSITURE,
    REGOLA_TX_CODICE_CERIMONIALI,
})


def ensure_regole_transazione_campagna(campagna) -> None:
    """Crea righe mancanti per tutte le categorie note."""
    if not campagna:
        return
    esistenti = set(
        RegolaTransazioneCategoria.objects.filter(campagna=campagna).values_list('codice', flat=True)
    )
    to_create = []
    for idx, codice in enumerate(REGOLA_TX_CODICI_DEFAULT):
        if codice in esistenti:
            continue
        defaults = {
            'nome': NOMI_CATEGORIA.get(codice, codice),
            'ordine': idx * 10,
            'vendibile_giocatori': True,
            'requisiti_gruppo': {},
        }
        if codice in (REGOLA_TX_CODICE_TESSITURE, REGOLA_TX_CODICE_CERIMONIALI, REGOLA_TX_CODICE_INFUSIONI):
            defaults['solo_posseduti'] = True
            defaults['trasferimento_copia'] = True
        to_create.append(RegolaTransazioneCategoria(campagna=campagna, codice=codice, **defaults))
    if to_create:
        RegolaTransazioneCategoria.objects.bulk_create(to_create)


def get_regole_map(campagna) -> Dict[str, RegolaTransazioneCategoria]:
    if not campagna:
        campagna = Campagna.objects.filter(slug='kor35').first()
    if not campagna:
        return {}
    ensure_regole_transazione_campagna(campagna)
    return {
        r.codice: r
        for r in RegolaTransazioneCategoria.objects.filter(campagna=campagna)
    }


def _regola_per_categoria(campagna, codice: str) -> Optional[RegolaTransazioneCategoria]:
    return get_regole_map(campagna).get(codice)


def personaggio_puo_trasferire_categoria(personaggio: Personaggio, codice: str) -> Tuple[bool, str]:
    regola = _regola_per_categoria(personaggio.campagna, codice)
    if not regola:
        return True, ''
    if not regola.vendibile_giocatori:
        return False, f"Gli scambi di «{regola.nome}» non sono consentiti."
    ok, msg = personaggio_soddisfa_requisiti_gruppo(personaggio, regola.requisiti_gruppo or {})
    if not ok:
        return False, msg or f"Non soddisfi i requisiti per scambiare «{regola.nome}»."
    return True, ''


def _valida_oggetto(personaggio: Personaggio, oggetto: Oggetto, regola: RegolaTransazioneCategoria) -> Tuple[bool, str]:
    if oggetto.inventario_corrente_id != personaggio.inventario_ptr_id:
        return False, f"L'oggetto «{oggetto.nome}» non è nel tuo inventario."
    codice = TIPO_OGGETTO_A_CATEGORIA.get(oggetto.tipo_oggetto, REGOLA_TX_CODICE_OGGETTI)
    ok, msg = personaggio_puo_trasferire_categoria(personaggio, codice)
    if not ok:
        return False, msg
    if _deve_bloccare_catalogo_accademia(regola) and oggetto_in_catalogo_accademia_ufficiale(oggetto):
        return False, (
            f"«{oggetto.nome}» è nel catalogo ufficiale Accademia: "
            "non può essere scambiata tra giocatori."
        )
    return True, ''


def _deve_bloccare_catalogo_accademia(regola: RegolaTransazioneCategoria) -> bool:
    if regola.codice in REGOLA_TX_CODICI_CATALOGO_OBBLIGATORIO:
        return True
    return bool(regola.solo_posseduti)


def _personaggio_possiede_tecnica(personaggio: Personaggio, tecnica, codice: str) -> bool:
    if codice == REGOLA_TX_CODICE_INFUSIONI:
        return personaggio.infusioni_possedute.filter(pk=tecnica.pk).exists()
    if codice == REGOLA_TX_CODICE_TESSITURE:
        return personaggio.tessiture_possedute.filter(pk=tecnica.pk).exists()
    if codice == REGOLA_TX_CODICE_CERIMONIALI:
        return personaggio.cerimoniali_posseduti.filter(pk=tecnica.pk).exists()
    return False


def _valida_tecnica(
    personaggio: Personaggio,
    tecnica,
    codice: str,
    regola: RegolaTransazioneCategoria,
) -> Tuple[bool, str]:
    if not _personaggio_possiede_tecnica(personaggio, tecnica, codice):
        return False, f"La tecnica «{tecnica.nome}» non è nel tuo elenco."
    ok, msg = personaggio_puo_trasferire_categoria(personaggio, codice)
    if not ok:
        return False, msg
    if _deve_bloccare_catalogo_accademia(regola) and tecnica_in_catalogo_accademia_ufficiale(tecnica):
        return False, (
            f"«{tecnica.nome}» è nel catalogo ufficiale Accademia (tab Nuove): "
            "non può essere scambiata tra giocatori."
        )
    if regola.rispetta_non_insegnabile and getattr(tecnica, 'non_acquistabile', False):
        return False, f"«{tecnica.nome}» non è trasferibile (non acquistabile / insegnabile)."
    return True, ''


def _valida_consumabile(personaggio: Personaggio, consumabile: ConsumabilePersonaggio) -> Tuple[bool, str]:
    if consumabile.personaggio_id != personaggio.id:
        return False, f"Il consumabile «{consumabile.nome}» non ti appartiene."
    return personaggio_puo_trasferire_categoria(personaggio, REGOLA_TX_CODICE_CONSUMABILI)


def valida_proposta_transazione(personaggio: Personaggio, proposta_data: dict) -> Tuple[bool, str]:
    """Valida una proposta (create o controproposta) rispetto alle regole campagna."""
    campagna = personaggio.campagna
    crediti_dare = Decimal(str(proposta_data.get('crediti_da_dare') or 0))
    if crediti_dare > 0:
        ok, msg = personaggio_puo_trasferire_categoria(personaggio, REGOLA_TX_CODICE_CREDITI)
        if not ok:
            return False, msg

    oggetti_ids = proposta_data.get('oggetti_da_dare') or []
    if oggetti_ids:
        oggetti = Oggetto.objects.filter(pk__in=oggetti_ids).select_related('oggetto_base')
        regole = get_regole_map(campagna)
        for oggetto in oggetti:
            codice = TIPO_OGGETTO_A_CATEGORIA.get(oggetto.tipo_oggetto, REGOLA_TX_CODICE_OGGETTI)
            regola = regole.get(codice)
            if not regola:
                continue
            ok, msg = _valida_oggetto(personaggio, oggetto, regola)
            if not ok:
                return False, msg

    consumabili_ids = proposta_data.get('consumabili_da_dare') or []
    if consumabili_ids:
        for cons in ConsumabilePersonaggio.objects.filter(pk__in=consumabili_ids):
            ok, msg = _valida_consumabile(personaggio, cons)
            if not ok:
                return False, msg

    from personaggi.models import Cerimoniale, Infusione, Tessitura

    tecniche_map = (
        (REGOLA_TX_CODICE_INFUSIONI, 'infusioni_da_dare', Infusione),
        (REGOLA_TX_CODICE_TESSITURE, 'tessiture_da_dare', Tessitura),
        (REGOLA_TX_CODICE_CERIMONIALI, 'cerimoniali_da_dare', Cerimoniale),
    )
    regole = get_regole_map(campagna)
    for codice, field, model_cls in tecniche_map:
        ids = proposta_data.get(field) or []
        if not ids:
            continue
        regola = regole.get(codice)
        if not regola:
            continue
        for tecnica in model_cls.objects.filter(pk__in=ids):
            ok, msg = _valida_tecnica(personaggio, tecnica, codice, regola)
            if not ok:
                return False, msg

    return True, ''
