"""
Applicazione effetti del wizard creazione guidata personaggio.
"""

from decimal import Decimal
import uuid as uuid_lib

from django.core.cache import cache
from django.db import transaction

from personaggi.models import (
    Abilita,
    Era,
    EraAbilita,
    ModelloAura,
    Personaggio,
    PersonaggioAbilita,
    PersonaggioModelloAura,
    Prefettura,
    RegioneAbilita,
    TipologiaPersonaggio,
    PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
    FEATURE_ABILITA,
)


def _resolve_sync_id(model_cls, sync_id_or_value):
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


def _effetto_payload(effetto):
    if not isinstance(effetto, dict):
        return {}
    payload = effetto.get('payload')
    if isinstance(payload, dict):
        merged = {**payload}
        for key in ('field', 'sync_id', 'value', 'abilita_sync_ids', 'prefettura_esterna'):
            if key in effetto and key not in merged:
                merged[key] = effetto[key]
        return merged
    return effetto


def _effetto_tipo(effetto):
    return (effetto or {}).get('tipo') or (effetto or {}).get('tipo_azione') or ''


def calcola_costo_acquisto_abilita(personaggio, abilita):
    """
    Costi effettivi all'acquisto: PC dal listino, CR con sconto da modificatori_calcolati
    (stessa logica di acquire_abilita / try_acquire_abilita).
    """
    from personaggi.views import PARAMETRO_SCONTO_ABILITA

    mods = personaggio.modificatori_calcolati
    sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {'add': 0, 'mol': 1.0})
    sconto_valore = max(0, int(sconto_stat.get('add', 0) or 0))
    sconto_percent = Decimal(sconto_valore) / Decimal(100)
    moltiplicatore_costo = Decimal(1) - sconto_percent
    costo_pc = int(abilita.costo_pc or 0)
    costo_crediti_base = Decimal(abilita.costo_crediti or 0)
    costo_crediti = (costo_crediti_base * moltiplicatore_costo).quantize(Decimal('0.01'))
    return {
        'costo_pc': costo_pc,
        'costo_crediti': costo_crediti,
        'costo_crediti_base': costo_crediti_base.quantize(Decimal('0.01')),
        'sconto_abilita_percent': sconto_valore,
    }


def try_acquire_abilita(personaggio, abilita, request=None):
    """
    Tenta l'acquisto di un'abilità.
    Ritorna dict: status in ('acquired', 'pending', 'skipped', 'error'), ...
    """
    from personaggi.views import (
        _campaign_feature_filter,
        _sync_coma_state,
    )

    if personaggio.abilita_possedute.filter(id=abilita.id).exists():
        return {
            'status': 'skipped',
            'abilita_id': abilita.id,
            'abilita_nome': abilita.nome,
            'motivo': 'già posseduta',
        }

    if request is not None:
        abilita_qs = _campaign_feature_filter(request, Abilita.objects.filter(id=abilita.id), FEATURE_ABILITA)
        if not abilita_qs.exists():
            return {
                'status': 'error',
                'abilita_id': abilita.id,
                'abilita_nome': abilita.nome,
                'motivo': 'Abilità non disponibile nella campagna attiva.',
            }

    from django.core.exceptions import ValidationError as DjangoValidationError

    from personaggi.accademia_catalogo import verifica_abilita_accademia

    try:
        verifica_abilita_accademia(abilita)
    except DjangoValidationError as exc:
        return {
            'status': 'error',
            'abilita_id': abilita.id,
            'abilita_nome': abilita.nome,
            'motivo': str(exc),
        }

    era_ids_abilita = set(EraAbilita.objects.filter(abilita_id=abilita.id).values_list('era_id', flat=True))
    if era_ids_abilita:
        if not personaggio.era_id:
            return {
                'status': 'pending',
                'abilita_id': abilita.id,
                'abilita_nome': abilita.nome,
                'motivo': 'richiede_era',
            }
        if personaggio.era_id not in era_ids_abilita:
            return {
                'status': 'pending',
                'abilita_id': abilita.id,
                'abilita_nome': abilita.nome,
                'motivo': 'era_incompatibile',
            }

    regione_ids_abilita = set(
        RegioneAbilita.objects.filter(abilita_id=abilita.id).values_list('regione_id', flat=True)
    )
    if regione_ids_abilita:
        regione_pg_id = getattr(getattr(personaggio, 'prefettura', None), 'regione_id', None)
        if not regione_pg_id:
            return {
                'status': 'pending',
                'abilita_id': abilita.id,
                'abilita_nome': abilita.nome,
                'motivo': 'richiede_prefettura',
            }
        if regione_pg_id not in regione_ids_abilita:
            return {
                'status': 'pending',
                'abilita_id': abilita.id,
                'abilita_nome': abilita.nome,
                'motivo': 'regione_incompatibile',
            }

    is_tratto_ain = (
        abilita.is_tratto_aura
        and abilita.aura_riferimento_id
        and getattr(abilita.aura_riferimento, 'sigla', None) == 'AIN'
    )

    ok_val, msg_val = personaggio.valida_acquisizione_abilita(abilita)
    if not ok_val:
        return {
            'status': 'pending',
            'abilita_id': abilita.id,
            'abilita_nome': abilita.nome,
            'motivo': msg_val or 'validazione',
        }

    if not is_tratto_ain:
        character_scores = personaggio.caratteristiche_base
        for req in abilita.abilita_requisito_set.all():
            punteggio_nome = req.requisito.nome
            valore_richiesto = req.valore
            punteggio_pg = character_scores.get(punteggio_nome, 0)
            if punteggio_pg < valore_richiesto:
                return {
                    'status': 'pending',
                    'abilita_id': abilita.id,
                    'abilita_nome': abilita.nome,
                    'motivo': f'requisito:{punteggio_nome}',
                }

        required_prereqs = [p.prerequisito for p in abilita.abilita_prerequisiti.all()]
        if required_prereqs:
            possessed_skill_ids = set(personaggio.abilita_possedute.values_list('id', flat=True))
            for prereq in required_prereqs:
                if prereq.id not in possessed_skill_ids:
                    return {
                        'status': 'pending',
                        'abilita_id': abilita.id,
                        'abilita_nome': abilita.nome,
                        'motivo': f'prerequisito:{prereq.nome}',
                    }

    personaggio = Personaggio.objects.select_related('tipologia').get(pk=personaggio.pk)

    if is_tratto_ain:
        return {
            'status': 'pending',
            'abilita_id': abilita.id,
            'abilita_nome': abilita.nome,
            'motivo': 'tratto_ain_wizard',
        }

    costi = calcola_costo_acquisto_abilita(personaggio, abilita)
    costo_pc_finale = costi['costo_pc']
    costo_crediti_finale = costi['costo_crediti']

    if personaggio.punti_caratteristica < costo_pc_finale:
        return {
            'status': 'pending',
            'abilita_id': abilita.id,
            'abilita_nome': abilita.nome,
            'motivo': 'fondi_pc',
            'costo_pc': costo_pc_finale,
        }
    if personaggio.crediti < costo_crediti_finale:
        return {
            'status': 'pending',
            'abilita_id': abilita.id,
            'abilita_nome': abilita.nome,
            'motivo': 'fondi_crediti',
            'costo_crediti': str(costo_crediti_finale),
        }

    personaggio.modifica_pc(-costo_pc_finale, f"Acquisito abilità (wizard): {abilita.nome}")
    personaggio.modifica_crediti(
        -costo_crediti_finale,
        f"Acquisito abilità (wizard): {abilita.nome}",
    )
    PersonaggioAbilita.objects.create(
        personaggio=personaggio,
        abilita=abilita,
        origine=PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
        costo_pc_pagato=int(costo_pc_finale),
        costo_crediti_pagato=costo_crediti_finale,
    )
    cache.delete(f"acquirable_skills_{personaggio.id}")
    _sync_coma_state(personaggio)

    return {
        'status': 'acquired',
        'abilita_id': abilita.id,
        'abilita_nome': abilita.nome,
        'sync_id': str(abilita.sync_id),
    }


@transaction.atomic
def apply_creazione_guidata_effetti(personaggio, effetti, request=None):
    """
    Applica effetti accumulati dal wizard.
    Ritorna dict con chiavi personaggio campi, acquistate, pendenti, errori.
    """
    effetti = effetti if isinstance(effetti, list) else []

    era_obj = None
    prefettura_obj = None
    prefettura_esterna = None
    tipologia_obj = None
    abilita_sync_ids = []
    modelli_aura_sync_ids = []

    for eff in effetti:
        tipo = _effetto_tipo(eff)
        data = _effetto_payload(eff)
        if tipo == 'seleziona_modello_aura':
            mid = data.get('modello_aura_sync_id') or data.get('sync_id')
            if mid:
                modelli_aura_sync_ids.append(str(mid))
            continue
        if tipo == 'imposta_campo':
            field = data.get('field')
            sync_id = data.get('sync_id')
            value = data.get('value')
            if field == 'era':
                era_obj = _resolve_sync_id(Era, sync_id) or (
                    Era.objects.filter(pk=value).first() if value else None
                )
            elif field == 'prefettura':
                prefettura_obj = _resolve_sync_id(Prefettura, sync_id) or (
                    Prefettura.objects.filter(pk=value).first() if value else None
                )
            elif field == 'prefettura_esterna':
                prefettura_esterna = bool(
                    data.get('prefettura_esterna', value) if value is not None else data.get('value', False)
                )
            elif field == 'tipologia':
                tipologia_obj = _resolve_sync_id(TipologiaPersonaggio, sync_id) or (
                    TipologiaPersonaggio.objects.filter(pk=value).first() if value else None
                )
        elif tipo in ('aggiungi_abilita', 'combo'):
            ids = data.get('abilita_sync_ids') or []
            if isinstance(ids, list):
                abilita_sync_ids.extend([str(x) for x in ids if x])
            if tipo == 'combo':
                mid = data.get('modello_aura_sync_id')
                if mid:
                    modelli_aura_sync_ids.append(str(mid))

    if tipologia_obj:
        personaggio.tipologia = tipologia_obj
        personaggio.save(update_fields=['tipologia', 'updated_at'])

    if era_obj is not None or prefettura_obj is not None or prefettura_esterna is not None:
        personaggio.assegna_era_e_prefettura(
            era=era_obj if era_obj is not None else personaggio.era,
            prefettura=prefettura_obj if prefettura_obj is not None else personaggio.prefettura,
            prefettura_esterna=(
                bool(prefettura_esterna)
                if prefettura_esterna is not None
                else personaggio.prefettura_esterna
            ),
            force=True,
        )
        personaggio.refresh_from_db()

    errori = []
    modelli_applicati = []
    for sync_raw in dict.fromkeys(modelli_aura_sync_ids):
        modello = _resolve_sync_id(ModelloAura, sync_raw)
        if not modello:
            errori.append({'sync_id': sync_raw, 'motivo': 'modello_aura_non_trovato'})
            continue
        if PersonaggioModelloAura.objects.filter(
            personaggio=personaggio, modello_aura__aura=modello.aura
        ).exists():
            continue
        PersonaggioModelloAura.objects.create(personaggio=personaggio, modello_aura=modello)
        modelli_applicati.append({'sync_id': str(modello.sync_id), 'nome': modello.nome})

    seen_abilita = set()
    acquistate = []
    pendenti = []

    for sync_raw in abilita_sync_ids:
        if sync_raw in seen_abilita:
            continue
        seen_abilita.add(sync_raw)
        abilita = _resolve_sync_id(Abilita, sync_raw)
        if not abilita:
            errori.append({'sync_id': sync_raw, 'motivo': 'abilita_non_trovata'})
            continue
        result = try_acquire_abilita(personaggio, abilita, request=request)
        st = result.get('status')
        if st == 'acquired':
            acquistate.append(result)
            personaggio.refresh_from_db()
        elif st == 'pending':
            pendenti.append(result)
        elif st == 'skipped':
            pass
        else:
            errori.append(result)

    from personaggi.creazione_guidata_proposte import clear_wizard_proposte

    clear_wizard_proposte(personaggio, fine_percorso=False)
    personaggio.refresh_from_db()

    ui = dict(personaggio.impostazioni_ui or {})
    pending_ids = list(ui.get('wizard_abilita_pendenti') or [])
    for p in pendenti:
        aid = p.get('abilita_id')
        if aid and aid not in pending_ids:
            pending_ids.append(aid)
    for a in acquistate:
        aid = a.get('abilita_id')
        if aid in pending_ids:
            pending_ids.remove(aid)
    ui['wizard_abilita_pendenti'] = pending_ids
    ui.pop('wizard_abilita_scelte', None)
    ui['creazione_guidata_in_corso'] = False
    personaggio.impostazioni_ui = ui
    personaggio.save(update_fields=['impostazioni_ui', 'updated_at'])

    return {
        'era': personaggio.era_id,
        'prefettura': personaggio.prefettura_id,
        'prefettura_esterna': personaggio.prefettura_esterna,
        'tipologia': personaggio.tipologia_id,
        'acquistate': acquistate,
        'pendenti': pendenti,
        'errori': errori,
        'modelli_aura': modelli_applicati,
    }
