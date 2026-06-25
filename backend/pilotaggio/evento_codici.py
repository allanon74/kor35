"""
Generazione codici evento (esatta / parziale / precipizio) dallo stato sottosistemi.

Usato dallo staff per allineare i pattern legacy ai livelli correnti della nave
o della sessione attiva, in coerenza con le condizioni ST/SP/CA in regole_json.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from django.db import transaction

from .engine import codice_valido_3char, normalizza_codice
from .models import ComandoNave, EventoNave, SottosistemaNave, StatoSottosistemaNave


def _default_comando_char() -> str:
    codice = (
        ComandoNave.objects.filter(attivo=True)
        .order_by("codice")
        .values_list("codice", flat=True)
        .first()
    )
    return (codice or "L").upper()[:1]


def _livello_da_stato(stato) -> int:
    if stato is None:
        return 0
    if getattr(stato, "espulso", False):
        return 0
    if not getattr(stato, "online", True):
        return 0
    return max(0, min(9, int(getattr(stato, "livello_attuale", 0) or 0)))


def _codice_esatto(ss: str, cmd: str, livello: int) -> str:
    return f"{ss.upper()}{cmd.upper()}{livello}"


def _pattern_range(ss: str, cmd: str, lo: int, hi: int) -> str:
    lo = max(0, min(9, int(lo)))
    hi = max(0, min(9, int(hi)))
    if lo > hi:
        lo, hi = hi, lo
    return f"{ss.upper()}{cmd.upper()}({lo}-{hi})"


def _conditions_from_regole(regole: dict, key: str) -> List[dict]:
    section = (regole or {}).get(key) or {}
    raw = section.get("_conditions") or []
    return [c for c in raw if isinstance(c, dict)]


def _sottosistema_primario(evento: EventoNave, regole: dict) -> str:
    for key in ("st", "sp", "ca"):
        for cond in _conditions_from_regole(regole, key):
            ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
            if ss:
                return ss
    if evento.sottosistema_id:
        ss = SottosistemaNave.objects.filter(pk=evento.sottosistema_id).values_list(
            "codice", flat=True
        ).first()
        if ss:
            return str(ss).upper()[:1]
    return "A"


def _patterns_da_condizione(
    cond: dict,
    cmd: str,
    stati_by_key: dict,
    *,
    modalita: str,
) -> List[str]:
    """modalita: parziale | catastrofe"""
    ss = str(cond.get("sottosistema") or "").strip().upper()[:1]
    if not ss:
        return []
    stato = stati_by_key.get(ss)
    cur = _livello_da_stato(stato)
    op = str(cond.get("op") or "=").strip().lower()

    if modalita == "catastrofe":
        if op in {"espulso", "distrutte"} or not getattr(stato, "online", True):
            return [_codice_esatto(ss, cmd, 9), _pattern_range(ss, cmd, 8, 9)]
        if op in {">", "gt", ">=", "gte"}:
            thr = int(cond.get("value", 0))
            return [_pattern_range(ss, cmd, 0, max(0, thr))]
        if op in {"<", "lt", "<=", "lte"}:
            thr = int(cond.get("value", 9))
            return [_pattern_range(ss, cmd, min(9, thr + 1), 9)]
        if op == "between":
            lo = int(cond.get("min", 0))
            return [_pattern_range(ss, cmd, 0, max(0, lo - 1)), _pattern_range(ss, cmd, 9, 9)]
        return [_pattern_range(ss, cmd, max(0, cur + 1), 9), f"{ss}{cmd}_"]

    # parziale
    if op in {"=", "eq"}:
        v = int(cond.get("value", cur))
        return [f"{ss}{cmd}_", _pattern_range(ss, cmd, max(0, v - 1), min(9, v + 1))]
    if op in {">", "gt"}:
        v = int(cond.get("value", 0))
        return [_pattern_range(ss, cmd, v + 1, 9), f"{ss}{cmd}_"]
    if op in {"<", "lt"}:
        v = int(cond.get("value", 9))
        return [_pattern_range(ss, cmd, 0, max(0, v - 1))]
    if op == "between":
        lo = int(cond.get("min", 0))
        hi = int(cond.get("max", 9))
        return [_pattern_range(ss, cmd, lo, hi)]
    if op in {"piene", "non_vuote"}:
        return [_pattern_range(ss, cmd, 7, 9)]
    if op in {"vuote", "non_piene"}:
        return [_pattern_range(ss, cmd, 0, 2)]
    return [f"{ss}{cmd}_"]


def genera_codici_evento_da_stato(
    evento: EventoNave,
    stati_by_key: dict,
    *,
    comando: Optional[str] = None,
) -> Dict[str, Any]:
    cmd = (comando or _default_comando_char()).upper()[:1]
    regole = evento.regole_json or {}
    ss = _sottosistema_primario(evento, regole)
    stato_pri = stati_by_key.get(ss)
    livello = _livello_da_stato(stato_pri)

    esatta = _codice_esatto(ss, cmd, livello)
    if not codice_valido_3char(esatta):
        esatta = "A00"

    parziali: List[str] = []
    for cond in _conditions_from_regole(regole, "sp"):
        parziali.extend(_patterns_da_condizione(cond, cmd, stati_by_key, modalita="parziale"))
    if not parziali:
        parziali = [f"{ss}{cmd}_", _pattern_range(ss, cmd, max(0, livello - 1), min(9, livello + 1))]

    precipizi: List[str] = []
    for cond in _conditions_from_regole(regole, "ca"):
        precipizi.extend(_patterns_da_condizione(cond, cmd, stati_by_key, modalita="catastrofe"))
    if not precipizi:
        precipizi = [_pattern_range(ss, cmd, 8, 9), f"{ss}{cmd}9"]

    def _uniq(seq):
        out = []
        seen = set()
        for item in seq:
            p = normalizza_codice(str(item))
            if not p or p in seen:
                continue
            seen.add(p)
            out.append(p)
        return out

    return {
        "codice_soluzione_esatta": esatta,
        "codici_soluzione_parziale": _uniq(parziali),
        "codici_precipizio": _uniq(precipizi),
        "sottosistema_riferimento": ss,
        "livello_riferimento": livello,
        "comando_riferimento": cmd,
    }


def build_stati_by_key_da_sessione_o_nave(sessione=None) -> Dict[str, Any]:
    """Mappa codice sottosistema → stato runtime (sessione se presente, altrimenti nave)."""
    from .stato_nave import stato_operativo_sottosistema

    stati_by_key: Dict[str, Any] = {}
    for sdef in SottosistemaNave.objects.filter(attivo=True).only("pk", "codice", "nome"):
        cod = (sdef.codice or "").strip().upper()
        if not cod:
            continue
        stato = stato_operativo_sottosistema(sdef, sessione)
        stati_by_key[cod] = stato
        nome = (sdef.nome or "").strip().upper()
        if nome:
            stati_by_key[nome] = stato
    return stati_by_key


@transaction.atomic
def aggiorna_codici_eventi_da_stato(
    *,
    evento_id: Optional[str] = None,
    solo_attivi: bool = True,
    sessione=None,
    comando: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Aggiorna codice_soluzione_esatta, codici_soluzione_parziale, codici_precipizio
    per uno o tutti gli eventi, in base allo stato corrente sottosistemi.
    """
    from .views import _sessione_attiva_corrente

    if sessione is None:
        sessione = _sessione_attiva_corrente()

    stati_by_key = build_stati_by_key_da_sessione_o_nave(sessione)
    qs = EventoNave.objects.all().order_by("nome")
    if solo_attivi:
        qs = qs.filter(attivo=True)
    if evento_id:
        qs = qs.filter(pk=evento_id)

    aggiornati = []
    for evento in qs:
        payload = genera_codici_evento_da_stato(evento, stati_by_key, comando=comando)
        if not dry_run:
            evento.codice_soluzione_esatta = payload["codice_soluzione_esatta"]
            evento.codici_soluzione_parziale = payload["codici_soluzione_parziale"]
            evento.codici_precipizio = payload["codici_precipizio"]
            evento.save(
                update_fields=[
                    "codice_soluzione_esatta",
                    "codici_soluzione_parziale",
                    "codici_precipizio",
                    "updated_at",
                ]
            )
        aggiornati.append(
            {
                "evento_id": str(evento.pk),
                "nome": evento.nome,
                **payload,
            }
        )

    fonte = "sessione" if sessione is not None else "nave_persistente"
    if sessione is not None:
        from .stato_nave import fase_operativa_sessione

        fonte = f"sessione_{fase_operativa_sessione(sessione)}"

    return {
        "fonte_stato": fonte,
        "sessione_id": str(sessione.pk) if sessione else None,
        "dry_run": dry_run,
        "aggiornati": aggiornati,
        "conteggio": len(aggiornati),
    }
