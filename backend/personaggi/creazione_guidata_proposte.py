"""
Bozza wizard creazione guidata: scelte in impostazioni_ui senza modificare la scheda PG.
"""

from gestione_plot.creazione_guidata_helpers import (
    _abilita_qs_from_sync_or_pk,
    _parse_effetti_param,
    _resolve_abilita_ids_from_effetti,
)

WIZARD_PROPOSTE_KEY = 'wizard_proposte'


def _abilita_pk_ids_from_effetti(effetti):
    raw_ids = _resolve_abilita_ids_from_effetti(effetti)
    return list(_abilita_qs_from_sync_or_pk(raw_ids).values_list('id', flat=True))


def load_wizard_proposte(personaggio):
    ui = personaggio.impostazioni_ui or {}
    blob = ui.get(WIZARD_PROPOSTE_KEY) or {}
    effetti = _parse_effetti_param(blob.get('effetti'))
    trail = blob.get('trail') if isinstance(blob.get('trail'), list) else []
    return effetti, trail


def salva_wizard_proposte(personaggio, effetti=None, trail=None):
    effetti = _parse_effetti_param(effetti)
    trail = trail if isinstance(trail, list) else []

    ui = dict(personaggio.impostazioni_ui or {})
    ui['creazione_guidata_in_corso'] = True
    ui[WIZARD_PROPOSTE_KEY] = {
        'effetti': effetti,
        'trail': trail,
    }
    scelte_ids = _abilita_pk_ids_from_effetti(effetti)
    if scelte_ids:
        ui['wizard_abilita_scelte'] = scelte_ids
    else:
        ui.pop('wizard_abilita_scelte', None)

    personaggio.impostazioni_ui = ui
    personaggio.save(update_fields=['impostazioni_ui', 'updated_at'])
    return ui[WIZARD_PROPOSTE_KEY]


def clear_wizard_proposte(personaggio, *, fine_percorso=False):
    ui = dict(personaggio.impostazioni_ui or {})
    ui.pop(WIZARD_PROPOSTE_KEY, None)
    ui.pop('wizard_abilita_scelte', None)
    if fine_percorso:
        ui['creazione_guidata_in_corso'] = False
    personaggio.impostazioni_ui = ui
    personaggio.save(update_fields=['impostazioni_ui', 'updated_at'])
