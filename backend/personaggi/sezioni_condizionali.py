"""
Sezioni condizionali di Infusione/Oggetto: testo extra + statistiche
visibili/attive solo se il personaggio soddisfa un gruppo di requisiti.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from .requisiti_accesso import (
    gruppo_requisiti_soddisfatto,
    simbolo_operatore,
)


class _MergedStatBase:
    """Adattatore minimale per formatta_testo_generico (statistica + valore_base)."""

    __slots__ = ("statistica", "valore_base", "statistica_id")

    def __init__(self, statistica, valore_base):
        self.statistica = statistica
        self.valore_base = valore_base
        self.statistica_id = getattr(statistica, "pk", None)


def prefetch_sezioni_related(qs):
    return qs.prefetch_related(
        "statistiche_base__statistica",
        "modificatori__statistica",
    )


def sezioni_queryset(item):
    from .models import Infusione, Oggetto

    manager = getattr(item, "sezioni_condizionali", None)
    if manager is None:
        return None
    qs = manager.order_by("ordine", "created_at")
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
    return [s for s in qs if sezione_attiva(s, personaggio, **eval_kwargs)]


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
    from .models import formatta_testo_generico

    sezioni = sezioni_attive(item, personaggio)
    if not sezioni:
        return ""
    parts = []
    for sezione in sezioni:
        testo = (sezione.testo or "").strip()
        if not testo:
            continue
        formatted = formatta_testo_generico(
            testo,
            formula=None,
            statistiche_base=statistiche_base,
            personaggio=personaggio,
            context=context,
        )
        if not formatted:
            continue
        label = etichetta_condizioni(sezione.condizioni)
        if personaggio is None:
            parts.append(
                f"<div class='sezione-condizionale' style='margin-top:8px;padding:6px 8px;"
                f"border-left:3px solid #6366f1;background:rgba(99,102,241,0.08);'>"
                f"<div style='font-size:0.75em;text-transform:uppercase;letter-spacing:.08em;"
                f"color:#a5b4fc;margin-bottom:4px;'>Se {label}</div>{formatted}</div>"
            )
        else:
            parts.append(f"<div class='sezione-condizionale' style='margin-top:8px;'>{formatted}</div>")
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


def sync_sezioni_nested(instance, sezioni_data, *, sezione_model, base_model, mod_model, parent_fk_name):
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
        sezione = sezione_model.objects.create(
            **{
                parent_fk_name: instance,
                "ordine": ordine,
                "testo": testo,
                "condizioni": condizioni or {},
            }
        )
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
