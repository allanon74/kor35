"""
Valutazione requisiti JSON condivisi (manifesti, negozi mercante, sezioni condizionali, …).
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Tuple

# Operatori di confronto per requisiti numerici (statistica / aura / caratteristica).
# Default storico: `gte` (≥), così i JSON esistenti restano validi.
OP_GTE = "gte"
OP_GT = "gt"
OP_LTE = "lte"
OP_LT = "lt"
OP_EQ = "eq"
OP_ALIASES = {
    ">=": OP_GTE,
    "≥": OP_GTE,
    ">": OP_GT,
    "<=": OP_LTE,
    "≤": OP_LTE,
    "<": OP_LT,
    "==": OP_EQ,
    "=": OP_EQ,
}
OP_SYMBOLS = {
    OP_GTE: "≥",
    OP_GT: ">",
    OP_LTE: "≤",
    OP_LT: "<",
    OP_EQ: "=",
}


def normalizza_operatore(op: Any, default: str = OP_GTE) -> str:
    raw = (op or default or OP_GTE)
    if not isinstance(raw, str):
        return default
    key = raw.strip().lower()
    if key in OP_ALIASES:
        return OP_ALIASES[key]
    if key in OP_SYMBOLS:
        return key
    return default


def confronta_valore(cur: Any, soglia: Any, op: Any = OP_GTE) -> bool:
    """Confronto numerico sicuro; valori non numerici → False."""
    try:
        cur_n = float(cur)
        soglia_n = float(soglia)
    except (TypeError, ValueError):
        return False
    oper = normalizza_operatore(op)
    if oper == OP_GT:
        return cur_n > soglia_n
    if oper == OP_LT:
        return cur_n < soglia_n
    if oper == OP_LTE:
        return cur_n <= soglia_n
    if oper == OP_EQ:
        return cur_n == soglia_n
    return cur_n >= soglia_n


def simbolo_operatore(op: Any = OP_GTE) -> str:
    return OP_SYMBOLS.get(normalizza_operatore(op), "≥")


def _soglia_requisito(req: dict) -> int:
    if req.get("soglia") is not None:
        return int(req.get("soglia") or 0)
    return int(req.get("min", 1) or 1)


def personaggio_soddisfa_requisiti(
    personaggio,
    requisiti: Iterable[dict] | None,
    *,
    get_statistica: Callable[[str], Any] | None = None,
    get_aura=None,
    get_caratteristica: Callable[[str], Any] | None = None,
) -> Tuple[bool, str]:
    """Ritorna (ok, messaggio). Lista vuota / None = accesso libero."""
    from .models import (
        Abilita,
        Punteggio,
        AURA,
        CARATTERISTICA,
        Statistica,
        PersonaggioCarrieraMembership,
    )

    reqs = requisiti or []
    if not reqs:
        return True, ""

    def _val_stat(sigla: str):
        if get_statistica:
            return get_statistica(sigla)
        return personaggio.get_valore_statistica(sigla)

    def _val_aura(punteggio_obj):
        if get_aura:
            return get_aura(punteggio_obj)
        return personaggio.get_valore_aura_effettivo(punteggio_obj)

    def _val_caratt(nome: str):
        if get_caratteristica:
            return get_caratteristica(nome)
        return (personaggio.caratteristiche_base or {}).get(nome, 0)

    for req in reqs:
        if not isinstance(req, dict):
            continue
        tipo = (req.get("tipo") or "").strip().lower()
        if tipo == "statistica":
            sigla = (req.get("sigla") or "").strip().upper()
            soglia = _soglia_requisito(req)
            op = req.get("op")
            if not sigla:
                continue
            cur = _val_stat(sigla)
            if not confronta_valore(cur, soglia, op):
                st = Statistica.objects.filter(sigla=sigla).first()
                nome = st.nome if st else sigla
                return False, (
                    f"Richiesto {nome} ({sigla}) {simbolo_operatore(op)} {soglia} (hai {cur})."
                )
        elif tipo == "abilita":
            aid = req.get("id")
            if aid is None:
                continue
            if not personaggio.abilita_possedute.filter(pk=aid).exists():
                ab = Abilita.objects.filter(pk=aid).first()
                nome = ab.nome if ab else str(aid)
                return False, f"È richiesta l'abilità: {nome}."
        elif tipo == "punteggio":
            nome = (req.get("nome") or "").strip()
            sigla = (req.get("sigla") or "").strip().upper()
            soglia = _soglia_requisito(req)
            op = req.get("op")
            p = None
            if sigla:
                p = Punteggio.objects.filter(sigla=sigla, tipo=AURA).first()
            if not p and nome:
                p = Punteggio.objects.filter(nome=nome, tipo=AURA).first()
            if not p:
                label = nome or sigla or "?"
                return False, f"Requisito aura sconosciuto: {label}."
            cur = _val_aura(p)
            if not confronta_valore(cur, soglia, op):
                return False, (
                    f"Richiesta aura {p.nome} {simbolo_operatore(op)} {soglia} (hai {cur})."
                )
        elif tipo == "caratteristica":
            nome = (req.get("nome") or "").strip()
            sigla = (req.get("sigla") or "").strip().upper()
            soglia = _soglia_requisito(req)
            op = req.get("op")
            p = None
            if sigla:
                p = Punteggio.objects.filter(sigla=sigla, tipo=CARATTERISTICA).first()
            if not p and nome:
                p = Punteggio.objects.filter(nome=nome, tipo=CARATTERISTICA).first()
            if not p:
                label = nome or sigla or "?"
                return False, f"Requisito caratteristica sconosciuto: {label}."
            cur = _val_caratt(p.nome)
            if not confronta_valore(cur, soglia, op):
                return False, (
                    f"Richiesta {p.nome} {simbolo_operatore(op)} {soglia} (hai {cur})."
                )
        elif tipo == "korp":
            kid = req.get("id")
            if kid is None:
                continue
            attiva = PersonaggioCarrieraMembership.objects.filter(
                personaggio=personaggio,
                data_a__isnull=True,
                tipo_carriera__codice="korp",
                carriera_id=kid,
            ).exists()
            if not attiva:
                return False, "Richiesta appartenenza a una KORP specifica."
        elif tipo == "carriera":
            cid = req.get("id")
            if cid is None:
                continue
            attiva = PersonaggioCarrieraMembership.objects.filter(
                personaggio=personaggio,
                data_a__isnull=True,
                carriera_id=cid,
            ).exists()
            if not attiva:
                return False, "Richiesta appartenenza a una carriera specifica."
        elif tipo == "carica":
            cid = req.get("id")
            if cid is None:
                continue
            attiva = PersonaggioCarrieraMembership.objects.filter(
                personaggio=personaggio,
                data_a__isnull=True,
                carica_id=cid,
            ).exists()
            if not attiva:
                return False, "Richiesta una carica specifica."
    return True, ""


def personaggio_soddisfa_requisiti_gruppo(
    personaggio,
    regole: dict | None,
    **kwargs,
) -> Tuple[bool, str]:
    """
    regole: {"operator": "OR"|"AND", "requisiti": [...]}
    Default AND se operator assente.
    kwargs inoltrati a personaggio_soddisfa_requisiti (get_statistica, …).
    """
    if not regole:
        return True, ""
    reqs = regole.get("requisiti") or []
    if not reqs:
        return True, ""
    op = (regole.get("operator") or "AND").strip().upper()
    if op == "OR":
        for req in reqs:
            ok, _ = personaggio_soddisfa_requisiti(personaggio, [req], **kwargs)
            if ok:
                return True, ""
        return False, "Non soddisfi i requisiti di accesso (nessuna condizione alternativa)."
    messages = []
    for req in reqs:
        ok, msg = personaggio_soddisfa_requisiti(personaggio, [req], **kwargs)
        if not ok:
            messages.append(msg)
    if messages:
        return False, messages[0]
    return True, ""


def gruppo_requisiti_soddisfatto(personaggio, gruppo: dict | None, **kwargs) -> bool:
    """True se il gruppo {operator, requisiti} è soddisfatto."""
    ok, _ = personaggio_soddisfa_requisiti_gruppo(personaggio, gruppo, **kwargs)
    return ok
