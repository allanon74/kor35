"""
Validazione requisiti componenti per riparazione sottosistema.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from personaggi.models import Mattone

from .componenti_nave_constants import AURA_COMPONENTI_SIGLA
from .componenti_stiva import build_stiva_payload


def riparazione_componenti_attiva_per(sottosistema) -> bool:
    from .models import PilotRuntimeConfig

    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.riparazione_componenti_abilitata:
        return False
    return bool(getattr(sottosistema, "richiede_componenti_riparazione", False))


def _requisiti_normalizzati(sottosistema) -> List[dict]:
    raw = getattr(sottosistema, "requisiti_riparazione_json", None) or []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        tipo = str(item.get("tipo") or "").strip().lower()
        qty = int(item.get("quantita") or 0)
        if qty <= 0:
            continue
        if tipo == "specifico":
            mid = item.get("mattone_id")
            if mid:
                out.append({"tipo": "specifico", "mattone_id": str(mid), "quantita": qty})
        elif tipo == "scelta":
            ids = item.get("mattone_ids") or []
            norm_ids = [str(x) for x in ids if x]
            if norm_ids:
                out.append({"tipo": "scelta", "mattone_ids": norm_ids, "quantita": qty})
    return out


def build_requisiti_riparazione_payload(sottosistema) -> dict:
    requisiti = _requisiti_normalizzati(sottosistema)
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

    dettaglio = []
    for req in requisiti:
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
        "richiede_componenti": riparazione_componenti_attiva_per(sottosistema),
        "vincoli": dettaglio,
        "stiva": build_stiva_payload(),
    }


def _stiva_disponibile() -> Dict[str, int]:
    payload = build_stiva_payload()
    out: Dict[str, int] = {}
    for r in payload.get("righe") or []:
        out[str(r["mattone_id"])] = int(r["quantita"])
    return out


def valida_selezione_componenti(
    sottosistema, selezione: List[dict]
) -> Tuple[bool, str, List[dict]]:
    """
    selezione: [{mattone_id, quantita}, ...]
    Ritorna (ok, errore, allocazioni_normalizzate).
    """
    requisiti = _requisiti_normalizzati(sottosistema)
    if not requisiti:
        return False, "Nessun requisito componenti configurato per questo sottosistema.", []

    if not isinstance(selezione, list) or not selezione:
        return False, "Seleziona i componenti necessari per la riparazione.", []

    alloc: Dict[str, int] = {}
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

    # soddisfacibilità vincoli
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

    # nessun extra obbligatorio ma warn se residui > 0? accettiamo extra solo se copre esattamente
    for mid, qty in residui.items():
        if qty > 0:
            return False, "Selezione contiene componenti in eccesso.", []

    allocazioni = [{"mattone_id": mid, "quantita": qty} for mid, qty in alloc.items()]
    return True, "", allocazioni
