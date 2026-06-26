"""
Genera HTML catalogo eventi pilotaggio per la pagina Wiki staff-pilot-eventi.
"""

from __future__ import annotations

import html
from typing import Any

BOOL_OPS = frozenset(
    {
        "piene",
        "vuote",
        "non_piene",
        "non_vuote",
        "distrutte",
        "invertito",
        "non_invertito",
        "espulso",
        "non_espulso",
    }
)


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _build_ss_maps():
    from pilotaggio.models import SottosistemaNave

    rows = list(SottosistemaNave.objects.order_by("codice", "nome"))
    ss_by_id = {str(s.id): s for s in rows}
    ss_by_codice = {
        (s.codice or "").strip().upper(): s for s in rows if (s.codice or "").strip()
    }
    return ss_by_id, ss_by_codice


def _codice_char_label(codice: str, ss_by_codice: dict) -> str:
    """Es. E → Deflettori (E)."""
    code = (codice or "?").strip().upper()
    row = ss_by_codice.get(code)
    if row and (row.nome or "").strip():
        return f"{row.nome.strip()} ({code})"
    return code


def _format_condition(c: dict, ss_by_codice: dict) -> str:
    sub_code = (c.get("sottosistema") or c.get("subsystem") or "?").strip().upper()
    sub_label = _codice_char_label(sub_code, ss_by_codice)
    op = str(c.get("op") or "").strip().lower()
    if op == "between":
        return f"{sub_label} tra {c.get('min', '?')} e {c.get('max', '?')}"
    if op == "direction":
        rule = c.get("direction_rule") or "?"
        return f"{sub_label} direction={rule}"
    if op in BOOL_OPS:
        return f"{sub_label} {op.replace('_', ' ')}"
    if op:
        return f"{sub_label} {op} {c.get('value', '')}"
    return sub_label


def _format_outcome_branch(regole: dict, key: str, ss_by_codice: dict) -> str:
    section = (regole or {}).get(key) or {}
    conditions = section.get("_conditions") or []
    if not isinstance(conditions, list) or not conditions:
        return "<em>Nessuna condizione</em>"
    items = "".join(
        f"<li>{idx}) {_esc(_format_condition(c, ss_by_codice))}</li>"
        for idx, c in enumerate(conditions, start=1)
        if isinstance(c, dict)
    )
    expr = str(section.get("_expr") or "").strip()
    expr_html = f'<p class="wiki-pilot-expr">Formula: <code>{_esc(expr)}</code></p>' if expr else ""
    return f"<ul>{items}</ul>{expr_html}"


def _resolve_sottosistema_label(sid: str, ss_by_id: dict) -> str:
    row = ss_by_id.get(str(sid).strip())
    if not row:
        return _esc(sid[:8] + "…" if len(str(sid)) > 8 else sid)
    codice = (row.codice or "").strip().upper()
    nome = (row.nome or "").strip()
    return _esc(f"{nome} ({codice})" if nome else codice)


def _format_ca_effetto(regole: dict, ss_by_id: dict, ss_by_codice: dict) -> str:
    cae = (regole or {}).get("ca_effetto") if isinstance(regole, dict) else None
    if not isinstance(cae, dict):
        return "Precipizio nave (default)"
    tipo = str(cae.get("tipo") or "precipizio").strip().lower()
    if tipo == "precipizio":
        return "Precipizio nave"
    if tipo == "guasto_sottosistema":
        codice = str(cae.get("sottosistema_codice") or "").strip().upper()
        sid = cae.get("sottosistema_id")
        if sid:
            return f"Guasto su {_resolve_sottosistema_label(sid, ss_by_id)}"
        if codice:
            return f"Guasto su {_esc(_codice_char_label(codice, ss_by_codice))}"
        return "Guasto su sottosistema (target non specificato)"
    if tipo == "guasto_sottosistemi":
        ids: list[str] = []
        if isinstance(cae.get("sottosistema_ids"), list):
            ids = [str(x) for x in cae["sottosistema_ids"]]
        elif isinstance(cae.get("sottosistemi_ids"), list):
            ids = [str(x) for x in cae["sottosistemi_ids"]]
        elif cae.get("sottosistema_id"):
            ids = [str(cae["sottosistema_id"])]
        modalita = str(cae.get("modalita") or "tutti").strip().lower()
        if modalita == "random":
            qty = max(1, int(cae.get("quantita") or 1))
            if ids:
                labels = ", ".join(_resolve_sottosistema_label(i, ss_by_id) for i in ids)
                return f"Guasto random ×{qty} da: {labels}"
            return f"Guasto random ×{qty} tra sottosistemi online in sessione"
        if ids:
            labels = ", ".join(_resolve_sottosistema_label(i, ss_by_id) for i in ids)
            return f"Guasto su tutti: {labels}"
        return "Guasto sottosistemi (elenco vuoto)"
    return _esc(f"Tipo CA: {tipo}")


def _format_legacy_codice(codice: str, ss_by_codice: dict) -> str:
    """Espande il primo carattere del codice 3-char con il nome sottosistema."""
    raw = str(codice or "").strip().upper()
    if not raw or raw == "—":
        return "—"
    first = raw[0]
    if len(raw) == 1:
        return _esc(_codice_char_label(first, ss_by_codice))
    rest = raw[1:]
    return f"<code>{_esc(raw)}</code> <span class=\"wiki-pilot-cod-hint\">({_esc(_codice_char_label(first, ss_by_codice))}…)</span>"


def _format_json_list(value: Any, ss_by_codice: dict) -> str:
    if not value:
        return "—"
    if isinstance(value, list):
        if not value:
            return "—"
        return ", ".join(_format_legacy_codice(v, ss_by_codice) for v in value)
    return _format_legacy_codice(str(value), ss_by_codice)


def _build_sottosistemi_legend_html(ss_by_codice: dict) -> str:
    if not ss_by_codice:
        return ""
    rows = "".join(
        f"<tr><td><code>{_esc(code)}</code></td><td>{_esc((row.nome or '').strip() or '—')}</td></tr>"
        for code, row in sorted(ss_by_codice.items())
    )
    return (
        '<h3>Legenda sottosistemi (1° carattere codice)</h3>'
        '<div class="wiki-table-scroll"><table data-table-style="grid">'
        "<thead><tr><th>Cod.</th><th>Sistema</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def build_pilot_eventi_catalog_html() -> str:
    """Elenco HTML eventi dal DB (append alla pagina wiki staff)."""
    from pilotaggio.models import EventoNave

    ss_by_id, ss_by_codice = _build_ss_maps()
    eventi = list(EventoNave.objects.select_related("sottosistema").order_by("nome"))

    parts = [
        "<hr>",
        "<h2>Catalogo eventi (database locale)</h2>",
        "<p><em>Generato automaticamente a ogni "
        "<code>make wiki-staff-sync</code> / deploy. "
        "Modifica gli eventi in Dashboard staff → Pilotaggio → Eventi.</em></p>",
    ]
    legend = _build_sottosistemi_legend_html(ss_by_codice)
    if legend:
        parts.append(legend)

    if not eventi:
        parts.append("<p><em>Nessun evento configurato.</em></p>")
        return "\n".join(parts)

    rows = []
    for ev in eventi:
        regole = ev.regole_json if isinstance(ev.regole_json, dict) else {}
        ss_label = "—"
        if ev.sottosistema_id:
            ss_label = _resolve_sottosistema_label(ev.sottosistema_id, ss_by_id)
        durata = _esc(ev.durata_tick or "—")
        crit = "sì" if ev.scadenza_critica else "no"
        attivo = "sì" if ev.attivo else "no"
        codice = _format_legacy_codice(ev.codice_soluzione_esatta or "", ss_by_codice)
        parziali = _format_json_list(ev.codici_soluzione_parziale, ss_by_codice)
        precipizio = _format_json_list(ev.codici_precipizio, ss_by_codice)
        ca_html = _format_ca_effetto(regole, ss_by_id, ss_by_codice)
        st_html = _format_outcome_branch(regole, "st", ss_by_codice)
        sp_html = _format_outcome_branch(regole, "sp", ss_by_codice)
        ca_cond_html = _format_outcome_branch(regole, "ca", ss_by_codice)
        desc = _esc((ev.descrizione or "").strip()[:280])
        if ev.descrizione and len(ev.descrizione.strip()) > 280:
            desc += "…"

        rows.append(
            f"""
<details class="wiki-pilot-evento">
<summary><strong>{_esc(ev.nome)}</strong> — durata {_esc(durata)} tick, scadenza CA {crit}, attivo {attivo}</summary>
<div class="wiki-pilot-evento-body">
<p>{desc}</p>
<table data-table-style="grid">
<thead><tr><th>Campo</th><th>Valore</th></tr></thead>
<tbody>
<tr><td>Sottosistema collegato</td><td>{ss_label}</td></tr>
<tr><td>Codice legacy ST</td><td>{codice}</td></tr>
<tr><td>Codici parziali (SP)</td><td>{parziali}</td></tr>
<tr><td>Codici precipizio</td><td>{precipizio}</td></tr>
<tr><td>Peso random</td><td>{_esc(ev.peso_random)}</td></tr>
</tbody>
</table>
<h4>Condizioni ST</h4>
{st_html}
<h4>Condizioni SP</h4>
{sp_html}
<h4>Condizioni CA (valutazione)</h4>
{ca_cond_html}
<h4>Effetto Catastrofe (ca_effetto)</h4>
<p>{ca_html}</p>
</div>
</details>
""".strip()
        )

    parts.append("\n".join(rows))
    return "\n".join(parts)
