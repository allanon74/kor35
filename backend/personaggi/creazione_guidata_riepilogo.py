"""
Riepilogo personaggio per il wizard creazione guidata (anteprima effetti accumulati).
"""

from decimal import Decimal

from gestione_plot.creazione_guidata_helpers import (
    _abilita_qs_from_sync_or_pk,
    _parse_effetti_param,
    _resolve_abilita_ids_from_effetti,
    simulated_caratteristiche,
)

from personaggi.creazione_guidata_apply import calcola_costo_acquisto_abilita
from personaggi.models import (
    Abilita,
    Era,
    ModelloAura,
    Personaggio,
    PersonaggioAbilita,
    PersonaggioModelloAura,
    Prefettura,
)
def _resolve_sync_id(model_cls, sync_id_or_value):
    import uuid as uuid_lib

    if sync_id_or_value is None:
        return None
    raw = str(sync_id_or_value).strip()
    if not raw:
        return None
    try:
        uid = uuid_lib.UUID(raw)
        obj = model_cls.objects.filter(sync_id=uid).first()
        if obj:
            return obj
    except (ValueError, TypeError):
        pass
    if str(raw).isdigit():
        return model_cls.objects.filter(pk=int(raw)).first()
    return None


def _preview_campi_da_effetti(effetti):
    era = None
    prefettura = None
    prefettura_esterna = None
    for eff in effetti:
        if not isinstance(eff, dict):
            continue
        tipo = eff.get('tipo') or eff.get('tipo_azione')
        payload = eff.get('payload') if isinstance(eff.get('payload'), dict) else eff
        if tipo not in ('imposta_campo', 'combo'):
            continue
        field = payload.get('field')
        sync_id = payload.get('sync_id')
        if field == 'era':
            era = _resolve_sync_id(Era, sync_id) or era
        elif field == 'prefettura':
            prefettura = _resolve_sync_id(Prefettura, sync_id) or prefettura
        elif field == 'prefettura_esterna':
            prefettura_esterna = bool(payload.get('value', True))
    return era, prefettura, prefettura_esterna


def build_wizard_riepilogo(personaggio, effetti=None):
    effetti = _parse_effetti_param(effetti) if effetti is not None else []

    personaggio = Personaggio.objects.select_related(
        'tipologia',
        'era',
        'prefettura__regione',
        'segno_zodiacale',
    ).get(pk=personaggio.pk)
    if hasattr(personaggio, '_modificatori_calcolati_cache'):
        delattr(personaggio, '_modificatori_calcolati_cache')

    era_pg, pref_pg, pref_ext_pg = personaggio.era, personaggio.prefettura, personaggio.prefettura_esterna
    era_ant, pref_ant, pref_ext_ant = _preview_campi_da_effetti(effetti)

    era_show = era_ant or era_pg
    pref_show = pref_ant if pref_ant is not None else pref_pg
    pref_ext_show = pref_ext_ant if pref_ext_ant is not None else pref_ext_pg

    possessed_ids = set(personaggio.abilita_possedute.values_list('id', flat=True))
    trail_ids = _resolve_abilita_ids_from_effetti(effetti)
    trail_qs = _abilita_qs_from_sync_or_pk(trail_ids)

    from personaggi.views import PARAMETRO_SCONTO_ABILITA

    sconto_stat = personaggio.modificatori_calcolati.get(
        PARAMETRO_SCONTO_ABILITA, {'add': 0, 'mol': 1.0}
    )
    sconto_ref = max(0, int(sconto_stat.get('add', 0) or 0))
    abilita_scelte = []
    costo_pc_percorso = 0
    costo_cr_percorso = Decimal('0')
    for ab in trail_qs:
        if ab.id in possessed_ids:
            continue
        costi = calcola_costo_acquisto_abilita(personaggio, ab)
        costo_pc_percorso += costi['costo_pc']
        costo_cr_percorso += costi['costo_crediti']
        entry = {
            'id': ab.id,
            'sync_id': str(ab.sync_id),
            'nome': ab.nome,
            'costo_pc': costi['costo_pc'],
            'costo_crediti': str(costi['costo_crediti']),
        }
        if costi['costo_crediti'] != costi['costo_crediti_base']:
            entry['costo_crediti_base'] = str(costi['costo_crediti_base'])
        abilita_scelte.append(entry)

    pivots = (
        PersonaggioAbilita.objects.filter(personaggio=personaggio)
        .select_related('abilita')
        .order_by('abilita__nome')
    )
    abilita_possedute = [
        {
            'id': p.abilita_id,
            'nome': p.abilita.nome,
            'origine': p.origine,
        }
        for p in pivots
    ]

    ui = personaggio.impostazioni_ui or {}
    pending_ids = ui.get('wizard_abilita_pendenti') or []
    abilita_da_acquistare = []
    for ab in Abilita.objects.filter(id__in=pending_ids):
        costi = calcola_costo_acquisto_abilita(personaggio, ab)
        row = {
            'id': ab.id,
            'nome': ab.nome,
            'costo_pc': costi['costo_pc'],
            'costo_crediti': str(costi['costo_crediti']),
        }
        if costi['costo_crediti'] != costi['costo_crediti_base']:
            row['costo_crediti_base'] = str(costi['costo_crediti_base'])
        abilita_da_acquistare.append(row)

    char_sim = simulated_caratteristiche(personaggio, effetti)
    char_db = dict(personaggio.caratteristiche_base or {})
    caratteristiche = [
        {
            'nome': nome,
            'valore_db': char_db.get(nome, 0),
            'valore_anteprima': val,
            'delta': val - char_db.get(nome, 0),
        }
        for nome, val in sorted(char_sim.items(), key=lambda x: x[0])
    ]

    modelli_trail = []
    for eff in effetti:
        if not isinstance(eff, dict):
            continue
        if (eff.get('tipo') or eff.get('tipo_azione')) != 'seleziona_modello_aura':
            continue
        payload = eff.get('payload') if isinstance(eff.get('payload'), dict) else eff
        mid = payload.get('modello_aura_sync_id') or payload.get('sync_id')
        mod = _resolve_sync_id(ModelloAura, mid)
        if mod:
            modelli_trail.append({'sync_id': str(mod.sync_id), 'nome': mod.nome, 'aura': mod.aura.nome})

    modelli_pg = [
        {'nome': l.modello_aura.nome, 'aura': l.modello_aura.aura.nome}
        for l in PersonaggioModelloAura.objects.filter(personaggio=personaggio).select_related(
            'modello_aura__aura'
        )
    ]

    pc_residuo = int(personaggio.punti_caratteristica or 0) - costo_pc_percorso
    cr_residuo = Decimal(personaggio.crediti or 0) - costo_cr_percorso

    return {
        'nome': personaggio.nome,
        'tipologia_nome': personaggio.tipologia.nome if personaggio.tipologia_id else None,
        'segno_zodiacale_nome': personaggio.segno_zodiacale.nome if personaggio.segno_zodiacale_id else None,
        'era_nome': era_show.nome if era_show else None,
        'prefettura_nome': pref_show.nome if pref_show else None,
        'prefettura_esterna': bool(pref_ext_show),
        'prefettura_regione': (
            pref_show.regione.sigla if pref_show and getattr(pref_show, 'regione', None) else None
        ),
        'crediti': str(personaggio.crediti),
        'punti_caratteristica': int(personaggio.punti_caratteristica or 0),
        'crediti_residui_stimati': str(cr_residuo.quantize(Decimal('0.01'))),
        'pc_residui_stimati': pc_residuo,
        'sconto_abilita_percent': sconto_ref or 0,
        'costo_percorso_pc': costo_pc_percorso,
        'costo_percorso_crediti': str(costo_cr_percorso.quantize(Decimal('0.01'))),
        'abilita_possedute': abilita_possedute,
        'abilita_scelte': abilita_scelte,
        'abilita_nel_percorso': abilita_scelte,
        'abilita_da_acquistare': abilita_da_acquistare,
        'caratteristiche': caratteristiche,
        'modelli_aura': modelli_pg + modelli_trail,
        'anteprima_attiva': bool(effetti),
    }
