"""
Helper per anteprima wizard creazione guidata (talenti simulati, widget modello aura).
"""

import json
import uuid as uuid_lib
from collections import defaultdict

from personaggi.models import (
    Abilita,
    CARATTERISTICA,
    ModelloAura,
    Personaggio,
    Punteggio,
    abilita_punteggio,
)


def _parse_effetti_param(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _resolve_abilita_ids_from_effetti(effetti):
    ids = set()
    for eff in effetti:
        if not isinstance(eff, dict):
            continue
        tipo = eff.get('tipo') or eff.get('tipo_azione')
        payload = eff.get('payload') if isinstance(eff.get('payload'), dict) else eff
        if tipo in ('aggiungi_abilita', 'combo') or payload.get('abilita_sync_ids'):
            for raw in payload.get('abilita_sync_ids') or []:
                if raw:
                    ids.add(str(raw))
    return ids


def _abilita_qs_from_sync_or_pk(ids):
    if not ids:
        return Abilita.objects.none()
    uuids = []
    pks = []
    for raw in ids:
        try:
            uuids.append(uuid_lib.UUID(str(raw)))
        except (ValueError, TypeError):
            if str(raw).isdigit():
                pks.append(int(raw))
    q = Abilita.objects.none()
    qs_list = []
    if uuids:
        qs_list.append(Abilita.objects.filter(sync_id__in=uuids))
    if pks:
        qs_list.append(Abilita.objects.filter(pk__in=pks))
    if not qs_list:
        return Abilita.objects.none()
    combined = qs_list[0]
    for extra in qs_list[1:]:
        combined = combined | extra
    return combined.distinct()


def simulated_caratteristiche(personaggio, effetti):
    """Somma caratteristiche base PG + contributi da abilità nel percorso."""
    scores = dict(personaggio.caratteristiche_base or {})
    abilita_ids = _resolve_abilita_ids_from_effetti(effetti)
    qs = _abilita_qs_from_sync_or_pk(abilita_ids).prefetch_related('punteggio_acquisito')
    for link in abilita_punteggio.objects.filter(
        abilita_id__in=qs.values_list('id', flat=True)
    ).select_related('punteggio'):
        if link.punteggio.tipo != CARATTERISTICA:
            continue
        nome = link.punteggio.nome
        scores[nome] = scores.get(nome, 0) + int(link.valore or 0)
    return scores


def detected_aura_sigle(personaggio, effetti):
    """Aura 'attive' da abilità già sul PG o accumulate nel wizard."""
    sigle = set()
    abilita_ids = _resolve_abilita_ids_from_effetti(effetti)
    possessed = set(personaggio.abilita_possedute.values_list('id', flat=True))
    qs = _abilita_qs_from_sync_or_pk(abilita_ids)
    all_ids = possessed | set(qs.values_list('id', flat=True))
    if not all_ids:
        return sigle
    for ab in Abilita.objects.filter(id__in=all_ids).select_related('aura_riferimento'):
        if ab.aura_riferimento_id and ab.aura_riferimento.sigla:
            sigle.add(ab.aura_riferimento.sigla.upper())
    for link in abilita_punteggio.objects.filter(abilita_id__in=all_ids).select_related('punteggio'):
        if link.punteggio.tipo == 'AU' and link.punteggio.sigla:
            sigle.add(link.punteggio.sigla.upper())
    return sigle


def build_widget_modello_aura(personaggio, effetti, widget_config):
    """
    Costruisce opzioni modello aura per il passo (footer wizard).
    widget_config esempio:
      aura_sigle: ["MAG","SAC","ARC","PSI"]
      caratteristica_per_aura: {"MAG": "Magia", ...}  # nome caratteristica
      messaggio_bloccato: "Hai zero talenti di {nome}..."
    """
    if not widget_config or widget_config.get('tipo') != 'modello_aura':
        return None

    aura_sigle = [str(s).upper() for s in (widget_config.get('aura_sigle') or [])]
    caratt_map = widget_config.get('caratteristica_per_aura') or {}
    msg_tpl = widget_config.get('messaggio_bloccato') or (
        'Hai zero talenti di {nome} e non puoi sceglierla.'
    )
    char_scores = simulated_caratteristiche(personaggio, effetti)
    active_auras = detected_aura_sigle(personaggio, effetti)

    gruppi = []
    for sigla in aura_sigle:
        aura = Punteggio.objects.filter(tipo='AU', sigla__iexact=sigla).first()
        if not aura:
            continue
        caratt_nome = caratt_map.get(sigla) or caratt_map.get(sigla.lower())
        talenti = int(char_scores.get(caratt_nome, 0)) if caratt_nome else 0
        modelli = (
            ModelloAura.objects.filter(aura=aura)
            .prefetch_related('req_caratt_rel__requisito')
            .order_by('nome')
        )
        opzioni = []
        for mod in modelli:
            min_req = 0
            for req in mod.req_caratt_rel.all():
                if req.requisito.tipo != CARATTERISTICA:
                    continue
                min_req = max(min_req, int(req.valore or 0))
            richiesto = max(min_req, 1) if mod.req_caratt_rel.exists() else 0
            disponibile = talenti >= richiesto if richiesto else talenti > 0
            if not caratt_nome and richiesto == 0:
                disponibile = sigla in active_auras
            motivo = None
            if not disponibile:
                motivo = msg_tpl.format(nome=caratt_nome or aura.nome)
            opzioni.append({
                'sync_id': str(mod.sync_id),
                'id': mod.id,
                'nome': mod.nome,
                'descrizione': mod.descrizione or '',
                'disponibile': disponibile,
                'motivo_blocco': motivo,
                'talenti_caratteristica': talenti,
                'richiesto': richiesto,
            })
        gruppi.append({
            'aura_sigla': sigla,
            'aura_nome': aura.nome,
            'caratteristica_nome': caratt_nome,
            'talenti': talenti,
            'aura_attiva': sigla in active_auras,
            'modelli': opzioni,
        })
    return {'tipo': 'modello_aura', 'gruppi': gruppi}


def enrich_passo_player_data(passo, personaggio, effetti, request=None):
    """Arricchisce il dict del passo per il client (widget, opzioni_ui)."""
    from .creazione_guidata_serializers import CreazioneGuidataPassoPlayerSerializer

    data = CreazioneGuidataPassoPlayerSerializer(passo, context={'request': request}).data
    opzioni = passo.opzioni_ui if isinstance(passo.opzioni_ui, dict) else {}
    data['opzioni_ui'] = opzioni
    widget_cfg = opzioni.get('widget_fondo')
    if personaggio and widget_cfg:
        data['widget_fondo'] = build_widget_modello_aura(personaggio, effetti, widget_cfg)
    else:
        data['widget_fondo'] = None
    return data
