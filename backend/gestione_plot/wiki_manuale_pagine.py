"""
Gestione pagine ↔ manuali PDF (ordine, inizio capitolo, membership).
"""

from __future__ import annotations

import json
from typing import Any

from django.db import transaction

from gestione_plot.models import ManualePdf, ManualePdfPagina, PaginaRegolamento
from kor35.syncing import touch_sync_updated_at


def _default_ordine_for_manuale(manuale: ManualePdf) -> int:
    last = (
        ManualePdfPagina.objects.filter(manuale=manuale)
        .order_by('-ordine')
        .values_list('ordine', flat=True)
        .first()
    )
    return (last or 0) + 10


def serialize_manuale_pagina_entry(mp: ManualePdfPagina) -> dict[str, Any]:
    pagina = mp.pagina
    return {
        'id': str(mp.pk),
        'pagina_id': pagina.pk,
        'titolo': pagina.titolo,
        'slug': pagina.slug,
        'ordine': mp.ordine,
        'inizio_capitolo': mp.inizio_capitolo,
        'includi_in_pdf': pagina.includi_in_pdf,
        'public': pagina.public,
        'visibile_solo_staff': pagina.visibile_solo_staff,
        'pdf_solo_indice': pagina.pdf_solo_indice,
        'pdf_forza_nuova_pagina': pagina.pdf_forza_nuova_pagina,
        'pdf_titolo_capitolo': pagina.pdf_titolo_capitolo or '',
    }


def list_manuale_pagine_entries(manuale: ManualePdf) -> list[dict[str, Any]]:
    qs = (
        ManualePdfPagina.objects.filter(manuale=manuale)
        .select_related('pagina')
        .order_by('ordine', 'pagina__titolo')
    )
    return [serialize_manuale_pagina_entry(mp) for mp in qs]


def get_pagina_manuali_pdf_config(pagina: PaginaRegolamento) -> list[dict[str, Any]]:
    return [
        {
            'manuale_id': mp.manuale_id,
            'ordine': mp.ordine,
            'inizio_capitolo': mp.inizio_capitolo,
        }
        for mp in pagina.manuali_manuale.select_related('manuale').order_by('manuale__ordine', 'ordine')
    ]


def parse_manuali_pdf_config(raw: Any) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        raw = json.loads(raw)
    if not isinstance(raw, list):
        return None
    parsed = []
    for item in raw:
        if isinstance(item, dict) and item.get('manuale_id') is not None:
            parsed.append(
                {
                    'manuale_id': int(item['manuale_id']),
                    'ordine': int(item.get('ordine', 0)),
                    'inizio_capitolo': bool(item.get('inizio_capitolo', True)),
                }
            )
        elif isinstance(item, (int, str)) and str(item).strip().isdigit():
            parsed.append({'manuale_id': int(item), 'ordine': 0, 'inizio_capitolo': True})
    return parsed


@transaction.atomic
def sync_pagina_manuali_pdf(
    pagina: PaginaRegolamento,
    manuali_ids: list[int] | None,
    config: list[dict[str, Any]] | None = None,
) -> None:
    """Allinea membership e metadati through per una pagina wiki."""
    if manuali_ids is None and config is None:
        return

    config_by_id: dict[int, dict[str, Any]] = {}
    if config:
        for item in config:
            config_by_id[item['manuale_id']] = item
    elif manuali_ids is not None:
        for mid in manuali_ids:
            config_by_id[mid] = {'manuale_id': mid, 'ordine': 0, 'inizio_capitolo': True}

    target_ids = set(config_by_id.keys()) if config is not None else set(manuali_ids or [])

    existing = {mp.manuale_id: mp for mp in pagina.manuali_manuale.select_for_update().all()}
    touched_manuali: set[int] = set()

    for manuale_id in target_ids:
        spec = config_by_id.get(manuale_id, {'manuale_id': manuale_id, 'inizio_capitolo': True})
        inizio = bool(spec.get('inizio_capitolo', True))
        mp = existing.get(manuale_id)
        if mp:
            updates = []
            if 'ordine' in spec and mp.ordine != spec['ordine']:
                mp.ordine = spec['ordine']
                updates.append('ordine')
            if mp.inizio_capitolo != inizio:
                mp.inizio_capitolo = inizio
                updates.append('inizio_capitolo')
            if updates:
                updates.append('updated_at')
                mp.save(update_fields=updates)
        else:
            manuale = ManualePdf.objects.filter(pk=manuale_id).first()
            if not manuale:
                continue
            ordine = spec.get('ordine')
            if ordine is None:
                ordine = _default_ordine_for_manuale(manuale)
            ManualePdfPagina.objects.create(
                manuale=manuale,
                pagina=pagina,
                ordine=ordine,
                inizio_capitolo=inizio,
            )
        touched_manuali.add(manuale_id)

    remove_ids = set(existing.keys()) - target_ids
    if remove_ids:
        ManualePdfPagina.objects.filter(pagina=pagina, manuale_id__in=remove_ids).delete()
        touched_manuali |= remove_ids

    if touched_manuali:
        touch_sync_updated_at(PaginaRegolamento, pagina.pk)
        for mid in touched_manuali:
            touch_sync_updated_at(ManualePdf, mid)


@transaction.atomic
def bulk_set_manuale_pagine(manuale: ManualePdf, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sostituisce l'elenco pagine del manuale (ordine, capitoli, titoli PDF).
    Ogni entry: pagina_id, ordine, inizio_capitolo, pdf_titolo_capitolo (opz.).
    """
    existing = {mp.pagina_id: mp for mp in manuale.pagine_manuale.select_for_update().select_related('pagina')}
    seen_pagina_ids: set[int] = set()
    touched_pagine: set[int] = set()

    for idx, entry in enumerate(entries):
        pagina_id = entry.get('pagina_id')
        if not pagina_id or pagina_id in seen_pagina_ids:
            continue
        seen_pagina_ids.add(pagina_id)
        pagina = PaginaRegolamento.objects.filter(pk=pagina_id).first()
        if not pagina:
            continue

        ordine = entry.get('ordine')
        if ordine is None:
            ordine = (idx + 1) * 10
        inizio = bool(entry.get('inizio_capitolo', True))
        titolo_pdf = entry.get('pdf_titolo_capitolo')

        pagina_updates = []
        if not pagina.includi_in_pdf:
            pagina.includi_in_pdf = True
            pagina_updates.append('includi_in_pdf')
        if titolo_pdf is not None and pagina.pdf_titolo_capitolo != (titolo_pdf or ''):
            pagina.pdf_titolo_capitolo = titolo_pdf or ''
            pagina_updates.append('pdf_titolo_capitolo')
        for flag in ('pdf_solo_indice', 'pdf_forza_nuova_pagina'):
            if flag in entry and getattr(pagina, flag) != bool(entry[flag]):
                setattr(pagina, flag, bool(entry[flag]))
                pagina_updates.append(flag)
        if pagina_updates:
            pagina.save(update_fields=pagina_updates + ['updated_at'])
            touched_pagine.add(pagina.pk)

        mp = existing.get(pagina_id)
        if mp:
            mp_updates = []
            if mp.ordine != ordine:
                mp.ordine = ordine
                mp_updates.append('ordine')
            if mp.inizio_capitolo != inizio:
                mp.inizio_capitolo = inizio
                mp_updates.append('inizio_capitolo')
            if mp_updates:
                mp_updates.append('updated_at')
                mp.save(update_fields=mp_updates)
        else:
            ManualePdfPagina.objects.create(
                manuale=manuale,
                pagina=pagina,
                ordine=ordine,
                inizio_capitolo=inizio,
            )
        touched_pagine.add(pagina.pk)

    remove_ids = set(existing.keys()) - seen_pagina_ids
    if remove_ids:
        ManualePdfPagina.objects.filter(manuale=manuale, pagina_id__in=remove_ids).delete()
        touched_pagine |= remove_ids

    touch_sync_updated_at(ManualePdf, manuale.pk)
    for pid in touched_pagine:
        touch_sync_updated_at(PaginaRegolamento, pid)

    return list_manuale_pagine_entries(manuale)
