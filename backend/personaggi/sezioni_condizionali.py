"""
Sezioni condizionali di Infusione/Oggetto/Tessitura: testo extra + statistiche
visibili/attive solo se il personaggio soddisfa un gruppo di requisiti
oppure, sulle tessiture, se il giocatore attiva un flag facoltativo.
"""
from __future__ import annotations

from itertools import combinations
from typing import Iterable, List, Optional

from django.utils.text import slugify

from .requisiti_accesso import (
    gruppo_requisiti_soddisfatto,
    simbolo_operatore,
)

SEZIONE_MODALITA_AUTO = "auto"
SEZIONE_MODALITA_MANUALE = "manuale"
BERSAGLIO_PARAMS = frozenset({"flusso", "dardo", "tocco", "cono", "tutti", "esplos"})
MAX_MANUAL_COMBINAZIONI = 3


class _ParamOnly:
    """Statistica fittizia per azzerare un parametro bersaglio in formula."""

    __slots__ = ("parametro", "pk")

    def __init__(self, parametro):
        self.parametro = parametro
        self.pk = f"__param__{parametro}"


class _MergedStatBase:
    """Adattatore minimale per formatta_testo_generico (statistica + valore_base)."""

    __slots__ = ("statistica", "valore_base", "statistica_id")

    def __init__(self, statistica, valore_base):
        self.statistica = statistica
        self.valore_base = valore_base
        self.statistica_id = getattr(statistica, "pk", None)


def prefetch_sezioni_related(qs, *, with_modificatori=True):
    related = ["statistiche_base__statistica"]
    if with_modificatori:
        related.append("modificatori__statistica")
    return qs.prefetch_related(*related)


def sezioni_queryset(item):
    from .models import Infusione, Oggetto, Tessitura

    manager = getattr(item, "sezioni_condizionali", None)
    if manager is None:
        return None
    qs = manager.order_by("ordine", "created_at")
    if isinstance(item, Tessitura):
        return prefetch_sezioni_related(qs, with_modificatori=False)
    if isinstance(item, (Infusione, Oggetto)):
        return prefetch_sezioni_related(qs)
    return qs


def etichetta_condizioni(condizioni: dict | None) -> str:
    """Etichetta breve per anteprima staff (es. «Aura Magica > 2»)."""
    regole = condizioni if isinstance(condizioni, dict) else {}
    reqs = regole.get("requisiti") or []
    if not reqs:
        return "Sempre attiva"
    parti = []
    for req in reqs:
        if not isinstance(req, dict):
            continue
        tipo = (req.get("tipo") or "").strip().lower()
        op_sym = simbolo_operatore(req.get("op"))
        soglia = req.get("soglia", req.get("min", ""))
        if tipo == "punteggio":
            nome = req.get("nome") or req.get("sigla") or "Aura"
            parti.append(f"{nome} {op_sym} {soglia}")
        elif tipo == "caratteristica":
            nome = req.get("nome") or req.get("sigla") or "Caratteristica"
            parti.append(f"{nome} {op_sym} {soglia}")
        elif tipo == "statistica":
            sigla = req.get("sigla") or "Stat"
            parti.append(f"{sigla} {op_sym} {soglia}")
        elif tipo == "abilita":
            parti.append("abilità richiesta")
        else:
            parti.append(tipo or "condizione")
    if not parti:
        return "Sempre attiva"
    joiner = " e " if (regole.get("operator") or "AND").upper() != "OR" else " o "
    return joiner.join(parti)


def sezione_is_manuale(sezione) -> bool:
    mode = (getattr(sezione, "modalita", None) or SEZIONE_MODALITA_AUTO).strip().lower()
    return mode == SEZIONE_MODALITA_MANUALE


def flag_id_sezione(sezione) -> str:
    etichetta = (getattr(sezione, "etichetta", None) or "").strip()
    slug = slugify(etichetta).replace("-", "_")
    if slug:
        return slug
    return f"azione_{getattr(sezione, 'ordine', 0)}"


def etichetta_sezione(sezione) -> str:
    if sezione_is_manuale(sezione):
        lab = (getattr(sezione, "etichetta", None) or "").strip()
        auto = etichetta_condizioni(getattr(sezione, "condizioni", None))
        if lab and auto != "Sempre attiva":
            return f"{lab} ({auto})"
        return lab or auto
    return etichetta_condizioni(getattr(sezione, "condizioni", None))


def etichetta_combinazione(sezioni: Iterable) -> str:
    parti = []
    for sezione in sezioni:
        lab = (getattr(sezione, "etichetta", None) or "").strip()
        if not lab:
            lab = etichetta_sezione(sezione)
        parti.append(lab)
    if not parti:
        return "Se condizione"
    if len(parti) == 1:
        return f"Se {parti[0]}"
    return "Se " + ", ".join(parti[:-1]) + f" e {parti[-1]}"


def flag_context(sezioni: Iterable) -> dict:
    ctx = {}
    for sezione in sezioni or []:
        fid = flag_id_sezione(sezione)
        if fid:
            ctx[fid] = 1
    return ctx


def contesto_formula_tessitura(item, **extra):
    from .models import FORMULA_SCOPE_WEAVE

    ctx = {
        "livello": getattr(item, "livello", 0),
        "aura": getattr(item, "aura_richiesta", None),
        "elemento": extra.pop("elemento", getattr(item, "elemento_principale", None)),
        "formula_kind": FORMULA_SCOPE_WEAVE,
        "allow_implicit_formula_source": False,
        "formula_builder_selezioni": getattr(item, "formula_builder_selezioni", None) or {},
        "attack_formula_template": getattr(item, "formula", None),
    }
    ctx.update(extra)
    return ctx


def sezione_attiva(sezione, personaggio, **eval_kwargs) -> bool:
    if personaggio is None:
        return True
    return gruppo_requisiti_soddisfatto(
        personaggio,
        getattr(sezione, "condizioni", None) or {},
        **eval_kwargs,
    )


def sezioni_attive(item, personaggio, **eval_kwargs) -> List:
    qs = sezioni_queryset(item)
    if qs is None:
        return []
    return [
        s
        for s in qs
        if not sezione_is_manuale(s) and sezione_attiva(s, personaggio, **eval_kwargs)
    ]


def sezioni_auto_attive(item, personaggio, **eval_kwargs) -> List:
    """Sezioni automatiche da mescolare nella formula principale (solo con personaggio)."""
    if personaggio is None:
        return []
    return sezioni_attive(item, personaggio, **eval_kwargs)


def sezioni_manuali_disponibili(item, personaggio, **eval_kwargs) -> List:
    qs = sezioni_queryset(item)
    if qs is None:
        return []
    out = []
    for sezione in qs:
        if not sezione_is_manuale(sezione):
            continue
        if personaggio is None or sezione_attiva(sezione, personaggio, **eval_kwargs):
            out.append(sezione)
    return out


def merge_statistiche_base(base_rows: Iterable, sezioni: Iterable) -> List[_MergedStatBase]:
    """Unisci statistiche_base dell'item con quelle delle sezioni attive (somma sullo stesso parametro)."""
    merged = {}
    order = []

    def _acc(statistica, valore_base):
        if statistica is None:
            return
        sid = getattr(statistica, "pk", None)
        if sid is None:
            return
        try:
            val = int(valore_base or 0)
        except (TypeError, ValueError):
            val = 0
        if sid in merged:
            merged[sid].valore_base += val
        else:
            merged[sid] = _MergedStatBase(statistica, val)
            order.append(sid)

    for item in base_rows or []:
        _acc(getattr(item, "statistica", None), getattr(item, "valore_base", 0))
    for sezione in sezioni or []:
        rows = getattr(sezione, "statistiche_base", None)
        if rows is None:
            continue
        for row in rows.all() if hasattr(rows, "all") else rows:
            _acc(getattr(row, "statistica", None), getattr(row, "valore_base", 0))
    return [merged[sid] for sid in order]


def merge_statistiche_tessitura_sezioni(base_rows: Iterable, sezioni: Iterable) -> List[_MergedStatBase]:
    sostituisci = [s for s in (sezioni or []) if getattr(s, "sostituisci_bersaglio", False)]
    if not sostituisci:
        return merge_statistiche_base(base_rows, sezioni)
    merged = merge_statistiche_base(base_rows, [])
    by_param = {}
    for row in merged:
        param = getattr(row.statistica, "parametro", None)
        if param:
            by_param[param] = row
    for param in BERSAGLIO_PARAMS:
        if param in by_param:
            by_param[param].valore_base = 0
        else:
            row = _MergedStatBase(_ParamOnly(param), 0)
            merged.append(row)
            by_param[param] = row
    return merge_statistiche_base(merged, sezioni)


def iter_modificatori_sezioni(sezioni: Iterable, *, solo_oggetto_ospitante: Optional[bool] = None):
    for sezione in sezioni or []:
        mods = getattr(sezione, "modificatori", None)
        if mods is None:
            continue
        iterable = mods.all() if hasattr(mods, "all") else mods
        for mod in iterable:
            flag = bool(getattr(mod, "solo_oggetto_ospitante", False))
            if solo_oggetto_ospitante is None or flag is solo_oggetto_ospitante:
                yield mod


def html_sezioni_append(item, personaggio, *, context=None, formula=None, statistiche_base=None) -> str:
    """HTML delle sezioni attive (testo formattato) da accodare al testo base."""
    from .models import Tessitura, formatta_testo_generico

    sezioni = sezioni_attive(item, personaggio)
    if not sezioni:
        return ""
    is_tessitura = isinstance(item, Tessitura)
    parts = []
    for sezione in sezioni:
        testo = (sezione.testo or "").strip()
        formatted = ""
        if testo:
            formatted = formatta_testo_generico(
                testo,
                formula=None,
                statistiche_base=statistiche_base,
                personaggio=personaggio,
                context=context,
            )
        formula_bit = ""
        if is_tessitura and formula and personaggio is None:
            stats_var = merge_statistiche_tessitura_sezioni(statistiche_base, [sezione])
            ctx_var = dict(context or {})
            ctx_var.update(flag_context([sezione]))
            formula_bit = formatta_testo_generico(
                None,
                formula=formula,
                statistiche_base=stats_var,
                personaggio=None,
                context=ctx_var,
                solo_formula=True,
            )
        if not formatted and not formula_bit:
            continue
        inner = f"{formatted}{formula_bit}"
        label = etichetta_sezione(sezione)
        if personaggio is None:
            parts.append(
                f"<div class='sezione-condizionale' style='margin-top:8px;padding:6px 8px;"
                f"border-left:3px solid #6366f1;background:rgba(99,102,241,0.08);'>"
                f"<div style='font-size:0.75em;text-transform:uppercase;letter-spacing:.08em;"
                f"color:#a5b4fc;margin-bottom:4px;'>Se {label}</div>{inner}</div>"
            )
        else:
            parts.append(f"<div class='sezione-condizionale' style='margin-top:8px;'>{inner}</div>")
    return "".join(parts)


def html_varianti_manuali_tessitura(item, personaggio, *, context=None, formula=None, statistiche_base=None) -> str:
    """Formule extra per le condizioni facoltative (flag giocatore) e loro combinazioni."""
    from .models import formatta_testo_generico

    manuals = sezioni_manuali_disponibili(item, personaggio)
    if not manuals:
        return ""
    if len(manuals) > MAX_MANUAL_COMBINAZIONI:
        subsets = [[sezione] for sezione in manuals]
    else:
        subsets = []
        for size in range(1, len(manuals) + 1):
            subsets.extend(list(combo) for combo in combinations(manuals, size))

    parts = []
    for subset in subsets:
        stats_var = merge_statistiche_tessitura_sezioni(statistiche_base, subset)
        ctx_var = dict(context or {})
        ctx_var.update(flag_context(subset))
        formula_html = ""
        if formula:
            formula_html = formatta_testo_generico(
                None,
                formula=formula,
                statistiche_base=stats_var,
                personaggio=personaggio,
                context=ctx_var,
                solo_formula=True,
            )
        testi = []
        for sezione in subset:
            testo = (sezione.testo or "").strip()
            if not testo:
                continue
            formatted = formatta_testo_generico(
                testo,
                formula=None,
                statistiche_base=stats_var,
                personaggio=personaggio,
                context=ctx_var,
            )
            if formatted:
                testi.append(formatted)
        if not formula_html and not testi:
            continue
        flags = ",".join(sorted(str(sezione.pk) for sezione in subset))
        label = etichetta_combinazione(subset)
        inner = "".join(testi) + (formula_html or "")
        parts.append(
            f"<div class='kor-formula-variante' data-flags='{flags}' style='margin-top:8px;padding:6px 8px;"
            f"border-left:3px solid #f59e0b;background:rgba(245,158,11,0.08);'>"
            f"<div style='font-size:0.75em;text-transform:uppercase;letter-spacing:.08em;"
            f"color:#fcd34d;margin-bottom:4px;'>{label}</div>{inner}</div>"
        )
    return "".join(parts)


def statistiche_base_per_item(item, personaggio=None, base_rows=None):
    """Lista statistiche_base (oggetto/infusione) + sezioni attive."""
    from .models import Infusione, Oggetto

    if base_rows is None:
        if isinstance(item, Oggetto):
            base_rows = item.oggettostatisticabase_set.select_related("statistica").all()
        elif isinstance(item, Infusione):
            base_rows = item.infusionestatisticabase_set.select_related("statistica").all()
        else:
            base_rows = []
    return merge_statistiche_base(base_rows, sezioni_attive(item, personaggio))


def copia_sezioni_infusione_su_oggetto(infusione, oggetto):
    """Duplica le sezioni catalogo sull'istanza forgiata."""
    from .models import (
        InfusioneSezioneCondizionale,
        OggettoSezioneCondizionale,
        OggettoSezioneStatistica,
        OggettoSezioneStatisticaBase,
    )

    for src in InfusioneSezioneCondizionale.objects.filter(infusione=infusione).order_by(
        "ordine", "created_at"
    ):
        dest = OggettoSezioneCondizionale.objects.create(
            oggetto=oggetto,
            ordine=src.ordine,
            testo=src.testo,
            condizioni=src.condizioni or {},
        )
        for row in src.statistiche_base.all():
            OggettoSezioneStatisticaBase.objects.create(
                sezione=dest,
                statistica=row.statistica,
                valore_base=row.valore_base,
            )
        for mod in src.modificatori.all():
            OggettoSezioneStatistica.objects.create(
                sezione=dest,
                statistica=mod.statistica,
                valore=mod.valore,
                tipo_modificatore=mod.tipo_modificatore,
                solo_oggetto_ospitante=mod.solo_oggetto_ospitante,
            )


def sync_sezioni_nested(
    instance,
    sezioni_data,
    *,
    sezione_model,
    base_model,
    mod_model,
    parent_fk_name,
    extra_from_raw=None,
):
    """Replace-all delle sezioni nested (stesso schema degli altri pivot staff)."""
    if sezioni_data is None:
        return
    instance.sezioni_condizionali.all().delete()
    for idx, raw in enumerate(sezioni_data):
        if not isinstance(raw, dict):
            continue
        testo = raw.get("testo") or ""
        condizioni = raw.get("condizioni") if isinstance(raw.get("condizioni"), dict) else {}
        ordine = raw.get("ordine", idx)
        try:
            ordine = int(ordine)
        except (TypeError, ValueError):
            ordine = idx
        create_kwargs = {
            parent_fk_name: instance,
            "ordine": ordine,
            "testo": testo,
            "condizioni": condizioni or {},
        }
        if extra_from_raw:
            extra = extra_from_raw(raw) or {}
            create_kwargs.update(extra)
        sezione = sezione_model.objects.create(**create_kwargs)
        seen_base = set()
        for row in raw.get("statistiche_base") or []:
            if not isinstance(row, dict):
                continue
            stat = row.get("statistica")
            sid = getattr(stat, "pk", stat)
            if not sid or sid in seen_base:
                continue
            seen_base.add(sid)
            try:
                valore_base = int(row.get("valore_base") or 0)
            except (TypeError, ValueError):
                valore_base = 0
            base_model.objects.create(sezione=sezione, statistica_id=sid, valore_base=valore_base)

        if mod_model is None:
            continue
        seen_mod = set()
        for row in raw.get("modificatori") or []:
            if not isinstance(row, dict):
                continue
            stat = row.get("statistica")
            sid = getattr(stat, "pk", stat)
            if not sid or sid in seen_mod:
                continue
            seen_mod.add(sid)
            tipo = (row.get("tipo_modificatore") or "ADD").upper()
            if tipo not in ("ADD", "MOL"):
                tipo = "ADD"
            try:
                valore = row.get("valore", 0)
            except (TypeError, ValueError):
                valore = 0
            mod_model.objects.create(
                sezione=sezione,
                statistica_id=sid,
                valore=valore or 0,
                tipo_modificatore=tipo,
                solo_oggetto_ospitante=bool(row.get("solo_oggetto_ospitante")),
            )


def tessitura_sezione_extra_from_raw(raw: dict) -> dict:
    modalita = str(raw.get("modalita") or SEZIONE_MODALITA_AUTO).strip().lower()
    if modalita not in (SEZIONE_MODALITA_AUTO, SEZIONE_MODALITA_MANUALE):
        modalita = SEZIONE_MODALITA_AUTO
    etichetta = raw.get("etichetta") or ""
    if not isinstance(etichetta, str):
        etichetta = str(etichetta)
    return {
        "modalita": modalita,
        "etichetta": etichetta[:80],
        "sostituisci_bersaglio": bool(raw.get("sostituisci_bersaglio")),
    }
