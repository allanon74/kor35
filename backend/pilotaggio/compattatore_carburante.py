"""
Sintesi carburante dal Compattatore: brucia componenti di stiva e riempie i serbatoi.

Taratura rispetto ai reattori (migrazione 0011):
- K (principale): 3.2 carburante/tick per livello
- L (ausiliario): 6.4 carburante/tick per livello
- Crociera tipica K=5 + L=2 → 28.8 carburante/tick
- Picco K=9 + L=9 → 86.4 carburante/tick

Energia interna Compattatore: +livello Z per tick, operazione da 9.
- Z=1 → 1 operazione ogni 9 tick (dock / nave ferma)
- Z=9 → 1 operazione per tick

Un ingegnere capace (Z alto, componenti medi/alti, 2–3 unità) produce più
carburante di quanto i reattori ne brucino in crociera. A Z=1 si rifornisce
solo a nave ferma, troppo lento per sostenere il volo.
"""
from __future__ import annotations

from typing import Any, Dict, List  # noqa: F401 — List used throughout

# Resa per unità di indice 0 a efficienza 1.0
BASE_RESA_INDICE_0 = 14.0
# densità = BASE * (1 + BONUS_INDICE * indice)  → indice 9 ≈ 36.7
BONUS_INDICE = 0.18
# eta(Z) = ETA_BASE + ETA_PER_LIVELLO * Z  → Z1=0.49, Z9=1.05
ETA_BASE = 0.42
ETA_PER_LIVELLO = 0.07
# Bonus se la carica mescola almeno 2 indici distinti (miscela catalitica)
BONUS_MISCELA = 1.22
QUANTITA_MIN = 1
QUANTITA_MAX = 3

CROCIERA_TIPICA_CARBURANTE_PER_TICK = 5.0 * 3.2 + 2.0 * 6.4  # 28.8
PICCO_REATTORI_CARBURANTE_PER_TICK = 9.0 * 3.2 + 9.0 * 6.4  # 86.4


def efficienza_livello(livello: int) -> float:
    lv = max(0, min(9, int(livello or 0)))
    if lv <= 0:
        return 0.0
    return round(ETA_BASE + ETA_PER_LIVELLO * lv, 4)


def densita_indice(indice: int) -> float:
    idx = max(0, min(9, int(indice or 0)))
    return round(BASE_RESA_INDICE_0 * (1.0 + BONUS_INDICE * idx), 4)


def calcola_resa_sintesi(*, unita: List[Dict[str, Any]], livello: int) -> float:
    """`unita`: lista {indice, quantita}. Totale quantità 1–3."""
    eta = efficienza_livello(livello)
    if eta <= 0:
        return 0.0
    totale_qty = 0
    indici = set()
    grezzo = 0.0
    for u in unita:
        qty = int(u.get("quantita") or 0)
        if qty <= 0:
            continue
        idx = int(
            u.get("indice")
            if u.get("indice") is not None
            else u.get("indice_componente") or 0
        )
        totale_qty += qty
        indici.add(idx)
        grezzo += densita_indice(idx) * qty
    if totale_qty < QUANTITA_MIN or totale_qty > QUANTITA_MAX:
        return 0.0
    mix = BONUS_MISCELA if len(indici) >= 2 else 1.0
    return round(grezzo * eta * mix, 3)


def descrizione_formula() -> Dict[str, Any]:
    return {
        "base_resa_indice_0": BASE_RESA_INDICE_0,
        "bonus_indice": BONUS_INDICE,
        "eta_base": ETA_BASE,
        "eta_per_livello": ETA_PER_LIVELLO,
        "bonus_miscela": BONUS_MISCELA,
        "quantita_min": QUANTITA_MIN,
        "quantita_max": QUANTITA_MAX,
        "crociera_tipica_carburante_per_tick": CROCIERA_TIPICA_CARBURANTE_PER_TICK,
        "picco_reattori_carburante_per_tick": PICCO_REATTORI_CARBURANTE_PER_TICK,
        "testo": (
            "Resa = Σ (14 × (1 + 0.18×indice) × qty) × η(Z) × miscela. "
            "η(Z) = 0.42 + 0.07×Z (Z1=49%, Z9=105%). "
            "Miscela (+22%) se si bruciano almeno due indici distinti."
        ),
    }


def nave_ferma_per_compattatore(sessione=None) -> bool:
    """True se non c'è crociera (idle, pre-decollo, o nessuna sessione)."""
    from .engine import _sessione_ha_decollato, sessione_nave_operativa

    if sessione is None:
        sessione = sessione_nave_operativa()
    if sessione is None:
        return True
    return not _sessione_ha_decollato(sessione)


def _sessione_serbatoio():
    from .engine import sessione_nave_operativa
    from .models import SessioneVolo

    sessione = sessione_nave_operativa()
    if sessione is not None:
        return sessione
    return SessioneVolo.objects.order_by("-created_at").first()


def payload_carburante_sessione() -> Dict[str, Any]:
    from .engine import capacita_carburante_serbatoi

    sessione = _sessione_serbatoio()
    massimo = capacita_carburante_serbatoi()
    attuale = float(getattr(sessione, "carburante_attuale", 0) or 0) if sessione else 0.0
    if sessione is not None:
        massimo = max(massimo, float(sessione.carburante_massimo or 0) or massimo)
        attuale = min(attuale, massimo)
    return {
        "carburante_attuale": round(attuale, 3),
        "carburante_massimo": round(massimo, 3),
        "sessione_id": str(sessione.pk) if sessione else None,
        "nave_ferma": nave_ferma_per_compattatore(sessione),
    }


def applica_carburante_sintesi(resa: float) -> Dict[str, Any]:
    from .engine import capacita_carburante_serbatoi

    if resa <= 0:
        raise ValueError("Resa carburante nulla.")
    sessione = _sessione_serbatoio()
    if sessione is None:
        raise ValueError(
            "Nessun serbatoio di sessione: avviare la plancia almeno una volta."
        )
    massimo = capacita_carburante_serbatoi()
    if float(sessione.carburante_massimo or 0) > massimo:
        massimo = float(sessione.carburante_massimo or massimo)
    prima = float(sessione.carburante_attuale or 0.0)
    spazio = max(0.0, massimo - prima)
    aggiunto = min(float(resa), spazio)
    sessione.carburante_massimo = massimo
    sessione.carburante_attuale = round(prima + aggiunto, 3)
    sessione.save(
        update_fields=["carburante_massimo", "carburante_attuale", "updated_at"]
    )
    return {
        "carburante_prima": round(prima, 3),
        "carburante_attuale": sessione.carburante_attuale,
        "carburante_massimo": massimo,
        "resa_calcolata": round(float(resa), 3),
        "aggiunto": round(aggiunto, 3),
        "sversato": round(max(0.0, float(resa) - aggiunto), 3),
    }


def stima_da_allocazioni(allocazioni: List[dict], livello: int) -> Dict[str, Any]:
    from personaggi.models import Mattone

    from .componenti_nave_constants import AURA_COMPONENTI_SIGLA

    unita = []
    for row in allocazioni:
        mid = str(row.get("mattone_id") or "").strip()
        qty = int(row.get("quantita") or 0)
        if not mid or qty <= 0:
            continue
        m = Mattone.objects.filter(pk=mid, aura__sigla=AURA_COMPONENTI_SIGLA).first()
        if m is None or m.indice_componente is None:
            raise ValueError("Componente non valido per la sintesi.")
        unita.append(
            {
                "mattone_id": str(m.pk),
                "indice": int(m.indice_componente),
                "quantita": qty,
                "nome": m.nome,
            }
        )
    tot = sum(u["quantita"] for u in unita)
    if tot < QUANTITA_MIN or tot > QUANTITA_MAX:
        raise ValueError(
            f"Bruciare da {QUANTITA_MIN} a {QUANTITA_MAX} unità per operazione."
        )
    resa = calcola_resa_sintesi(unita=unita, livello=livello)
    return {
        "unita": unita,
        "quantita_totale": tot,
        "livello": livello,
        "efficienza": efficienza_livello(livello),
        "miscela": len({u["indice"] for u in unita}) >= 2,
        "resa": resa,
        "formula": descrizione_formula(),
    }
