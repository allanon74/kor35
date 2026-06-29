"""
Console scientifica — Fase 2: matrice R/S/T, coerenza di campo, interventi attivi.
"""
from __future__ import annotations

from typing import Optional

from django.db import transaction
from django.utils import timezone

ESOTICI = (
    ("R", "Nucleo Temporale"),
    ("S", "Nucleo Dimensionale"),
    ("T", "Correttore Paradossi"),
)

INTERVENTI = {
    "dilatazione": {
        "label": "Dilatazione temporale",
        "descrizione": "+1 tick rimanente sull'evento attivo.",
        "coerenza": 8,
        "componenti": 1,
        "max_per_evento": 2,
        "conta_limite_volo": True,
    },
    "gabbia": {
        "label": "Gabbia dimensionale",
        "descrizione": "Sopprime la prossima valutazione CA sull'evento.",
        "coerenza": 10,
        "componenti": 2,
        "max_per_evento": 1,
        "conta_limite_volo": True,
    },
    "correzione": {
        "label": "Correzione paradosso",
        "descrizione": "DEFCON -1 senza risolvere l'evento (max 1 per fenomeno).",
        "coerenza": 12,
        "componenti": 1,
        "max_per_evento": 1,
        "conta_limite_volo": True,
    },
    "eco": {
        "label": "Eco parziale",
        "descrizione": "Prossima valutazione SP non consuma tick.",
        "coerenza": 6,
        "componenti": 0,
        "max_per_evento": 1,
        "conta_limite_volo": True,
    },
    "reset_risonanza": {
        "label": "Reset risonanza",
        "descrizione": "Azzera le fasi R/S/T della matrice.",
        "coerenza": 0,
        "componenti": 0,
        "max_per_evento": None,
        "conta_limite_volo": False,
    },
}


def _clamp_fase(value: int) -> int:
    return max(0, min(2, int(value or 0)))


def _metriche_esotici_sessione(sessione) -> tuple[dict[str, dict], float]:
    """
    Metriche runtime R/S/T: livello, energia assorbita/tick (livello × coeff_consumo).
    """
    from .engine import _stati_by_key_sessione

    stati = _stati_by_key_sessione(sessione)
    nuclei: dict[str, dict] = {}
    energia_totale = 0.0
    for codice, nome in ESOTICI:
        st = stati.get(codice)
        online = bool(st and st.online and not getattr(st, "espulso", False))
        livello = int(getattr(st, "livello_attuale", 0) or 0) if st and online else 0
        coeff = 0.0
        if st is not None:
            coeff = float(getattr(st.sottosistema, "coeff_consumo_energia", 0) or 0)
        energia = livello * coeff if online and livello > 0 else 0.0
        energia_totale += energia
        nuclei[codice] = {
            "codice": codice,
            "nome": nome,
            "online": online,
            "livello": livello,
            "coeff_consumo_energia": round(coeff, 2),
            "energia_per_tick": round(energia, 2),
        }
    return nuclei, energia_totale


def _livelli_esotici_sessione(sessione) -> dict[str, dict]:
    nuclei, _ = _metriche_esotici_sessione(sessione)
    return nuclei


def _soglia_energia_minima(cfg) -> float:
    """Energia/tick minima (≈ livello min su tutti e tre i nuclei)."""
    min_lv = int(getattr(cfg, "scientifica_livello_min_esotici", 1) or 1)
    if min_lv <= 0:
        return 0.0
    # R=1.8, S=1.9, T=2.1 — media conservativa per nucleo
    return float(min_lv) * (1.8 + 1.9 + 2.1)


def _coerenza_da_energia(energia: float, cfg) -> int:
    divisore = max(0.5, float(getattr(cfg, "scientifica_energia_per_coerenza", 4.0) or 4.0))
    if energia <= 0:
        return 0
    return max(1, int(energia / divisore))


def _carica_da_energia(energia: float, cfg, carica_attuale: int) -> int:
    soglia = int(getattr(cfg, "scientifica_carica_intervento_soglia", 100) or 100)
    cap = max(1, min(100, soglia))
    fattore = max(0.1, float(getattr(cfg, "scientifica_carica_per_energia", 5.0) or 5.0))
    if energia <= 0:
        return int(carica_attuale or 0)
    delta = int(energia * fattore)
    return min(cap, int(carica_attuale or 0) + max(1, delta))


def _requisiti_intervento(cfg, tipo: str) -> list:
    raw = getattr(cfg, "scientifica_interventi_requisiti_json", None) or {}
    if isinstance(raw, dict):
        req = raw.get(tipo)
        if req is not None:
            return req if isinstance(req, list) else []
    return []


def _valida_consumo_componenti(cfg, componenti_scelti: list, *, tipo: str, n_richiesti: int):
    from .componenti_riparazione import _requisiti_normalizzati_da_raw, valida_selezione_componenti

    if n_richiesti <= 0:
        return True, "", []
    requisiti_raw = _requisiti_intervento(cfg, tipo)
    if requisiti_raw:
        requisiti = _requisiti_normalizzati_da_raw(requisiti_raw, richiedi_ricarica=False)
        if requisiti:
            class _FakeSS:
                requisiti_riparazione_json = requisiti
                richiede_componenti_riparazione = True

            return valida_selezione_componenti(_FakeSS(), componenti_scelti)
    if not componenti_scelti:
        return False, f"Servono {n_richiesti} componente/i dalla stiva.", []
    tot = sum(int(c.get("quantita") or 0) for c in componenti_scelti if isinstance(c, dict))
    if tot < n_richiesti:
        return False, f"Servono {n_richiesti} componente/i (selezionati: {tot}).", []
    alloc = []
    rim = n_richiesti
    for row in componenti_scelti:
        if not isinstance(row, dict):
            continue
        q = min(rim, int(row.get("quantita") or 0))
        if q <= 0:
            continue
        alloc.append({"mattone_id": row.get("mattone_id"), "quantita": q})
        rim -= q
        if rim <= 0:
            break
    if rim > 0:
        return False, f"Servono {n_richiesti} componente/i dalla stiva.", []
    return True, "", alloc


def build_matrice_payload(sessione) -> dict:
    from .models import PilotRuntimeConfig, ScientificoStatoNave

    cfg = PilotRuntimeConfig.get_solo()
    stato = ScientificoStatoNave.get_solo()
    nuclei_dict, energia_totale = (
        _metriche_esotici_sessione(sessione)
        if sessione
        else ({c: {"codice": c, "nome": n, "online": False, "livello": 0, "energia_per_tick": 0} for c, n in ESOTICI}, 0.0)
    )
    cap = int(getattr(cfg, "scientifica_coerenza_cap", 24) or 24)
    soglia_energia = _soglia_energia_minima(cfg)
    esotici_ok = energia_totale >= soglia_energia
    carica_soglia = int(getattr(cfg, "scientifica_carica_intervento_soglia", 100) or 100)
    carica = int(stato.carica_intervento or 0)
    risonanza_tripla = (
        stato.fase_r == 2 and stato.fase_s == 2 and stato.fase_t == 2 and esotici_ok
    )
    nuclei = []
    fasi = {"R": stato.fase_r, "S": stato.fase_s, "T": stato.fase_t}
    for codice, nome in ESOTICI:
        lv = nuclei_dict[codice]
        nuclei.append(
            {
                "codice": codice,
                "nome": nome,
                "fase": int(fasi[codice]),
                "online": lv["online"],
                "livello": lv["livello"],
                "energia_per_tick": lv.get("energia_per_tick", 0),
            }
        )
    return {
        "coerenza": int(stato.coerenza_accumulata or 0),
        "coerenza_cap": cap,
        "esotici_alimentano_coerenza": esotici_ok,
        "energia_esotici_per_tick": round(energia_totale, 2),
        "energia_minima_richiesta": round(soglia_energia, 2),
        "carica_intervento": carica,
        "carica_intervento_soglia": carica_soglia,
        "carica_pronta": carica >= carica_soglia,
        "risonanza_tripla": risonanza_tripla,
        "nuclei": nuclei,
    }


def _interventi_catalogo(cfg, sessione, istanza) -> list[dict]:
    from .models import ScientificoStatoNave

    max_volo = int(getattr(cfg, "scientifica_interventi_max_per_volo", 12) or 12)
    usati_volo = int(getattr(sessione, "interventi_scientifici_count", 0) or 0) if sessione else 0
    stato = ScientificoStatoNave.get_solo()
    carica_soglia = int(getattr(cfg, "scientifica_carica_intervento_soglia", 100) or 100)
    carica = int(stato.carica_intervento or 0)
    out = []
    for tipo, meta in INTERVENTI.items():
        disponibile = bool(getattr(cfg, "scientifica_interventi_abilitati", True))
        motivo = ""
        if not disponibile:
            motivo = "Interventi disabilitati in runtime."
        elif sessione is None or not sessione.is_attiva:
            disponibile = False
            motivo = "Nessun volo attivo."
        elif tipo != "reset_risonanza" and istanza is None:
            disponibile = False
            motivo = "Nessun evento attivo."
        elif meta.get("conta_limite_volo") and carica < carica_soglia:
            disponibile = False
            motivo = (
                f"Carica campo insufficiente ({carica}/{carica_soglia}) — "
                "aumenta energia su R/S/T."
            )
        elif meta.get("conta_limite_volo") and usati_volo >= max_volo:
            disponibile = False
            motivo = "Limite interventi per volo raggiunto."
        elif istanza is not None and meta.get("max_per_evento") is not None:
            if tipo == "dilatazione" and istanza.dilatazioni_applicate >= meta["max_per_evento"]:
                disponibile = False
                motivo = "Limite dilatazioni su questo evento."
            elif tipo == "gabbia" and istanza.ca_soppressa_scientifica:
                disponibile = False
                motivo = "Gabbia già armata su questo evento."
            elif tipo == "correzione" and istanza.correzione_paradosso_applicata:
                disponibile = False
                motivo = "Correzione già applicata su questo evento."
            elif tipo == "eco" and istanza.eco_parziale_attiva:
                disponibile = False
                motivo = "Eco parziale già attiva su questo evento."
        if tipo == "dilatazione" and istanza is not None and istanza.ticks_rimanenti is None:
            disponibile = False
            motivo = "Evento a durata infinita — dilatazione non applicabile."

        out.append(
            {
                "tipo": tipo,
                "label": meta["label"],
                "descrizione": meta["descrizione"],
                "coerenza": meta["coerenza"],
                "componenti": meta["componenti"],
                "disponibile": disponibile,
                "motivo_indisponibile": motivo if not disponibile else "",
            }
        )
    return out


def build_interventi_payload(sessione, istanza) -> dict:
    from .models import PilotRuntimeConfig

    cfg = PilotRuntimeConfig.get_solo()
    max_volo = int(getattr(cfg, "scientifica_interventi_max_per_volo", 12) or 12)
    usati = int(getattr(sessione, "interventi_scientifici_count", 0) or 0) if sessione else 0
    flags = {}
    if istanza is not None:
        flags = {
            "ca_soppressa_armata": bool(istanza.ca_soppressa_scientifica),
            "eco_parziale_attiva": bool(istanza.eco_parziale_attiva),
            "dilatazioni_applicate": int(istanza.dilatazioni_applicate or 0),
            "correzione_applicata": bool(istanza.correzione_paradosso_applicata),
        }
    return {
        "abilitati": bool(getattr(cfg, "scientifica_interventi_abilitati", True)),
        "interventi_usati_volo": usati,
        "interventi_rimanenti_volo": max(0, max_volo - usati),
        "flags_evento": flags,
        "catalogo": _interventi_catalogo(cfg, sessione, istanza),
    }


def reset_stato_scientifica_volo() -> None:
    """Azzera coerenza e fasi a fine/inizio volo."""
    from .models import ScientificoStatoNave

    stato = ScientificoStatoNave.get_solo()
    stato.coerenza_accumulata = 0
    stato.fase_r = 0
    stato.fase_s = 0
    stato.fase_t = 0
    stato.carica_intervento = 0
    stato.save(
        update_fields=[
            "coerenza_accumulata",
            "fase_r",
            "fase_s",
            "fase_t",
            "carica_intervento",
            "updated_at",
        ]
    )


def tick_coerenza_scientifica(sessione) -> int:
    """Accumula coerenza e carica in base all'energia inviata a R/S/T; ritorna delta coerenza."""
    from .models import PilotRuntimeConfig, ScientificoStatoNave

    if sessione is None or not sessione.is_attiva:
        return 0
    cfg = PilotRuntimeConfig.get_solo()
    if not getattr(cfg, "scientifica_interventi_abilitati", True):
        return 0
    if not getattr(cfg, "scientifica_console_abilitata", False):
        return 0

    _, energia = _metriche_esotici_sessione(sessione)
    if energia < _soglia_energia_minima(cfg):
        return 0

    gain = _coerenza_da_energia(energia, cfg)
    stato = ScientificoStatoNave.get_solo()
    if stato.fase_r == 2 and stato.fase_s == 2 and stato.fase_t == 2:
        gain += 1

    cap = int(getattr(cfg, "scientifica_coerenza_cap", 24) or 24)
    before = int(stato.coerenza_accumulata or 0)
    stato.coerenza_accumulata = min(cap, before + gain)
    stato.carica_intervento = _carica_da_energia(energia, cfg, int(stato.carica_intervento or 0))
    stato.save(update_fields=["coerenza_accumulata", "carica_intervento", "updated_at"])
    return stato.coerenza_accumulata - before


@transaction.atomic
def imposta_fase_matrice(*, codice: str, fase: int) -> dict:
    from .models import PilotRuntimeConfig, ScientificoStatoNave

    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.scientifica_console_abilitata:
        raise ValueError("Console scientifica disabilitata.")
    if not getattr(cfg, "scientifica_interventi_abilitati", True):
        raise ValueError("Matrice R/S/T disabilitata in runtime.")

    codice = (codice or "").strip().upper()[:1]
    if codice not in {c for c, _ in ESOTICI}:
        raise ValueError("Codice nucleo non valido (R, S o T).")

    fase = _clamp_fase(fase)
    stato = ScientificoStatoNave.get_solo()
    field = {"R": "fase_r", "S": "fase_s", "T": "fase_t"}[codice]
    setattr(stato, field, fase)
    stato.save(update_fields=[field, "updated_at"])

    from .scientifica_spectro import build_scientifica_state_payload

    payload = build_scientifica_state_payload()
    payload["fase_impostata"] = {"codice": codice, "fase": fase}
    return payload


@transaction.atomic
def esegui_intervento_scientifico(*, tipo: str, componenti_scelti: list | None = None) -> dict:
    from .componenti_stiva import consuma_mattoni_stiva
    from .engine import applica_delta_defcon, evento_attivo_corrente
    from .models import EVENTO_ESITO_PENDING, PilotRuntimeConfig, ScientificoStatoNave
    from .views import _sessione_attiva_corrente

    tipo = (tipo or "").strip().lower()
    meta = INTERVENTI.get(tipo)
    if meta is None:
        raise ValueError("Tipo intervento non valido.")

    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.scientifica_console_abilitata:
        raise ValueError("Console scientifica disabilitata.")
    if not getattr(cfg, "scientifica_interventi_abilitati", True):
        raise ValueError("Interventi disabilitati in runtime.")

    sessione = _sessione_attiva_corrente()
    if sessione is None or not sessione.is_attiva:
        raise ValueError("Nessuna sessione di volo attiva.")

    istanza = None
    if tipo != "reset_risonanza":
        istanza = evento_attivo_corrente(sessione)
        if istanza is None or istanza.esito != EVENTO_ESITO_PENDING:
            raise ValueError("Nessun evento attivo per l'intervento.")

    catalogo = _interventi_catalogo(cfg, sessione, istanza)
    voce = next((c for c in catalogo if c["tipo"] == tipo), None)
    if voce is None or not voce["disponibile"]:
        raise ValueError(voce["motivo_indisponibile"] if voce else "Intervento non disponibile.")

    stato = ScientificoStatoNave.get_solo()
    costo = int(meta["coerenza"] or 0)
    if int(stato.coerenza_accumulata or 0) < costo:
        raise ValueError(f"Coerenza insufficiente (servono {costo}, disponibili {stato.coerenza_accumulata}).")

    n_comp = int(meta["componenti"] or 0)
    ok, err, alloc = _valida_consumo_componenti(
        cfg, componenti_scelti or [], tipo=tipo, n_richiesti=n_comp
    )
    if not ok:
        raise ValueError(err)

    if alloc:
        consuma_mattoni_stiva(alloc)

    stato.coerenza_accumulata = int(stato.coerenza_accumulata or 0) - costo
    carica_soglia = int(getattr(cfg, "scientifica_carica_intervento_soglia", 100) or 100)
    if meta.get("conta_limite_volo"):
        stato.carica_intervento = max(0, int(stato.carica_intervento or 0) - carica_soglia)
    stato.save(update_fields=["coerenza_accumulata", "carica_intervento", "updated_at"])

    effetto = {}
    update_evento_fields = []

    if tipo == "dilatazione":
        istanza.ticks_rimanenti = int(istanza.ticks_rimanenti or 0) + 1
        istanza.dilatazioni_applicate = int(istanza.dilatazioni_applicate or 0) + 1
        update_evento_fields = ["ticks_rimanenti", "dilatazioni_applicate"]
        effetto = {"ticks_rimanenti": istanza.ticks_rimanenti}
    elif tipo == "gabbia":
        istanza.ca_soppressa_scientifica = True
        update_evento_fields = ["ca_soppressa_scientifica"]
        effetto = {"ca_soppressa_armata": True}
    elif tipo == "correzione":
        defcon_pre = int(sessione.defcon or 0)
        applica_delta_defcon(sessione, -1)
        sessione.refresh_from_db()
        istanza.correzione_paradosso_applicata = True
        update_evento_fields = ["correzione_paradosso_applicata"]
        effetto = {"defcon_pre": defcon_pre, "defcon_post": int(sessione.defcon or 0)}
    elif tipo == "eco":
        istanza.eco_parziale_attiva = True
        update_evento_fields = ["eco_parziale_attiva"]
        effetto = {"eco_parziale_attiva": True}
    elif tipo == "reset_risonanza":
        stato.fase_r = 0
        stato.fase_s = 0
        stato.fase_t = 0
        stato.save(update_fields=["fase_r", "fase_s", "fase_t", "updated_at"])
        effetto = {"fasi_reset": True}

    if update_evento_fields and istanza is not None:
        update_evento_fields.append("updated_at")
        istanza.save(update_fields=update_evento_fields)

    if meta.get("conta_limite_volo"):
        sessione.interventi_scientifici_count = int(sessione.interventi_scientifici_count or 0) + 1
        sessione.save(update_fields=["interventi_scientifici_count", "updated_at"])

    try:
        from .flight_log import log_intervento_scientifico

        log_intervento_scientifico(sessione, istanza, tipo, effetto)
    except Exception:
        pass

    from .scientifica_spectro import build_scientifica_state_payload

    payload = build_scientifica_state_payload()
    payload["intervento_eseguito"] = {"tipo": tipo, "effetto": effetto}
    return payload
