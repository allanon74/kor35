"""
Utility tag carte: assegnazione esplicita su catalogo, filtri per effetti duello.
"""
from __future__ import annotations

from personaggi.carte_collezionabili_models import CartaPosseduta, TagCarta


def _norm_codice(codice: str) -> str:
    return (codice or "").strip().upper()


def codici_tag_carta(carta) -> set[str]:
    """Codici tag attivi sulla definizione carta (richiede prefetch tags se possibile)."""
    if carta is None:
        return set()
    if hasattr(carta, "_prefetched_objects_cache") and "tags" in getattr(carta, "_prefetched_objects_cache", {}):
        tags = carta.tags.all()
    else:
        tags = carta.tags.filter(attiva=True)
    return {_norm_codice(t.codice) for t in tags if t.attiva and t.codice}


def carta_ha_tag(carta, codice: str, *, tags_any: list[str] | None = None) -> bool:
    """Verifica tag singolo o lista (almeno uno)."""
    codici = codici_tag_carta(carta)
    if tags_any:
        wanted = {_norm_codice(c) for c in tags_any if c}
        return bool(codici & wanted)
    return _norm_codice(codice) in codici


def _carta_eroe_slot(lato: dict, slot: int):
    from personaggi.carte_collezionabili_models import CartaPosseduta

    cp_id = (lato.get("eroi") or [None, None])[slot]
    if not cp_id:
        return None
    return CartaPosseduta.objects.filter(pk=cp_id).select_related("carta").prefetch_related("carta__tags").first()


def eroe_slot_match_tag_filter(
    lato: dict,
    slot: int,
    *,
    tags_any: list[str] | None = None,
    tags_all: list[str] | None = None,
    tags_none: list[str] | None = None,
) -> bool:
    cp = _carta_eroe_slot(lato, slot)
    if not cp:
        return False
    codici = codici_tag_carta(cp.carta)
    if tags_none:
        banned = {_norm_codice(c) for c in tags_none if c}
        if codici & banned:
            return False
    if tags_all:
        needed = {_norm_codice(c) for c in tags_all if c}
        if not needed.issubset(codici):
            return False
    if tags_any:
        wanted = {_norm_codice(c) for c in tags_any if c}
        if not (codici & wanted):
            return False
    return True


def iter_eroi_per_tag_filter(
    duello,
    controller,
    owner: str,
    *,
    tags_any: list[str] | None = None,
    tags_all: list[str] | None = None,
    tags_none: list[str] | None = None,
) -> list[tuple[object, dict, int]]:
    """
    Ritorna [(personaggio, lato, slot), …] per eroi che soddisfano filtro tag.
    owner: controller | opponent | any
    """
    from personaggi.carte_duello_service import _altro_pg, _pg_key

    owner = (owner or "controller").lower()
    out: list[tuple[object, dict, int]] = []
    pairs: list[tuple[object, str]] = []
    if owner in ("controller", "self"):
        pairs = [(controller, _pg_key(controller))]
    elif owner == "opponent":
        pairs = [(_altro_pg(duello, controller), _pg_key(_altro_pg(duello, controller)))]
    else:
        pairs = [
            (duello.sfidante, _pg_key(duello.sfidante)),
        ]
        if duello.sfidato_id:
            pairs.append((duello.sfidato, _pg_key(duello.sfidato)))

    stato = duello.stato_gioco or {}
    for pg, pg_key in pairs:
        lato = stato.get(pg_key) or {}
        for slot in (0, 1):
            if eroe_slot_match_tag_filter(
                lato,
                slot,
                tags_any=tags_any,
                tags_all=tags_all,
                tags_none=tags_none,
            ):
                out.append((pg, lato, slot))
    return out


def lista_tags_campagna(campagna) -> list[dict]:
    return list(
        TagCarta.objects.filter(campagna=campagna, attiva=True)
        .order_by("nome")
        .values("id", "codice", "nome", "descrizione", "colore")
    )
