"""
Interprete EffectScript v1 — risoluzione passi in duello (MVP).
"""
from __future__ import annotations

from django.core.exceptions import ValidationError

from personaggi.carte_collezionabili_models import DuelloCarte
from personaggi.carte_effect_script import resolve_param_values, resolve_value_ref
from personaggi.carte_duello_service import _append_log, _pg_key
from personaggi.models import Personaggio

EFFECT_QUEUE_KEY = "effect_queue"


def _lato_for_owner(duello: DuelloCarte, personaggio: Personaggio, owner: str) -> str:
    ctrl = _pg_key(personaggio)
    opp = _pg_key(_altro_pg(duello, personaggio))
    if owner in ("controller", "self"):
        return ctrl
    if owner == "opponent":
        return opp
    return ctrl


def _altro_pg(duello: DuelloCarte, personaggio: Personaggio) -> Personaggio:
    if duello.sfidante_id == personaggio.id:
        return duello.sfidato
    return duello.sfidante


def _get_queue(stato_gioco: dict) -> list:
    return list(stato_gioco.get(EFFECT_QUEUE_KEY) or [])


def _set_queue(stato_gioco: dict, queue: list):
    stato_gioco[EFFECT_QUEUE_KEY] = queue


def _pending_from_queue_head(duello: DuelloCarte) -> dict | None:
    stato = duello.stato_gioco or {}
    queue = _get_queue(stato)
    if not queue:
        return None
    from personaggi.models import Personaggio as Pg

    state = queue[0]
    controller = Pg.objects.get(pk=state["controller_id"])
    steps = state["script"].get("steps") or []
    idx = int(state.get("step_index") or 0)
    if idx >= len(steps) or steps[idx].get("type") != "player_choice":
        return None
    return _build_player_choice(duello, controller, steps[idx], state)


def enqueue_effect(
    duello: DuelloCarte,
    *,
    script: dict,
    controller: Personaggio,
    keyword_params: dict | None,
    context: dict,
) -> dict | None:
    """
    Accoda risoluzione effetto (FIFO). Avanza solo se la coda era vuota.
    Ritorna payload scelta aperta se serve input giocatore.
    """
    params = resolve_param_values(script, keyword_params)
    state = {
        "script": script,
        "step_index": 0,
        "params": params,
        "choices": {},
        "context": context,
        "controller_id": controller.id,
    }
    stato = duello.stato_gioco or {}
    queue = _get_queue(stato)
    queue.append(state)
    _set_queue(stato, queue)
    duello.stato_gioco = stato
    duello.save(update_fields=["stato_gioco", "updated_at"])
    if len(queue) == 1:
        return _advance_effect(duello, queue[0])
    return _pending_from_queue_head(duello)


def _advance_effect(duello: DuelloCarte, state: dict) -> dict | None:
    """Esegue passi fino a scelta giocatore o fine script."""
    from personaggi.models import Personaggio as Pg

    controller = Pg.objects.get(pk=state["controller_id"])
    script = state["script"]
    steps = script.get("steps") or []
    idx = int(state.get("step_index") or 0)

    while idx < len(steps):
        step = steps[idx]
        stype = step.get("type")

        if stype == "player_choice":
            pending = _build_player_choice(duello, controller, step, state)
            state["step_index"] = idx
            duello.save(update_fields=["stato_gioco", "updated_at"])
            if pending:
                return pending
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "replace":
            _exec_replace(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "modify_energy":
            _exec_modify_energy(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "modify_influence":
            _exec_modify_influence(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "deal_damage":
            _exec_deal_damage(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "draw_cards":
            _exec_draw_cards(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "move_card":
            _exec_move_card(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "modify_shell":
            _exec_modify_shell(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "heal_heroes":
            _exec_heal_heroes(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        if stype == "sinergia_if_active":
            _exec_sinergia_if_active(duello, controller, step, state)
            idx += 1
            state["step_index"] = idx
            continue

        raise ValidationError(f"Passo effetto non implementato: {stype}")

    _pop_queue_head(duello)
    duello.save(update_fields=["stato_gioco", "updated_at", "influenza_sfidante", "influenza_sfidato"])
    queue = _get_queue(duello.stato_gioco or {})
    if queue:
        return _advance_effect(duello, queue[0])
    return None


def _pop_queue_head(duello: DuelloCarte):
    stato = duello.stato_gioco or {}
    queue = _get_queue(stato)
    if queue:
        queue.pop(0)
    _set_queue(stato, queue)
    duello.stato_gioco = stato


def _build_player_choice(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict) -> dict | None:
    filt = step.get("filter") or {}
    choice_kind = filt.get("target") or "card"
    choice_id = step.get("id")
    optional = bool(step.get("optional", False))
    prompt = (step.get("prompt") or "Scegli").replace("{X}", str(state["params"].get("X", "")))

    if choice_kind == "hero":
        eligible_heroes = _filter_hero_targets(duello, controller, filt)
        if not eligible_heroes:
            if optional:
                state["choices"][choice_id] = None
                return None
            raise ValidationError("Nessun eroe idoneo per la scelta richiesta.")
        return {
            "type": "effect_player_choice",
            "choice_kind": "hero",
            "choice_id": choice_id,
            "prompt": prompt,
            "min": int(step.get("min") or (0 if optional else 1)),
            "max": int(step.get("max") or 1),
            "eligible_hero_targets": eligible_heroes,
        }

    owner = filt.get("owner") or "controller"
    pg_key = _lato_for_owner(duello, controller, owner)
    lato = (duello.stato_gioco or {}).get(pg_key) or {}
    zone = filt.get("zone") or "hand"
    ids = list(lato.get(zone if zone != "hand" else "mano") or [])
    if zone == "hand":
        ids = list(lato.get("mano") or [])

    eligible = _filter_card_ids(ids, controller, filt, state)

    if not eligible:
        if optional:
            state["choices"][choice_id] = None
            return None
        raise ValidationError("Nessuna carta idonea per la scelta richiesta.")

    return {
        "type": "effect_player_choice",
        "choice_kind": "card",
        "choice_id": choice_id,
        "prompt": prompt,
        "min": int(step.get("min") or (0 if optional else 1)),
        "max": int(step.get("max") or 1),
        "eligible_carta_posseduta_ids": eligible,
    }


def _filter_hero_targets(duello: DuelloCarte, controller: Personaggio, filt: dict) -> list[dict]:
    """Eroi in campo ammessi come bersaglio (token deal_damage)."""
    from personaggi.carte_collezionabili_models import CartaPosseduta

    owner = filt.get("owner") or "opponent"
    occupied_only = bool(filt.get("occupied", True))
    ctrl_key = _pg_key(controller)
    opp = _altro_pg(duello, controller)
    opp_key = _pg_key(opp)

    sides: list[tuple[str, Personaggio, str]] = []
    if owner in ("controller", "self"):
        sides.append(("hero", controller, ctrl_key))
    elif owner == "opponent":
        sides.append(("opponent_hero", opp, opp_key))
    elif owner == "any":
        sides.append(("hero", controller, ctrl_key))
        sides.append(("opponent_hero", opp, opp_key))

    out: list[dict] = []
    for prefix, pg, pg_key in sides:
        lato = (duello.stato_gioco or {}).get(pg_key) or {}
        eroi = list(lato.get("eroi") or [None, None])
        salute = list(lato.get("salute_eroi") or [None, None])
        while len(eroi) < 2:
            eroi.append(None)
        while len(salute) < 2:
            salute.append(None)
        for slot in (0, 1):
            cp_id = eroi[slot]
            if occupied_only and not cp_id:
                continue
            token = f"{prefix}_{slot}"
            label = f"Eroe slot {slot + 1}"
            if cp_id:
                cp = CartaPosseduta.objects.filter(pk=cp_id).select_related("carta").first()
                if cp:
                    label = cp.carta.nome
                    cur_hp = salute[slot]
                    if cur_hp is not None:
                        label = f"{label} ({cur_hp} PV)"
            out.append(
                {
                    "target": token,
                    "slot": slot,
                    "owner": "self" if prefix == "hero" else "opponent",
                    "carta_posseduta_id": str(cp_id) if cp_id else None,
                    "label": label,
                }
            )
    return out


def _filter_card_ids(cp_ids: list, personaggio: Personaggio, filt: dict, state: dict) -> list[str]:
    from personaggi.carte_collezionabili_models import CartaPosseduta

    if not cp_ids:
        return []
    cost_lte = filt.get("cost_play_lte")
    cost_gte = filt.get("cost_play_gte")
    card_type = filt.get("card_type")
    energy = filt.get("energy")

    lte_val = None
    gte_val = None
    if cost_lte is not None:
        lte_val = resolve_value_ref(cost_lte, params=state["params"], choices=state["choices"])
    if cost_gte is not None:
        gte_val = resolve_value_ref(cost_gte, params=state["params"], choices=state["choices"])

    qs = CartaPosseduta.objects.filter(pk__in=cp_ids, personaggio=personaggio).select_related("carta")
    out = []
    for cp in qs:
        c = cp.carta
        if card_type and c.tipo != card_type:
            continue
        if energy and c.energia != energy:
            continue
        costo = int(c.costo_gioco or 0)
        if lte_val is not None and costo > int(lte_val):
            continue
        if gte_val is not None and costo < int(gte_val):
            continue
        out.append(str(cp.id))
    return out


def submit_effect_choice(
    duello: DuelloCarte,
    personaggio: Personaggio,
    choice_id: str,
    carta_posseduta_id=None,
    *,
    hero_target: str | None = None,
) -> dict | None:
    stato = duello.stato_gioco or {}
    queue = _get_queue(stato)
    if not queue:
        raise ValidationError("Nessun effetto in attesa di scelta.")
    state = queue[0]
    if personaggio.id != state.get("controller_id"):
        raise ValidationError("Non puoi rispondere per questo effetto.")

    steps = state["script"].get("steps") or []
    idx = int(state.get("step_index") or 0)
    if idx >= len(steps) or steps[idx].get("type") != "player_choice":
        raise ValidationError("Nessuna scelta attesa in questo momento.")
    if steps[idx].get("id") != choice_id:
        raise ValidationError("ID scelta non valido.")

    pending = _build_player_choice(duello, personaggio, steps[idx], state)
    choice_kind = (pending or {}).get("choice_kind") or "card"

    if choice_kind == "hero":
        eligible = {
            row["target"]
            for row in (pending.get("eligible_hero_targets") or [])
            if row.get("target")
        }
        if hero_target:
            if hero_target not in eligible:
                raise ValidationError("Eroe non ammesso per questa scelta.")
            state["choices"][choice_id] = hero_target
        else:
            if not steps[idx].get("optional"):
                raise ValidationError("Scelta obbligatoria.")
            state["choices"][choice_id] = None
    else:
        eligible = set(pending["eligible_carta_posseduta_ids"] if pending else [])
        if carta_posseduta_id:
            cp_id = str(carta_posseduta_id)
            if cp_id not in eligible:
                raise ValidationError("Carta non ammessa per questa scelta.")
            state["choices"][choice_id] = cp_id
        else:
            if not steps[idx].get("optional"):
                raise ValidationError("Scelta obbligatoria.")
            state["choices"][choice_id] = None

    state["step_index"] = idx + 1
    duello.save(update_fields=["stato_gioco", "updated_at"])
    return _advance_effect(duello, state)


def _exec_replace(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    with_ref = resolve_value_ref(
        step.get("with"),
        params=state["params"],
        choices=state["choices"],
        context=state.get("context"),
    )
    if with_ref is None and step.get("skip_if_no_choice"):
        return
    if not with_ref:
        raise ValidationError("Sostituzione senza carta scelta.")

    ctx = state.get("context") or {}
    pg_key = ctx.get("pg_key") or _pg_key(controller)
    slot = step.get("slot") or "this"
    lato = duello.stato_gioco[pg_key]
    new_id = str(with_ref)

    if slot == "this":
        hero_slot = ctx.get("hero_slot")
        if hero_slot is not None:
            old_id = ctx.get("carta_posseduta_id")
            lato["eroi"][int(hero_slot)] = new_id
            if new_id in lato.get("mano", []):
                lato["mano"].remove(new_id)
            if old_id and str(old_id) != new_id:
                lato.setdefault("scarto", []).append(str(old_id))
            from personaggi.carte_collezionabili_models import CartaPosseduta

            cp_new = CartaPosseduta.objects.select_related("carta").get(pk=new_id)
            from personaggi.carte_duello_service import _imposta_salute_eroe_slot

            _imposta_salute_eroe_slot(lato, int(hero_slot), int(cp_new.carta.salute or 1))
        else:
            raise ValidationError("replace/this richiede context.hero_slot.")
    elif slot in ("hero_0", "hero_1"):
        idx = 0 if slot == "hero_0" else 1
        old = lato["eroi"][idx]
        lato["eroi"][idx] = new_id
        if new_id in lato.get("mano", []):
            lato["mano"].remove(new_id)
        if old:
            lato.setdefault("scarto", []).append(old)
        from personaggi.carte_collezionabili_models import CartaPosseduta
        from personaggi.carte_duello_service import _imposta_salute_eroe_slot

        cp_new = CartaPosseduta.objects.select_related("carta").get(pk=new_id)
        _imposta_salute_eroe_slot(lato, idx, int(cp_new.carta.salute or 1))
    elif slot == "location":
        lato["luogo"] = new_id
        if new_id in lato.get("mano", []):
            lato["mano"].remove(new_id)
    _append_log(duello.stato_gioco, f"{controller.nome}: sostituzione carta (effetto).")


def _exec_modify_energy(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    delta = int(resolve_value_ref(step.get("delta"), params=state["params"], choices=state["choices"]) or 0)
    target = step.get("target") or "self"
    pg_key = _lato_for_owner(duello, controller, "controller" if target == "self" else "opponent")
    lato = duello.stato_gioco[pg_key]
    lato["energia"] = max(0, int(lato.get("energia") or 0) + delta)


def _exec_modify_influence(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    delta = int(resolve_value_ref(step.get("delta"), params=state["params"], choices=state["choices"]) or 0)
    target = step.get("target") or "opponent"
    if target == "self":
        if duello.sfidante_id == controller.id:
            duello.influenza_sfidante = max(0, duello.influenza_sfidante + delta)
        else:
            duello.influenza_sfidato = max(0, duello.influenza_sfidato + delta)
    else:
        if duello.sfidante_id == controller.id:
            duello.influenza_sfidato = max(0, duello.influenza_sfidato + delta)
        else:
            duello.influenza_sfidante = max(0, duello.influenza_sfidante + delta)


def _exec_deal_damage(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    from personaggi.carte_duello_service import _applica_danno_eroe

    amount = int(resolve_value_ref(step.get("amount"), params=state["params"], choices=state["choices"]) or 0)
    raw_target = step.get("target") or "opponent_influence"
    if isinstance(raw_target, dict) and "ref" in raw_target:
        target = resolve_value_ref(
            raw_target,
            params=state["params"],
            choices=state["choices"],
            context=state.get("context"),
        )
    else:
        target = raw_target
    if not target:
        raise ValidationError("Bersaglio danno non specificato.")
    opp = _altro_pg(duello, controller)

    if target == "opponent_influence":
        if duello.sfidante_id == controller.id:
            duello.influenza_sfidato = max(0, duello.influenza_sfidato - amount)
        else:
            duello.influenza_sfidante = max(0, duello.influenza_sfidante - amount)
        return

    hero_slot_map = {
        "hero_0": (controller, 0),
        "hero_1": (controller, 1),
        "opponent_hero_0": (opp, 0),
        "opponent_hero_1": (opp, 1),
    }
    if target in hero_slot_map:
        owner, slot = hero_slot_map[target]
        _applica_danno_eroe(duello, owner, slot, amount)
        return

    raise ValidationError(f"Target deal_damage non supportato: {target}")


def _exec_draw_cards(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    count = max(0, int(resolve_value_ref(step.get("count"), params=state["params"], choices=state["choices"]) or 1))
    target = step.get("target") or "self"
    pg_key = _lato_for_owner(duello, controller, "controller" if target == "self" else "opponent")
    lato = duello.stato_gioco[pg_key]
    pescate = 0
    for _ in range(count):
        if not lato.get("mazzo"):
            break
        lato.setdefault("mano", []).append(lato["mazzo"].pop())
        pescate += 1
    if pescate:
        _append_log(duello.stato_gioco, f"{controller.nome}: pesca {pescate} carta/e (effetto).")


def _zone_list_key(zone: str) -> str:
    return {"hand": "mano", "deck": "mazzo", "discard": "scarto"}.get(zone, zone)


def _exec_move_card(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    ctx = state.get("context") or {}
    card_ref = step.get("card") or {"ref": "context.carta_posseduta_id"}
    cp_id = resolve_value_ref(
        card_ref,
        params=state["params"],
        choices=state["choices"],
        context=ctx,
    )
    if not cp_id:
        if step.get("optional"):
            return
        raise ValidationError("move_card senza carta.")
    cp_id = str(cp_id)
    from_zone = step.get("from") or "hand"
    to_zone = step.get("to") or "discard"
    pg_key = ctx.get("pg_key") or _pg_key(controller)
    lato = duello.stato_gioco[pg_key]

    if from_zone == "field":
        field_slot = step.get("field_slot") or ctx.get("field_slot")
        if field_slot in ("hero_0", "hero_1"):
            idx = 0 if field_slot == "hero_0" else 1
            if str(lato.get("eroi", [None, None])[idx]) != cp_id:
                raise ValidationError("Carta non nello slot eroe indicato.")
            lato["eroi"][idx] = None
            sal = lato.setdefault("salute_eroi", [None, None])
            if idx < len(sal):
                sal[idx] = None
        elif field_slot == "location":
            if str(lato.get("luogo")) != cp_id:
                raise ValidationError("Carta non nel luogo.")
            lato["luogo"] = None
        else:
            raise ValidationError("field_slot richiesto per move_card da field.")
    else:
        src_key = _zone_list_key(from_zone)
        src = list(lato.get(src_key) or [])
        if cp_id not in src:
            raise ValidationError(f"Carta non in {from_zone}.")
        src.remove(cp_id)
        lato[src_key] = src

    if to_zone == "field":
        field_slot = step.get("field_slot")
        if field_slot in ("hero_0", "hero_1"):
            idx = 0 if field_slot == "hero_0" else 1
            lato["eroi"][idx] = cp_id
            from personaggi.carte_collezionabili_models import CartaPosseduta
            from personaggi.carte_duello_service import _imposta_salute_eroe_slot

            cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id)
            _imposta_salute_eroe_slot(lato, idx, int(cp.carta.salute or 1))
        elif field_slot == "location":
            lato["luogo"] = cp_id
        else:
            raise ValidationError("field_slot richiesto per move_card verso field.")
    elif to_zone == "exhaust":
        lato.setdefault("scarto", []).append(cp_id)
    else:
        dst_key = _zone_list_key(to_zone)
        dst = list(lato.get(dst_key) or [])
        dst.append(cp_id)
        lato[dst_key] = dst
    _append_log(duello.stato_gioco, f"{controller.nome}: spostamento carta (effetto).")


def _resolve_hero_slot_from_step(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict) -> int | None:
    from personaggi.carte_duello_service import _hero_slot_per_carta

    hero = step.get("hero") or "this"
    ctx = state.get("context") or {}
    pg_key = ctx.get("pg_key") or _pg_key(controller)
    lato = (duello.stato_gioco or {}).get(pg_key) or {}
    if hero == "this":
        slot = ctx.get("hero_slot")
        if slot is not None:
            return int(slot)
        return _hero_slot_per_carta(lato, ctx.get("carta_posseduta_id"))
    if hero in ("hero_0", "hero_1"):
        return 0 if hero == "hero_0" else 1
    return None


def _exec_modify_shell(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    from personaggi.carte_duello_service import _modifica_guscio_eroe

    slot = _resolve_hero_slot_from_step(duello, controller, step, state)
    if slot is None:
        if step.get("optional"):
            return
        raise ValidationError("modify_shell: slot eroe non trovato.")
    delta = int(resolve_value_ref(step.get("delta"), params=state["params"], choices=state["choices"]) or 0)
    pg_key = (state.get("context") or {}).get("pg_key") or _pg_key(controller)
    lato = duello.stato_gioco[pg_key]
    _modifica_guscio_eroe(lato, slot, delta, set_value=bool(step.get("set")))
    _append_log(duello.stato_gioco, f"{controller.nome}: Guscio slot {slot + 1} → {_guscio_log(lato, slot)}.")


def _guscio_log(lato: dict, slot: int) -> int:
    from personaggi.carte_duello_service import _guscio_eroi

    return _guscio_eroi(lato)[slot]


def _exec_heal_heroes(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    from personaggi.carte_duello_service import (
        _eroi_esauriti,
        _hero_slot_per_carta,
        _stats_eroe_slot,
    )

    target = step.get("target") or "self_hero"
    amount_raw = step.get("amount", 1)
    if amount_raw == "full":
        amount = None
    else:
        amount = int(resolve_value_ref(amount_raw, params=state["params"], choices=state["choices"]) or 0)

    ctx = state.get("context") or {}
    pg_key = ctx.get("pg_key") or _pg_key(controller)
    lato = duello.stato_gioco[pg_key]
    esauriti = _eroi_esauriti(lato)
    sal = lato.setdefault("salute_eroi", [None, None])
    slots: list[int] = []

    if target == "self_hero":
        slot = _resolve_hero_slot_from_step(duello, controller, step, state)
        if slot is not None:
            slots = [slot]
    elif target in ("own_heroes", "own_non_exhausted"):
        for slot in (0, 1):
            if not (lato.get("eroi") or [None, None])[slot]:
                continue
            if target == "own_non_exhausted" and esauriti[slot]:
                continue
            slots.append(slot)
    else:
        raise ValidationError(f"heal_heroes target non supportato: {target}")

    curati = 0
    for slot in slots:
        try:
            stats = _stats_eroe_slot(duello, controller, lato, slot)
            max_hp = int(stats["robustezza"])
            cur = sal[slot]
            if cur is None:
                cur = max_hp
            if amount is None:
                sal[slot] = max_hp
            else:
                sal[slot] = min(max_hp, int(cur) + amount)
            curati += 1
        except Exception:
            continue
    if curati:
        _append_log(duello.stato_gioco, f"{controller.nome}: Guarigione su {curati} personaggio/i.")


def _conta_eroi_sinergia(lato: dict) -> int:
    from personaggi.carte_collezionabili_models import CartaPosseduta

    count = 0
    for slot in (0, 1):
        cp_id = (lato.get("eroi") or [None, None])[slot]
        if not cp_id:
            continue
        cp = CartaPosseduta.objects.filter(pk=cp_id).select_related("carta").first()
        if cp and "sinergia" in (cp.carta.testo_gioco or "").lower():
            count += 1
    return count


def _exec_sinergia_if_active(duello: DuelloCarte, controller: Personaggio, step: dict, state: dict):
    min_count = int(step.get("min_count") or 2)
    pg_key = (state.get("context") or {}).get("pg_key") or _pg_key(controller)
    lato = duello.stato_gioco[pg_key]
    if _conta_eroi_sinergia(lato) < min_count:
        return

    draw_count = step.get("draw_count")
    if draw_count is not None:
        sub = {
            "type": "draw_cards",
            "count": draw_count,
            "target": step.get("draw_target") or "self",
        }
        _exec_draw_cards(duello, controller, sub, state)

    energy_delta = step.get("energy_delta")
    if energy_delta is not None:
        sub = {
            "type": "modify_energy",
            "target": step.get("energy_target") or "self",
            "delta": energy_delta,
        }
        _exec_modify_energy(duello, controller, sub, state)

    _append_log(duello.stato_gioco, f"{controller.nome}: Sinergia attiva ({min_count}+ personaggi).")


def get_open_effect_choice(duello: DuelloCarte, personaggio: Personaggio) -> dict | None:
    stato = duello.stato_gioco or {}
    queue = _get_queue(stato)
    if not queue:
        return None
    state = queue[0]
    if personaggio.id != state.get("controller_id"):
        return None
    steps = state["script"].get("steps") or []
    idx = int(state.get("step_index") or 0)
    if idx >= len(steps) or steps[idx].get("type") != "player_choice":
        return None
    return _build_player_choice(duello, personaggio, steps[idx], state)


def trigger_keyword_effects_for_event(
    duello: DuelloCarte,
    personaggio: Personaggio,
    testo_gioco: str,
    event: str,
    *,
    context: dict | None = None,
) -> dict | None:
    """Accoda tutti gli effect_script con trigger `event` trovati nel testo (ordine di lettura)."""
    from personaggi.carte_keyword_utils import find_all_keyword_effects_in_text

    hits = find_all_keyword_effects_in_text(personaggio.campagna, testo_gioco or "", event)
    if not hits:
        return None
    ctx_base = {"pg_key": _pg_key(personaggio), **(context or {})}
    pending = None
    for hit in hits:
        ctx = dict(ctx_base)
        if hit.get("index") is not None:
            ctx["keyword_index"] = hit["index"]
        result = enqueue_effect(
            duello,
            script=hit["effect_script"],
            controller=personaggio,
            keyword_params=hit.get("params"),
            context=ctx,
        )
        if result:
            pending = result
    return pending


def trigger_keyword_effect_for_event(
    duello: DuelloCarte,
    personaggio: Personaggio,
    testo_gioco: str,
    event: str,
    *,
    context: dict | None = None,
) -> dict | None:
    """Alias: accoda tutte le keyword per l'evento (catena FIFO)."""
    return trigger_keyword_effects_for_event(
        duello, personaggio, testo_gioco, event, context=context
    )


def trigger_keyword_effects_on_exhaust(
    duello: DuelloCarte,
    personaggio: Personaggio,
    *,
    carta_posseduta_id: str,
    hero_slot: int,
    testo_gioco: str,
) -> dict | None:
    """Accoda tutti gli script on_exhaust nel testo della carta esaurita."""
    from personaggi.carte_keyword_utils import find_all_keyword_effects_in_text

    hits = find_all_keyword_effects_in_text(personaggio.campagna, testo_gioco or "", "on_exhaust")
    if not hits:
        return None
    ctx_base = {
        "pg_key": _pg_key(personaggio),
        "hero_slot": hero_slot,
        "carta_posseduta_id": str(carta_posseduta_id),
    }
    pending = None
    for hit in hits:
        ctx = dict(ctx_base)
        if hit.get("index") is not None:
            ctx["keyword_index"] = hit["index"]
        result = enqueue_effect(
            duello,
            script=hit["effect_script"],
            controller=personaggio,
            keyword_params=hit.get("params"),
            context=ctx,
        )
        if result:
            pending = result
    return pending


def trigger_keyword_effect_on_exhaust(
    duello: DuelloCarte,
    personaggio: Personaggio,
    *,
    carta_posseduta_id: str,
    hero_slot: int,
    keyword_params: dict | None,
    effect_script: dict,
) -> dict | None:
    """Avvia un singolo script on_exhaust (uso diretto / test)."""
    if not effect_script or effect_script.get("trigger", {}).get("event") != "on_exhaust":
        return None
    ctx = {
        "pg_key": _pg_key(personaggio),
        "hero_slot": hero_slot,
        "carta_posseduta_id": str(carta_posseduta_id),
    }
    return enqueue_effect(
        duello,
        script=effect_script,
        controller=personaggio,
        keyword_params=keyword_params,
        context=ctx,
    )
