# personaggi/effetti_casuali.py
"""
Logica per la selezione casuale di effetti e la loro applicazione a personaggi.
"""

import random
from django.utils import timezone
from django.db import transaction

from .models import (
    EffettoCasuale, TipologiaEffetto, ConsumabilePersonaggio,
    Oggetto, OggettoInInventario, Personaggio, Statistica,
    TIPO_EFFETTO_OGGETTO, TIPO_EFFETTO_TESSITURA, TIPO_OGGETTO_FISICO,
    formatta_testo_generico,
)


def _build_context_valori_predefiniti(effetto):
    """Costruisce il contesto con valori predefiniti (valore_base_predefinito) per tutte le statistiche."""
    ctx = {}
    for stat in Statistica.objects.filter(parametro__isnull=False).exclude(parametro__exact=''):
        ctx[stat.parametro] = stat.valore_base_predefinito
    return ctx


def _formatta_effetto(effetto, personaggio=None):
    """
    Formatta descrizione e formula di un effetto con i valori del personaggio o predefiniti.
    Restituisce (descrizione_html, formula_html).
    """
    context = {
        'aura': effetto.tipologia.aura_collegata if effetto.tipologia else None,
        'elemento': effetto.elemento_principale,
    }
    if personaggio:
        desc = formatta_testo_generico(
            effetto.descrizione,
            formula=effetto.formula,
            personaggio=personaggio,
            context=context,
        )
        # formatta_testo_generico restituisce descrizione+formula insieme; separiamo se serve
        formula_txt = formatta_testo_generico(
            None,
            formula=effetto.formula,
            personaggio=personaggio,
            context=context,
            solo_formula=True,
        )
        return desc, formula_txt
    else:
        base_vals = _build_context_valori_predefiniti(effetto)
        context.update(base_vals)
        # Senza personaggio usiamo statistiche_base vuote e context con valori predefiniti
        desc = formatta_testo_generico(
            effetto.descrizione,
            formula=effetto.formula,
            statistiche_base=[],
            context=context,
        )
        formula_txt = formatta_testo_generico(
            None,
            formula=effetto.formula,
            statistiche_base=[],
            context=context,
            solo_formula=True,
        )
        return desc, formula_txt


def seleziona_effetto_casuale(tipologia, personaggio=None):
    """
    Seleziona un effetto casuale tra quelli della tipologia indicata.

    Args:
        tipologia: TipologiaEffetto (o id)
        personaggio: Personaggio opzionale

    Returns:
        dict con:
        - nome: str
        - descrizione: str (HTML formattato)
        - formula: str (HTML formattato, può essere vuoto)
        - oggetto_creato: Oggetto se tipo=oggetto e personaggio valido (opzionale)
        - consumabile_creato: ConsumabilePersonaggio se tipo=tessitura e personaggio valido (opzionale)
    """
    if isinstance(tipologia, int):
        tipologia = TipologiaEffetto.objects.get(pk=tipologia)

    effetti = list(EffettoCasuale.objects.filter(tipologia=tipologia).select_related('tipologia', 'elemento_principale'))
    if not effetti:
        return {'nome': '', 'descrizione': '', 'formula': '', 'errore': 'Nessun effetto trovato per questa tipologia.'}

    effetto = random.choice(effetti)

    # Personaggio valido?
    pg_valido = personaggio and isinstance(personaggio, Personaggio) and personaggio.pk

    if not pg_valido:
        desc, formula = _formatta_effetto(effetto, personaggio=None)
        return {
            'nome': effetto.nome,
            'descrizione': desc,
            'formula': formula or '',
        }

    # Personaggio valido: applica l'effetto
    with transaction.atomic():
        desc, formula = _formatta_effetto(effetto, personaggio=personaggio)

        if tipologia.tipo == TIPO_EFFETTO_OGGETTO:
            # Crea Oggetto e inseriscilo nell'inventario
            oggetto = Oggetto.objects.create(
                nome=effetto.nome,
                testo=desc,
                tipo_oggetto=TIPO_OGGETTO_FISICO,
                aura=tipologia.aura_collegata,
            )
            OggettoInInventario.objects.create(
                oggetto=oggetto,
                inventario=personaggio,
                data_inizio=timezone.now(),
            )
            return {
                'nome': effetto.nome,
                'descrizione': desc,
                'formula': formula or '',
                'oggetto_creato': oggetto,
            }

        elif tipologia.tipo == TIPO_EFFETTO_TESSITURA:
            # Crea ConsumabilePersonaggio con 1 utilizzo, scadenza oggi
            # Salviamo i template raw (descrizione, formula) per formattarli al volo con le stat del pg
            oggi = timezone.now().date()
            consumabile = ConsumabilePersonaggio.objects.create(
                personaggio=personaggio,
                effetto_casuale=effetto,
                nome=effetto.nome,
                descrizione=effetto.descrizione,
                formula=effetto.formula or '',
                utilizzi_rimanenti=1,
                data_scadenza=oggi,
            )
            return {
                'nome': effetto.nome,
                'descrizione': desc,
                'formula': formula or '',
                'consumabile_creato': consumabile,
            }

    return {'nome': effetto.nome, 'descrizione': desc, 'formula': formula or ''}
