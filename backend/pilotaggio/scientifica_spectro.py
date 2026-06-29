"""
Console scientifica — Fase 1: spettrografia eventi e scan profondo.

Read-only analysis degli eventi attivi + consumo opzionale componenti stiva
per rivelare una condizione SP non ancora soddisfatta.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from .evento_codici import _conditions_from_regole

GRUPPO_COLORI = {
    "Propulsione e Manovra": "#00e5ff",
    "Difesa": "#b388ff",
    "Alimentazione": "#ffd54f",
    "Sistemi Interni": "#81c784",
    "Sistemi Esotici": "#ff80ab",
}
DEFAULT_BAND_COLOR = "#78909c"

PESO_SEZIONE = {"st": 3, "sp": 2, "ca": 1}


def _gruppo_sottosistema(codice: str) -> str:
    from .models import SottosistemaNave

    ss = SottosistemaNave.objects.filter(codice=str(codice or "").upper()[:1]).first()
    return (ss.gruppo if ss else "") or "Sistema"


def _livello_stato(stato) -> int:
    if stato is None or getattr(stato, "espulso", False) or not getattr(stato, "online", True):
        return 0
    return max(0, min(9, int(getattr(stato, "livello_attuale", 0) or 0)))


def _opposto_direzione(d: str) -> str:
    return {
        "avanti": "indietro",
        "indietro": "avanti",
        "su": "giu",
        "giu": "su",
        "destra": "sinistra",
        "sinistra": "destra",
    }.get(str(d or "").strip().lower(), "")


def _format_direzione(d: str) -> str:
    labels = {
        "avanti": "avanti",
        "indietro": "indietro",
        "su": "su",
        "giu": "giù",
        "destra": "destra",
        "sinistra": "sinistra",
    }
    return labels.get(str(d or "").strip().lower(), d or "?")


def _hint_condizione(cond: dict, stati_by_key: dict, direzione_evento: str) -> Optional[str]:
    from .engine import _eval_leaf

    ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
    if not ss:
        return None
    stato = stati_by_key.get(ss)
    nome = getattr(getattr(stato, "sottosistema", None), "nome", ss) if stato else ss
    op = str(cond.get("op") or "=").strip().lower()

    if _eval_leaf(cond, stati_by_key, direzione_evento):
        return None

    if stato is None or not getattr(stato, "online", True):
        return f"{ss} ({nome}): modulo offline o non disponibile"

    if getattr(stato, "espulso", False):
        return f"{ss} ({nome}): modulo espulso — reintegrazione da plancia"

    livello = _livello_stato(stato)
    tipo = str(getattr(stato.sottosistema, "tipo", "") or "").strip().lower()

    if op == "direction":
        rule = str(cond.get("direction_rule") or "stessa_direzione").strip().lower()
        dir_evt = _format_direzione(direzione_evento)
        dir_sub = _format_direzione(getattr(stato, "direzione", ""))
        if rule == "stessa_direzione":
            return f"{ss} (manovra): allineare direzione «{dir_evt}» (attuale «{dir_sub}»)"
        if rule == "direzione_opposta":
            opp = _format_direzione(_opposto_direzione(direzione_evento))
            return f"{ss} (manovra): direzione opposta all'evento → «{opp}» (attuale «{dir_sub}»)"
        return f"{ss} (manovra): regolare direzione propulsori"

    if op in {"invertito", "non_invertito"}:
        inv = bool(getattr(stato, "invertito", False))
        if op == "invertito" and not inv:
            return f"{ss} ({nome}): attivare inversione effetto"
        if op == "non_invertito" and inv:
            return f"{ss} ({nome}): disattivare inversione effetto"
        return None

    if op in {"espulso", "non_espulso"}:
        return f"{ss} ({nome}): verificare stato espulsione modulo"

    if tipo in {"batteria", "serbatoio"} and op in {"piene", "vuote", "non_piene", "non_vuote", "distrutte"}:
        labels = {
            "piene": "carica piena",
            "vuote": "scarico/vuoto",
            "non_piene": "non al massimo",
            "non_vuote": "non vuoto",
            "distrutte": "offline",
        }
        return f"{ss} ({nome}): richiesto stato «{labels.get(op, op)}»"

    def _int_val(key, default=0):
        try:
            return int(cond.get(key, default))
        except (TypeError, ValueError):
            return default

    if op in {"=", "eq"}:
        target = _int_val("value", livello)
        if livello != target:
            delta = target - livello
            segno = "+" if delta > 0 else ""
            return f"{ss} ({nome}): livello target {target} (attuale {livello}, {segno}{delta})"
    elif op in {">", "gt"}:
        target = _int_val("value", 0)
        if livello <= target:
            return f"{ss} ({nome}): serve livello > {target} (attuale {livello})"
    elif op in {">=", "gte"}:
        target = _int_val("value", 0)
        if livello < target:
            return f"{ss} ({nome}): serve livello ≥ {target} (attuale {livello})"
    elif op in {"<", "lt"}:
        target = _int_val("value", 9)
        if livello >= target:
            return f"{ss} ({nome}): serve livello < {target} (attuale {livello})"
    elif op in {"<=", "lte"}:
        target = _int_val("value", 9)
        if livello > target:
            return f"{ss} ({nome}): serve livello ≤ {target} (attuale {livello})"
    elif op == "between":
        lo = _int_val("min", 0)
        hi = _int_val("max", 9)
        if lo > hi:
            lo, hi = hi, lo
        if not (lo <= livello <= hi):
            return f"{ss} ({nome}): livello tra {lo} e {hi} (attuale {livello})"
    return f"{ss} ({nome}): regolare parametri operativi"


def _raccogli_condizioni(regole: dict) -> List[Tuple[str, dict]]:
    out: List[Tuple[str, dict]] = []
    for sezione in ("st", "sp", "ca"):
        for cond in _conditions_from_regole(regole or {}, sezione):
            out.append((sezione, cond))
    return out


def _firma_spettrale(regole: dict) -> List[dict]:
    pesi: Dict[str, float] = {}
    for sezione, cond in _raccogli_condizioni(regole):
        ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
        if not ss:
            continue
        gruppo = _gruppo_sottosistema(ss)
        pesi[gruppo] = pesi.get(gruppo, 0.0) + float(PESO_SEZIONE.get(sezione, 1))
    if not pesi:
        return []
    max_p = max(pesi.values()) or 1.0
    bands = []
    for gruppo, peso in sorted(pesi.items(), key=lambda x: (-x[1], x[0].lower())):
        bands.append(
            {
                "gruppo": gruppo,
                "intensita": round(min(100.0, (peso / max_p) * 100.0), 1),
                "colore": GRUPPO_COLORI.get(gruppo, DEFAULT_BAND_COLOR),
            }
        )
    return bands


def _delta_navigazione(
    regole: dict,
    stati_by_key: dict,
    direzione_evento: str,
    *,
    max_voci: int = 6,
) -> List[str]:
    from .engine import _eval_soluzione_totale

    if _eval_soluzione_totale(regole, stati_by_key, direzione_evento):
        return ["Configurazione ST soddisfatta — attendere prossima valutazione tick."]

    voci: List[str] = []
    seen = set()
    for sezione in ("st", "sp"):
        for cond in _conditions_from_regole(regole or {}, sezione):
            hint = _hint_condizione(cond, stati_by_key, direzione_evento)
            if not hint or hint in seen:
                continue
            seen.add(hint)
            voci.append(hint)
            if len(voci) >= max_voci:
                return voci
    if not voci:
        voci.append("Nessun delta rilevabile — verificare livelli plancia e manovra.")
    return voci


def _stato_rischio_ca(
    istanza,
    regole: dict,
    stati_by_key: dict,
    direzione_evento: str,
) -> dict:
    from .engine import _ca_scadenza_critica_permessa, _eval_outcome_regole

    if not _ca_scadenza_critica_permessa(istanza):
        return {
            "livello": "reazione",
            "etichetta": "Tempo di reazione",
            "descrizione": "Valutazione CA disattivata fino al primo tick operativo.",
        }
    ca_attiva = _eval_outcome_regole(regole, "ca", stati_by_key, direzione_evento)
    if ca_attiva:
        return {
            "livello": "critico",
            "etichetta": "CA attiva",
            "descrizione": "Condizione catastrofe soddisfatta — rischio effetto CA imminente.",
        }
    ca_vicine = []
    for cond in _conditions_from_regole(regole or {}, "ca"):
        ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
        if not ss:
            continue
        stato = stati_by_key.get(ss)
        if stato and _livello_stato(stato) >= max(0, int(cond.get("value", 0) or 0) - 1):
            ca_vicine.append(ss)
    if ca_vicine:
        return {
            "livello": "elevato",
            "etichetta": "Rischio elevato",
            "descrizione": f"Sottosistemi sensibili CA: {', '.join(sorted(set(ca_vicine)))}.",
        }
    return {
        "livello": "moderato",
        "etichetta": "Monitoraggio",
        "descrizione": "Nessuna condizione CA attiva al momento.",
    }


def _stato_sp_st(
    regole: dict,
    stati_by_key: dict,
    direzione_evento: str,
) -> dict:
    from .engine import _eval_soluzione_parziale, _eval_soluzione_totale

    st = _eval_soluzione_totale(regole, stati_by_key, direzione_evento)
    sp = _eval_soluzione_parziale(regole, stati_by_key, direzione_evento)
    if st:
        return {"codice": "st_ok", "etichetta": "Soluzione totale", "descrizione": "Formula ST verificata."}
    if sp:
        return {
            "codice": "sp_ok",
            "etichetta": "Parziale stabilizzata",
            "descrizione": "Configurazione SP soddisfatta; serve affinamento per ST.",
        }
    return {
        "codice": "in_corso",
        "etichetta": "In analisi",
        "descrizione": "Né ST né SP soddisfatti — regolare sottosistemi indicati.",
    }


def _cronometro_evento(sessione, istanza) -> dict:
    from .engine import intervallo_tick_effettivo_sessione, secondi_fino_valutazione_evento

    tick_sec = float(intervallo_tick_effettivo_sessione(sessione))
    ticks = int(istanza.ticks_rimanenti) if istanza.ticks_rimanenti is not None else None
    sec_fino = secondi_fino_valutazione_evento(sessione)
    return {
        "ticks_rimanenti": ticks,
        "secondi_per_tick": round(tick_sec, 2),
        "secondi_stimati_totali": round(ticks * tick_sec, 1) if ticks is not None else None,
        "secondi_fino_prossima_valutazione": round(sec_fino, 1) if sec_fino is not None else None,
        "reazione_fino_at": (
            istanza.reazione_fino_at.isoformat() if istanza.reazione_fino_at else None
        ),
    }


def _scan_requisiti_payload(cfg) -> dict:
    from .componenti_riparazione import _requisiti_normalizzati_da_raw
    from .componenti_stiva import build_stiva_payload, mattoni_componente_qs

    raw = getattr(cfg, "scientifica_scan_requisiti_json", None) or []
    vincoli = _requisiti_normalizzati_da_raw(raw, richiedi_ricarica=False)
    if not vincoli:
        ids = [str(m.pk) for m in mattoni_componente_qs()]
        if ids:
            vincoli = [{"tipo": "scelta", "mattone_ids": ids, "quantita": 1}]
    return {
        "abilitato": bool(getattr(cfg, "scientifica_scan_profondo_abilitato", True)),
        "vincoli": vincoli,
        "stiva": build_stiva_payload(),
        "max_per_volo": int(getattr(cfg, "scientifica_scan_max_per_volo", 2) or 2),
    }


def _valida_consumo_scan(cfg, componenti_scelti: list) -> Tuple[bool, str, List[dict]]:
    from .componenti_riparazione import _requisiti_normalizzati_da_raw, valida_selezione_componenti
    from .componenti_stiva import mattoni_componente_qs

    if not getattr(cfg, "scientifica_scan_profondo_abilitato", True):
        return False, "Scan profondo disabilitato in runtime.", []

    raw = getattr(cfg, "scientifica_scan_requisiti_json", None) or []
    requisiti = _requisiti_normalizzati_da_raw(raw, richiedi_ricarica=False)
    if not requisiti:
        if not isinstance(componenti_scelti, list) or len(componenti_scelti) != 1:
            return False, "Seleziona un componente dalla stiva.", []
        mid = str(componenti_scelti[0].get("mattone_id") or "").strip()
        qty = int(componenti_scelti[0].get("quantita") or 0)
        if not mid or qty != 1:
            return False, "Scan profondo: 1 componente richiesto.", []
        return True, "", [{"mattone_id": mid, "quantita": 1}]

    class _FakeSS:
        requisiti_riparazione_json = requisiti
        richiede_componenti_riparazione = True

    return valida_selezione_componenti(_FakeSS(), componenti_scelti)


def _primo_hint_sp_non_soddisfatto(
    regole: dict,
    stati_by_key: dict,
    direzione_evento: str,
) -> Optional[dict]:
    from .engine import _eval_leaf

    for cond in _conditions_from_regole(regole or {}, "sp"):
        if _eval_leaf(cond, stati_by_key, direzione_evento):
            continue
        hint = _hint_condizione(cond, stati_by_key, direzione_evento)
        if not hint:
            continue
        ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
        return {
            "sezione": "sp",
            "sottosistema": ss,
            "gruppo": _gruppo_sottosistema(ss),
            "messaggio": hint,
            "operatore": str(cond.get("op") or ""),
        }
    for cond in _conditions_from_regole(regole or {}, "st"):
        if _eval_leaf(cond, stati_by_key, direzione_evento):
            continue
        hint = _hint_condizione(cond, stati_by_key, direzione_evento)
        if hint:
            ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
            return {
                "sezione": "st",
                "sottosistema": ss,
                "gruppo": _gruppo_sottosistema(ss),
                "messaggio": hint,
                "operatore": str(cond.get("op") or ""),
            }
    return None


def build_spectrografia_evento(sessione, istanza) -> dict:
    from .engine import _stati_by_key_sessione

    regole = istanza.evento.regole_json or {}
    stati_by_key = _stati_by_key_sessione(sessione)
    direzione = istanza.direzione_evento or ""

    return {
        "evento_id": str(istanza.pk),
        "evento_nome": istanza.evento.nome,
        "evento_descrizione": (istanza.evento.descrizione or "").replace(
            "<direzione>", str(direzione)
        ),
        "direzione_evento": direzione,
        "firma_spettrale": _firma_spettrale(regole),
        "delta_navigazione": _delta_navigazione(regole, stati_by_key, direzione),
        "stato_soluzione": _stato_sp_st(regole, stati_by_key, direzione),
        "rischio_ca": _stato_rischio_ca(istanza, regole, stati_by_key, direzione),
        "cronometro": _cronometro_evento(sessione, istanza),
        "scan_profondo": {
            "eseguito_su_questo_evento": bool(istanza.scan_profondo_eseguito),
            "indizio": istanza.scan_profondo_hint_json or None,
        },
    }


def build_scientifica_state_payload() -> dict:
    from .engine import evento_attivo_corrente
    from .models import EVENTO_ESITO_PENDING, PilotRuntimeConfig
    from .views import _sessione_attiva_corrente

    cfg = PilotRuntimeConfig.get_solo()
    sessione = _sessione_attiva_corrente()
    istanza = None
    spettro = None

    if sessione is not None and sessione.is_attiva:
        istanza = evento_attivo_corrente(sessione)
        if istanza is not None and istanza.esito == EVENTO_ESITO_PENDING:
            spettro = build_spectrografia_evento(sessione, istanza)

    scans_usati = int(getattr(sessione, "scans_profondi_count", 0) or 0) if sessione else 0
    max_scans = int(getattr(cfg, "scientifica_scan_max_per_volo", 2) or 2)
    req = _scan_requisiti_payload(cfg)

    from .scientifica_engine import build_interventi_payload, build_matrice_payload

    matrice = build_matrice_payload(sessione)
    interventi = build_interventi_payload(sessione, istanza)

    return {
        "abilitato": bool(cfg.scientifica_console_abilitata),
        "sessione_attiva": sessione is not None and bool(sessione.is_attiva),
        "sessione_id": str(sessione.pk) if sessione else None,
        "defcon": int(sessione.defcon or 0) if sessione else 0,
        "evento_pending": istanza is not None and istanza.esito == EVENTO_ESITO_PENDING,
        "spettrografia": spettro,
        "matrice": matrice,
        "interventi": interventi,
        "scan_profondo": {
            **req,
            "scans_usati_volo": scans_usati,
            "scans_rimanenti_volo": max(0, max_scans - scans_usati),
            "disponibile": bool(
                req["abilitato"]
                and spettro is not None
                and istanza is not None
                and not istanza.scan_profondo_eseguito
                and scans_usati < max_scans
            ),
        },
    }


@transaction.atomic
def esegui_scan_profondo(*, componenti_scelti: list) -> dict:
    from .componenti_stiva import consuma_mattoni_stiva
    from .engine import evento_attivo_corrente
    from .models import EVENTO_ESITO_PENDING, PilotRuntimeConfig
    from .views import _sessione_attiva_corrente

    cfg = PilotRuntimeConfig.get_solo()
    sessione = _sessione_attiva_corrente()
    if sessione is None or not sessione.is_attiva:
        raise ValueError("Nessuna sessione di volo attiva.")

    istanza = evento_attivo_corrente(sessione)
    if istanza is None or istanza.esito != EVENTO_ESITO_PENDING:
        raise ValueError("Nessun evento attivo da analizzare.")

    if istanza.scan_profondo_eseguito:
        raise ValueError("Scan profondo già eseguito su questo evento.")

    max_scans = int(getattr(cfg, "scientifica_scan_max_per_volo", 2) or 2)
    if int(sessione.scans_profondi_count or 0) >= max_scans:
        raise ValueError("Limite scan profondi per volo raggiunto.")

    ok, err, alloc = _valida_consumo_scan(cfg, componenti_scelti)
    if not ok:
        raise ValueError(err)

    from .engine import _stati_by_key_sessione

    regole = istanza.evento.regole_json or {}
    stati_by_key = _stati_by_key_sessione(sessione)
    hint = _primo_hint_sp_non_soddisfatto(regole, stati_by_key, istanza.direzione_evento or "")
    if hint is None:
        raise ValueError("Nessuna condizione SP/ST da rivelare — configurazione già vicina alla soluzione.")

    consuma_mattoni_stiva(alloc)
    istanza.scan_profondo_eseguito = True
    istanza.scan_profondo_hint_json = hint
    istanza.save(update_fields=["scan_profondo_eseguito", "scan_profondo_hint_json", "updated_at"])
    sessione.scans_profondi_count = int(sessione.scans_profondi_count or 0) + 1
    sessione.save(update_fields=["scans_profondi_count", "updated_at"])

    payload = build_scientifica_state_payload()
    payload["scan_eseguito"] = hint
    return payload
