"""
Utility keyword carte: pattern con placeholder [X], [Y], … nel nome e nei testi regola.
"""
from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"\[([A-Z]+)\]")
PARAM_VALUE_RE = r"(-?\d+|\S+)"


def keyword_ha_parametri(testo: str) -> bool:
    return bool(PLACEHOLDER_RE.search(testo or ""))


def placeholder_nomi(testo: str) -> list[str]:
    seen: list[str] = []
    for name in PLACEHOLDER_RE.findall(testo or ""):
        if name not in seen:
            seen.append(name)
    return seen


def _escape_literal_flexible_ws(literal: str) -> str:
    escaped = re.escape(literal)
    return escaped.replace(r"\ ", r"\s+")


def template_regex_body(template: str) -> tuple[str, list[str]]:
    """Corpo regex (senza ancoraggi) e nomi placeholder nell'ordine dei gruppi."""
    names: list[str] = []
    chunks: list[str] = []
    pos = 0
    for match in PLACEHOLDER_RE.finditer(template):
        literal = template[pos : match.start()]
        if literal:
            chunks.append(_escape_literal_flexible_ws(literal))
        name = match.group(1)
        names.append(name)
        chunks.append(PARAM_VALUE_RE)
        pos = match.end()
    if pos < len(template):
        chunks.append(re.escape(template[pos:]))
    return "".join(chunks), names


def match_keyword_parametrizzata(template: str, testo: str, start: int = 0) -> dict | None:
    """
    Prova un match case-insensitive da `start`.
    Ritorna dict con matched, params (nome placeholder → valore), length.
    """
    if not keyword_ha_parametri(template):
        return None
    body, names = template_regex_body(template)
    compiled = re.compile(rf"^{body}", re.IGNORECASE)
    m = compiled.match(testo[start:])
    if not m:
        return None
    params = {names[i]: m.group(i + 1) for i in range(len(names))}
    return {"matched": m.group(0), "params": params, "length": len(m.group(0))}


def substituisci_parametri_keyword(testo: str, params: dict[str, str]) -> str:
    if not testo or not params:
        return testo or ""

    def repl(match: re.Match) -> str:
        return str(params.get(match.group(1), match.group(0)))

    return PLACEHOLDER_RE.sub(repl, testo)


def risolvi_testi_keyword(kw: dict, params: dict[str, str]) -> dict:
    """Applica sostituzione a testo_regola e reminder_breve."""
    return {
        **kw,
        "testo_regola": substituisci_parametri_keyword(kw.get("testo_regola") or "", params),
        "reminder_breve": substituisci_parametri_keyword(kw.get("reminder_breve") or "", params),
        "params": params,
    }


def _kw_field(kw, name: str, default=None):
    if isinstance(kw, dict):
        return kw.get(name, default)
    return getattr(kw, name, default)


def _build_keyword_matchers(keywords) -> list[dict]:
    """Allinea priorità/ordine a parseCardRulesText.js (match più lungo prima)."""
    matchers: list[dict] = []
    seen_terms: set[str] = set()
    for kw in keywords or []:
        if _kw_field(kw, "attiva", True) is False:
            continue
        for raw in (_kw_field(kw, "nome"), _kw_field(kw, "codice")):
            term = (raw or "").strip()
            if not term:
                continue
            key = term.casefold()
            if key in seen_terms:
                continue
            seen_terms.add(key)
            if keyword_ha_parametri(term):
                matchers.append({
                    "kind": "template",
                    "template": term,
                    "kw": kw,
                    "sort_len": len(PLACEHOLDER_RE.sub("", term)) + 8,
                    "priorita": int(_kw_field(kw, "priorita") or 0),
                })
            else:
                matchers.append({
                    "kind": "exact",
                    "term": term,
                    "kw": kw,
                    "sort_len": len(term),
                    "priorita": int(_kw_field(kw, "priorita") or 0),
                })
    matchers.sort(key=lambda m: (-m["sort_len"], -m["priorita"]))
    return matchers


def iter_keyword_matches(testo: str, keywords) -> list[dict]:
    """Trova occorrenze keyword nel testo (ordine di lettura)."""
    if not testo:
        return []
    matchers = _build_keyword_matchers(keywords)
    if not matchers:
        return []

    hits: list[dict] = []
    i = 0
    while i < len(testo):
        found = None
        for entry in matchers:
            if entry["kind"] == "template":
                m = match_keyword_parametrizzata(entry["template"], testo, i)
                if m:
                    found = {
                        "kw": entry["kw"],
                        "matched": m["matched"],
                        "index": i,
                        "length": m["length"],
                        "params": m["params"],
                    }
                    break
            else:
                term = entry["term"]
                slice_ = testo[i : i + len(term)]
                if slice_.casefold() == term.casefold():
                    found = {
                        "kw": entry["kw"],
                        "matched": slice_,
                        "index": i,
                        "length": len(term),
                        "params": None,
                    }
                    break
        if found:
            hits.append(found)
            i += found["length"]
        else:
            i += 1
    return hits


def _keyword_effects_for_event_queryset(campagna):
    from personaggi.carte_collezionabili_models import KeywordCarta

    return list(
        KeywordCarta.objects.filter(campagna=campagna, attiva=True)
        .exclude(effect_script={})
        .order_by("-priorita", "nome")
    )


def find_all_keyword_effects_in_text(campagna, testo: str, event: str) -> list[dict]:
    """Tutte le keyword con effect_script per l'evento, in ordine di lettura nel testo."""
    keywords = _keyword_effects_for_event_queryset(campagna)
    out: list[dict] = []
    for hit in iter_keyword_matches(testo or "", keywords):
        kw = hit["kw"]
        script = kw.effect_script or {}
        if script.get("trigger", {}).get("event") != event:
            continue
        out.append(
            {
                "keyword": kw,
                "nome": kw.nome,
                "params": hit.get("params") or {},
                "effect_script": script,
                "index": hit.get("index", 0),
            }
        )
    return out


def find_keyword_effect_in_text(campagna, testo: str, event: str) -> dict | None:
    """Prima keyword con effect_script per l'evento richiesto trovata nel testo carta."""
    hits = find_all_keyword_effects_in_text(campagna, testo, event)
    return hits[0] if hits else None


def find_on_exhaust_keyword_in_text(campagna, testo: str) -> dict | None:
    """Prima keyword con effect_script on_exhaust trovata nel testo carta."""
    return find_keyword_effect_in_text(campagna, testo, "on_exhaust")
