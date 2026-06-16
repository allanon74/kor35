"""
Valutazione requisiti JSON condivisi (manifesti, negozi mercante, …).
"""
from __future__ import annotations

from typing import Any, Iterable, Tuple


def personaggio_soddisfa_requisiti(personaggio, requisiti: Iterable[dict] | None) -> Tuple[bool, str]:
    """Ritorna (ok, messaggio). Lista vuota / None = accesso libero."""
    from .models import Abilita, Punteggio, AURA, Statistica, PersonaggioCarrieraMembership

    reqs = requisiti or []
    if not reqs:
        return True, ""

    for req in reqs:
        if not isinstance(req, dict):
            continue
        tipo = (req.get("tipo") or "").strip().lower()
        if tipo == "statistica":
            sigla = (req.get("sigla") or "").strip().upper()
            min_v = int(req.get("min", 1) or 1)
            if not sigla:
                continue
            cur = personaggio.get_valore_statistica(sigla)
            if cur < min_v:
                st = Statistica.objects.filter(sigla=sigla).first()
                nome = st.nome if st else sigla
                return False, f"Richiesto {nome} ({sigla}) ≥ {min_v} (hai {cur})."
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
            min_v = int(req.get("min", 1) or 1)
            if not nome:
                continue
            p = Punteggio.objects.filter(nome=nome, tipo=AURA).first()
            if not p:
                return False, f"Requisito aura sconosciuto: {nome}."
            cur = personaggio.get_valore_aura_effettivo(p)
            if cur < min_v:
                return False, f"Richiesta aura {nome} ≥ {min_v} (hai {cur})."
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


def personaggio_soddisfa_requisiti_gruppo(personaggio, regole: dict | None) -> Tuple[bool, str]:
    """
    regole: {"operator": "OR"|"AND", "requisiti": [...]}
    Default AND se operator assente.
    """
    if not regole:
        return True, ""
    reqs = regole.get("requisiti") or []
    if not reqs:
        return True, ""
    op = (regole.get("operator") or "AND").strip().upper()
    if op == "OR":
        for req in reqs:
            ok, _ = personaggio_soddisfa_requisiti(personaggio, [req])
            if ok:
                return True, ""
        return False, "Non soddisfi i requisiti di accesso (nessuna condizione alternativa)."
    messages = []
    for req in reqs:
        ok, msg = personaggio_soddisfa_requisiti(personaggio, [req])
        if not ok:
            messages.append(msg)
    if messages:
        return False, messages[0]
    return True, ""


def gruppo_requisiti_soddisfatto(personaggio, gruppo: dict | None) -> bool:
    """True se il gruppo {operator, requisiti} è soddisfatto."""
    ok, _ = personaggio_soddisfa_requisiti_gruppo(personaggio, gruppo)
    return ok
