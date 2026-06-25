"""
Validazione requisiti componenti per ricarica batterie / serbatoi via QR.
"""
from __future__ import annotations

from typing import List, Tuple

from personaggi.models import Mattone

from .componenti_nave_constants import AURA_COMPONENTI_SIGLA
from .componenti_riparazione import (
    _requisiti_normalizzati_da_raw,
    _stiva_disponibile,
)
from .componenti_stiva import build_stiva_payload


def ricarica_componenti_attiva_per(sottosistema) -> bool:
    from .models import PilotRuntimeConfig

    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.riparazione_componenti_abilitata:
        return False
    tipo = str(getattr(sottosistema, "tipo", "") or "").strip().lower()
    if tipo not in {"batteria", "serbatoio"}:
        return False
    return bool(getattr(sottosistema, "richiede_componenti_ricarica", False))


def _requisiti_ricarica_normalizzati(sottosistema) -> List[dict]:
    raw = getattr(sottosistema, "requisiti_ricarica_json", None) or []
    return _requisiti_normalizzati_da_raw(raw, richiedi_ricarica=True)


def build_requisiti_ricarica_payload(sottosistema) -> dict:
    requisiti = _requisiti_ricarica_normalizzati(sottosistema)
    mattoni_ids = set()
    for req in requisiti:
        if req["tipo"] == "specifico":
            mattoni_ids.add(req["mattone_id"])
        else:
            mattoni_ids.update(req["mattone_ids"])

    mattoni_map = {
        str(m.pk): m
        for m in Mattone.objects.filter(
            pk__in=mattoni_ids, aura__sigla=AURA_COMPONENTI_SIGLA
        ).select_related("caratteristica_associata")
    }

    tipo = str(getattr(sottosistema, "tipo", "") or "").strip().lower()
    unita_label = "energia storage" if tipo == "batteria" else "carburante"

    dettaglio = []
    ricarica_totale = 0.0
    for req in requisiti:
        ricarica_totale += float(req.get("ricarica") or 0)
        if req["tipo"] == "specifico":
            m = mattoni_map.get(req["mattone_id"])
            dettaglio.append(
                {
                    **req,
                    "mattone_nome": m.nome if m else None,
                    "colore_nome": m.caratteristica_associata.nome if m and m.caratteristica_associata else None,
                }
            )
        else:
            opzioni = []
            for mid in req["mattone_ids"]:
                m = mattoni_map.get(mid)
                if m:
                    opzioni.append(
                        {
                            "mattone_id": mid,
                            "mattone_nome": m.nome,
                            "colore_nome": m.caratteristica_associata.nome
                            if m.caratteristica_associata
                            else "",
                        }
                    )
            dettaglio.append({**req, "opzioni": opzioni})

    return {
        "richiede_componenti": ricarica_componenti_attiva_per(sottosistema),
        "tipo_ricarica": tipo,
        "unita_label": unita_label,
        "ricarica_totale_configurata": round(ricarica_totale, 3),
        "vincoli": dettaglio,
        "stiva": build_stiva_payload(),
    }


def valida_selezione_ricarica(sottosistema, selezione: List[dict]) -> Tuple[bool, str, List[dict], float]:
    """Valida selezione su requisiti_ricarica_json e ritorna importo ricarica totale."""
    requisiti = _requisiti_ricarica_normalizzati(sottosistema)
    if not requisiti:
        return False, "Nessun requisito ricarica configurato per questo sottosistema.", [], 0.0

    ok, err, allocazioni = _valida_selezione_su_requisiti(requisiti, selezione)
    if not ok:
        return False, err, [], 0.0

    ricarica = sum(float(r.get("ricarica") or 0) for r in requisiti)
    return True, "", allocazioni, ricarica


def _valida_selezione_su_requisiti(requisiti, selezione: List[dict]) -> Tuple[bool, str, List[dict]]:
    """Validazione vincoli identica a componenti_riparazione.valida_selezione_componenti."""
    if not isinstance(selezione, list) or not selezione:
        return False, "Seleziona i componenti necessari per la ricarica.", []

    alloc = {}
    for item in selezione:
        mid = str(item.get("mattone_id") or "").strip()
        qty = int(item.get("quantita") or 0)
        if not mid or qty <= 0:
            continue
        alloc[mid] = alloc.get(mid, 0) + qty

    if not alloc:
        return False, "Selezione componenti non valida.", []

    disponibile = _stiva_disponibile()
    for mid, qty in alloc.items():
        if disponibile.get(mid, 0) < qty:
            m = Mattone.objects.filter(pk=mid).first()
            nome = m.nome if m else mid
            return False, f"Componenti insufficienti in stiva: {nome}.", []

    residui = dict(alloc)
    for req in requisiti:
        qty = int(req["quantita"])
        if req["tipo"] == "specifico":
            mid = req["mattone_id"]
            used = min(residui.get(mid, 0), qty)
            if used < qty:
                return False, "Selezione non soddisfa i requisiti specifici.", []
            residui[mid] = residui.get(mid, 0) - used
        else:
            ids = req["mattone_ids"]
            remaining = qty
            for mid in ids:
                if remaining <= 0:
                    break
                take = min(residui.get(mid, 0), remaining)
                if take > 0:
                    residui[mid] = residui.get(mid, 0) - take
                    remaining -= take
            if remaining > 0:
                return False, "Selezione non soddisfa un gruppo a scelta.", []

    for qty in residui.values():
        if qty > 0:
            return False, "Selezione contiene componenti in eccesso.", []

    allocazioni = [{"mattone_id": mid, "quantita": qty} for mid, qty in alloc.items()]
    return True, "", allocazioni
