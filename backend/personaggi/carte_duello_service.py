"""
Duello carte live — stato partita, turni, sincronizzazione.
"""
from __future__ import annotations

import random
import re
import secrets
import string

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_ARCANA,
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_LUOGO,
    CARTA_TIPO_OGGETTO,
    CARTA_TIPO_PERSONAGGIO,
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    DUELLO_AVVIO_TEST,
    DUELLO_MODALITA_MANUALE,
    DUELLO_STATO_ANNULLATO,
    DUELLO_STATO_ATTESA,
    DUELLO_STATO_FINITO,
    DUELLO_STATO_IN_CORSO,
    DUELLO_STATO_LOBBY,
    DUELLO_STATO_PREMATCH,
    DuelloCarte,
    INFLUENZA_INIZIALE,
    MAZZO_DUELLO_SIZE,
)
from personaggi.carte_collezionabili_service import (
    assert_personaggio_puo_accedere_carte,
    get_carte_accesso_modo,
    personaggio_puo_accedere_carte,
    valida_setup_duello,
)
from personaggi.carte_duello_ws import broadcast_duello_update
from personaggi.models import Personaggio

MANA_MASSIMO_BASE = 3
MANA_MASSIMO_ARCANA = 4

FASE_TURNO_APERTURA = "APE"
FASE_TURNO_COMBATTIMENTO = "COM"
FASE_TURNO_CHIUSURA = "CHI"
FASE_TURNO_LABEL = {
    FASE_TURNO_APERTURA: "Apertura",
    FASE_TURNO_COMBATTIMENTO: "Combattimento",
    FASE_TURNO_CHIUSURA: "Chiusura",
}

BONUS_LEADER_BY_AURA = {
    CARTA_ENERGIA_MARZIALE: ["+1 Forza a tutti i tuoi personaggi"],
    CARTA_ENERGIA_SACRA: ["+2 Robustezza a tutti i tuoi personaggi"],
    CARTA_ENERGIA_PSIONICA: ["+1 Iniziativa a tutti i tuoi personaggi"],
    CARTA_ENERGIA_MAGICA: ["−1 costo mana agli Effetti"],
    CARTA_ENERGIA_INNATA: ["−1 costo mana ai Personaggi"],
    CARTA_ENERGIA_TECNOLOGICA: ["−1 costo mana agli Equipaggiamenti"],
    CARTA_ENERGIA_ARCANA: ["+1 mana massimo per turno (fino a 4)"],
}


def bonus_leader_attivi(duello: DuelloCarte, personaggio: Personaggio) -> list[str]:
    aura = _aura_primaria(duello, personaggio)
    if not aura:
        return []
    return list(BONUS_LEADER_BY_AURA.get(aura, []))


def _guscio_eroi(lato: dict) -> list[int]:
    raw = lato.get("guscio_eroi") or [0, 0]
    out = [int(raw[0] or 0), int(raw[1] or 0) if len(raw) > 1 else 0]
    return out


def _modifica_guscio_eroe(lato: dict, slot: int, delta: int, *, set_value: bool = False) -> None:
    guscio = _guscio_eroi(lato)
    while len(guscio) < 2:
        guscio.append(0)
    if set_value:
        guscio[slot] = max(0, int(delta))
    else:
        guscio[slot] = max(0, guscio[slot] + int(delta))
    lato["guscio_eroi"] = guscio


def _hero_slot_per_carta(lato: dict, carta_posseduta_id) -> int | None:
    if not carta_posseduta_id:
        return None
    cp_s = str(carta_posseduta_id)
    eroi = lato.get("eroi") or [None, None]
    for slot in (0, 1):
        if eroi[slot] and str(eroi[slot]) == cp_s:
            return slot
    return None


def _avanza_fase_turno(duello: DuelloCarte, personaggio: Personaggio) -> bool:
    """
    Avanza la fase del turno. Ritorna True se il turno deve terminare (_fine_turno).
    """
    pg_key = _pg_key(personaggio)
    lato = duello.stato_gioco[pg_key]
    fase = lato.get("fase_turno") or FASE_TURNO_APERTURA
    flags = lato.get("turno_flags") or _turno_flags_vuoti()

    if fase == FASE_TURNO_APERTURA:
        lato["fase_turno"] = FASE_TURNO_COMBATTIMENTO
        _append_log(duello.stato_gioco, f"{personaggio.nome}: fase combattimento.")
        return False

    if fase == FASE_TURNO_COMBATTIMENTO:
        if not flags.get("permanente_giocato") or not flags.get("effetto_giocato"):
            lato["fase_turno"] = FASE_TURNO_CHIUSURA
            _append_log(
                duello.stato_gioco,
                f"{personaggio.nome}: fase finale — puoi ancora giocare carte.",
            )
            return False
        return True

    return True
MANO_INIZIALE = 4
MAX_EROI = 2


def _turno_flags_vuoti() -> dict:
    return {"permanente_giocato": False, "effetto_giocato": False}


def _personaggio_da_key(duello: DuelloCarte, pg_key: str) -> Personaggio | None:
    if str(duello.sfidante_id) == str(pg_key):
        return duello.sfidante
    if duello.sfidato_id and str(duello.sfidato_id) == str(pg_key):
        return duello.sfidato
    return None


def _leader_carta_posseduta_id(duello: DuelloCarte, personaggio: Personaggio) -> str | None:
    """ID carta Leader del mazzo (identità partita / aura primaria)."""
    if personaggio.id == duello.sfidante_id:
        lid = duello.leader_sfidante_id
    else:
        lid = duello.leader_sfidato_id
    return str(lid) if lid else None


def carta_e_leader_partita(
    duello: DuelloCarte,
    personaggio: Personaggio,
    carta_posseduta_id,
) -> bool:
    """True se la carta è il Leader scelto in prematch (flag «è Leader» in partita)."""
    lid = _leader_carta_posseduta_id(duello, personaggio)
    return bool(lid and str(carta_posseduta_id) == lid)


def slot_leader_in_campo(lato: dict, leader_cp_id: str | None) -> int | None:
    """Slot eroe (0/1) occupato dal Leader, se in campo."""
    if not leader_cp_id:
        return None
    lid = str(leader_cp_id)
    for slot in (0, 1):
        cp_id = (lato.get("eroi") or [None, None])[slot]
        if cp_id and str(cp_id) == lid:
            return slot
    return None


def _aura_primaria(duello: DuelloCarte, personaggio: Personaggio) -> str | None:
    """Aura primaria del mazzo = energia del Leader scelto in setup."""
    leader_id = _leader_carta_posseduta_id(duello, personaggio)
    if not leader_id:
        return None
    from personaggi.carte_collezionabili_models import CartaPosseduta

    cp = CartaPosseduta.objects.select_related("carta").filter(pk=leader_id).first()
    return cp.carta.energia if cp else None


def _aura_leader(duello: DuelloCarte, personaggio: Personaggio) -> str | None:
    """Alias retrocompatibile: aura primaria da Leader di mazzo."""
    return _aura_primaria(duello, personaggio)


def mana_massimo_giocatore(duello: DuelloCarte, personaggio: Personaggio) -> int:
    """Massimo mana rinnovabile per turno (3 base, 4 con Leader Arcana)."""
    if _aura_leader(duello, personaggio) == CARTA_ENERGIA_ARCANA:
        return MANA_MASSIMO_ARCANA
    return MANA_MASSIMO_BASE


def mana_disponibile_per_turno(turno_numero: int, mana_massimo: int) -> int:
    """Curva 1 → 2 → massimo dal turno 3 in poi."""
    n = max(1, int(turno_numero or 1))
    if n == 1:
        return 1
    if n == 2:
        return 2
    return mana_massimo


def costo_effettivo_carta(duello: DuelloCarte, personaggio: Personaggio, carta) -> int:
    """Costo mana con bonus color pie del Leader (aura primaria)."""
    costo = int(carta.costo_gioco or 0)
    aura = _aura_leader(duello, personaggio)
    if aura == CARTA_ENERGIA_MAGICA and carta.tipo == CARTA_TIPO_EVENTO:
        costo -= 1
    elif aura == CARTA_ENERGIA_INNATA and carta.tipo == CARTA_TIPO_PERSONAGGIO:
        costo -= 1
    elif aura == CARTA_ENERGIA_TECNOLOGICA and carta.tipo == CARTA_TIPO_OGGETTO:
        costo -= 1
    return max(0, costo)


_DIFENSORE_RE = re.compile(r"\bdifensore\b", re.IGNORECASE)


def _carta_ha_difensore(testo: str | None) -> bool:
    return bool(_DIFENSORE_RE.search(testo or ""))


def stats_combattimento_carta(
    duello: DuelloCarte,
    owner_pg: Personaggio,
    carta,
    *,
    carta_posseduta_id=None,
) -> dict:
    """Forza, Robustezza e Iniziativa con bonus aura primaria (Leader di mazzo)."""
    forza = int(carta.attacco or 1)
    robustezza = max(1, int(carta.salute or 1))
    iniziativa = int(carta.iniziativa or 0)
    is_leader = (
        carta_e_leader_partita(duello, owner_pg, carta_posseduta_id)
        if carta_posseduta_id
        else False
    )
    aura = _aura_primaria(duello, owner_pg)
    if aura == CARTA_ENERGIA_MARZIALE:
        forza += 1
    if aura == CARTA_ENERGIA_SACRA:
        robustezza += 2
    if aura == CARTA_ENERGIA_PSIONICA:
        iniziativa += 1
    return {
        "forza": forza,
        "robustezza": robustezza,
        "iniziativa": iniziativa,
        "is_leader": is_leader,
    }


def _stats_eroe_slot(duello: DuelloCarte, owner_pg: Personaggio, lato: dict, slot: int) -> dict:
    from personaggi.carte_collezionabili_models import CartaPosseduta
    from personaggi.carte_equip_bonus import applica_bonus_equip_duello

    cp_id = (lato.get("eroi") or [None, None])[slot]
    cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id)
    stats = stats_combattimento_carta(duello, owner_pg, cp.carta, carta_posseduta_id=cp_id)
    og_id = (lato.get("oggetti") or {}).get(str(slot))
    if og_id:
        cp_ogg = CartaPosseduta.objects.select_related("carta").get(pk=og_id)
        delta = applica_bonus_equip_duello(
            cp_ogg.carta.bonus_equip,
            is_leader=stats["is_leader"],
        )
        for key in ("forza", "robustezza", "iniziativa"):
            stats[key] += delta[key]
    fb = lato.get("forza_bonus_eroi") or [0, 0]
    rb = lato.get("robustezza_bonus_eroi") or [0, 0]
    while len(fb) < 2:
        fb.append(0)
    while len(rb) < 2:
        rb.append(0)
    stats["forza"] = int(stats.get("forza", 0)) + int(fb[slot] or 0)
    stats["robustezza"] = int(stats.get("robustezza", 0)) + int(rb[slot] or 0)
    return stats


def _aggiorna_salute_eroe_da_stats(lato: dict, slot: int, stats: dict) -> None:
    """Allinea PV correnti alla Robustezza (es. dopo equip che aumenta il massimo)."""
    sal = lato.setdefault("salute_eroi", [None, None])
    while len(sal) < 2:
        sal.append(None)
    nuova = int(stats["robustezza"])
    cur = sal[slot]
    if cur is None:
        sal[slot] = nuova
    elif int(cur) < nuova:
        sal[slot] = nuova
    else:
        sal[slot] = min(int(cur), nuova)


def _eroi_esauriti(lato: dict) -> list[bool]:
    raw = lato.get("eroi_esauriti")
    if not raw:
        return [False, False]
    out = list(raw)
    while len(out) < 2:
        out.append(False)
    return out[:2]


def _esaurisci_eroe(lato: dict, slot: int):
    es = lato.setdefault("eroi_esauriti", [False, False])
    while len(es) < 2:
        es.append(False)
    es[slot] = True


def slot_difensore(lato: dict) -> int | None:
    """Slot eroe con keyword Difensore in campo, se presente."""
    from personaggi.carte_collezionabili_models import CartaPosseduta

    for slot in (0, 1):
        cp_id = (lato.get("eroi") or [None, None])[slot]
        if not cp_id:
            continue
        cp = CartaPosseduta.objects.select_related("carta").filter(pk=cp_id).first()
        if cp and _carta_ha_difensore(cp.carta.testo_gioco):
            return slot
    return None


def _valida_bersaglio_difensore(alt_lato: dict, bersaglio_eroe_slot) -> None:
    d_slot = slot_difensore(alt_lato)
    if d_slot is None:
        return
    if bersaglio_eroe_slot is None:
        raise ValidationError("Devi attaccare il Difensore avversario.")
    if int(bersaglio_eroe_slot) != d_slot:
        raise ValidationError("Devi attaccare il Difensore avversario.")


def _eroe_ancora_in_campo(lato: dict, slot: int) -> bool:
    eroi = lato.get("eroi") or [None, None]
    return bool(eroi[slot] if slot < len(eroi) else None)


def _scambio_combattimento_iniziativa(
    duello: DuelloCarte,
    ini_att: int,
    dmg_att: int,
    applica_danno_a_difensore,
    difensore_ancora_attivo,
    ini_def: int,
    dmg_def: int,
    applica_danno_ad_attaccante,
    attaccante_ancora_attivo,
) -> None:
    """Risolve uno scambio danni con regole Iniziativa."""
    if ini_att > ini_def:
        morto_def = applica_danno_a_difensore(dmg_att)
        danno_risposta = 0 if morto_def else dmg_def
        if not morto_def and attaccante_ancora_attivo():
            applica_danno_ad_attaccante(dmg_def)
        _append_log(
            duello.stato_gioco,
            f"Combattimento (ini {ini_att}>{ini_def}): danni {dmg_att}/{danno_risposta}.",
        )
    elif ini_def > ini_att:
        morto_att = applica_danno_ad_attaccante(dmg_def)
        danno_risposta = 0 if morto_att else dmg_att
        if not morto_att and difensore_ancora_attivo():
            applica_danno_a_difensore(dmg_att)
        _append_log(
            duello.stato_gioco,
            f"Combattimento (ini {ini_def}>{ini_att}): danni {dmg_def}/{danno_risposta}.",
        )
    else:
        applica_danno_a_difensore(dmg_att)
        applica_danno_ad_attaccante(dmg_def)
        _append_log(
            duello.stato_gioco,
            f"Combattimento simultaneo (ini {ini_att}): danni {dmg_att}/{dmg_def}.",
        )


def _combatti_eroi(
    duello: DuelloCarte,
    attaccante_pg: Personaggio,
    slot_att: int,
    difensore_pg: Personaggio,
    slot_def: int,
) -> None:
    """Scambio PG vs PG con regole Iniziativa."""
    lato_a = duello.stato_gioco[_pg_key(attaccante_pg)]
    lato_d = duello.stato_gioco[_pg_key(difensore_pg)]
    sa = _stats_eroe_slot(duello, attaccante_pg, lato_a, slot_att)
    sd = _stats_eroe_slot(duello, difensore_pg, lato_d, slot_def)
    _scambio_combattimento_iniziativa(
        duello,
        sa["iniziativa"],
        sa["forza"],
        lambda d: _applica_danno_eroe(duello, difensore_pg, slot_def, d),
        lambda: _eroe_ancora_in_campo(lato_d, slot_def),
        sd["iniziativa"],
        sd["forza"],
        lambda d: _applica_danno_eroe(duello, attaccante_pg, slot_att, d),
        lambda: _eroe_ancora_in_campo(lato_a, slot_att),
    )


def _cura_eroi_fine_turno(duello: DuelloCarte, personaggio: Personaggio):
    """Eroi non esauriti recuperano tutta la Robustezza a fine turno."""
    pg_key = _pg_key(personaggio)
    lato = duello.stato_gioco[pg_key]
    esauriti = _eroi_esauriti(lato)
    sal = lato.setdefault("salute_eroi", [None, None])
    curati = 0
    for slot in (0, 1):
        if not _eroe_ancora_in_campo(lato, slot) or esauriti[slot]:
            continue
        try:
            stats = _stats_eroe_slot(duello, personaggio, lato, slot)
            sal[slot] = stats["robustezza"]
            curati += 1
        except Exception:
            continue
    if curati:
        _append_log(
            duello.stato_gioco,
            f"{personaggio.nome}: {curati} personaggio/i si curano a fine turno.",
        )


def _pg_key(personaggio: Personaggio) -> str:
    return str(personaggio.id)


def _altro_pg(duello: DuelloCarte, personaggio: Personaggio) -> Personaggio:
    if duello.sfidante_id == personaggio.id:
        return duello.sfidato
    return duello.sfidante


def _ruolo_in_duello(duello: DuelloCarte, personaggio: Personaggio) -> str:
    return "sfidante" if duello.sfidante_id == personaggio.id else "sfidato"


def _genera_codice_invito() -> str:
    alfabeto = string.ascii_uppercase + string.digits
    for _ in range(30):
        codice = "".join(secrets.choice(alfabeto) for _ in range(6))
        if not DuelloCarte.objects.filter(
            codice_invito=codice,
            stato__in=(DUELLO_STATO_ATTESA, DUELLO_STATO_LOBBY),
        ).exists():
            return codice
    raise ValidationError("Impossibile generare codice invito.")


def risolvi_personaggio_da_qrcode(qrcode_id) -> Personaggio:
    from personaggi.models import QrCode
    from personaggi.qr_logic import validate_qr_id

    try:
        qr_pk = validate_qr_id(qrcode_id)
    except ValueError as exc:
        raise ValidationError("ID QR non valido.") from exc
    try:
        qr_code = QrCode.objects.select_related("vista").get(pk=qr_pk)
    except QrCode.DoesNotExist:
        raise ValidationError("QR non trovato.")
    if not qr_code.vista_id:
        raise ValidationError("Questo QR non è collegato a un personaggio.")
    pg = (
        Personaggio.objects.filter(inventario_ptr_id=qr_code.vista_id)
        .select_related("campagna", "proprietario", "tipologia")
        .first()
    )
    if not pg:
        raise ValidationError("Questo QR non appartiene a un personaggio.")
    return pg


def _valida_coppia_duello(sfidante: Personaggio, sfidato: Personaggio):
    if sfidato.id == sfidante.id:
        raise ValidationError("Non puoi sfidare te stesso.")
    if sfidato.campagna_id != sfidante.campagna_id:
        raise ValidationError("L'avversario deve essere nella stessa campagna.")
    if sfidato.proprietario_id == sfidante.proprietario_id:
        raise ValidationError("Non puoi sfidare un tuo altro personaggio.")
    if not personaggio_puo_accedere_carte(sfidato):
        raise ValidationError("L'avversario non può partecipare ai duelli in questa modalità.")


def _blocca_invito_duplicato(sfidante: Personaggio, sfidato: Personaggio):
    if DuelloCarte.objects.filter(
        sfidante=sfidante,
        sfidato=sfidato,
        stato=DUELLO_STATO_ATTESA,
    ).exists():
        raise ValidationError("Hai già una sfida in attesa con questo avversario.")


def lista_avversari_duello(sfidante: Personaggio) -> list[dict]:
    """Lista avversari per modalità TEST (sfida a distanza)."""
    assert_personaggio_puo_accedere_carte(sfidante)
    if get_carte_accesso_modo(sfidante.campagna) != CARTE_ACCESSO_TEST:
        return []
    qs = (
        Personaggio.objects.filter(campagna_id=sfidante.campagna_id)
        .exclude(pk=sfidante.pk)
        .exclude(proprietario_id=sfidante.proprietario_id)
        .select_related("tipologia")
        .order_by("nome")[:200]
    )
    out = []
    for pg in qs:
        if personaggio_puo_accedere_carte(pg):
            out.append({
                "id": pg.id,
                "nome": pg.nome,
                "tipologia": pg.tipologia.nome if pg.tipologia_id else None,
            })
    return out


def _mazzo_mescolato(ids: list[str]) -> list[str]:
    deck = list(ids)
    random.shuffle(deck)
    return deck


def _stato_lato_vuoto() -> dict:
    return {
        "eroi": [None, None],
        "salute_eroi": [None, None],
        "guscio_eroi": [0, 0],
        "forza_bonus_eroi": [0, 0],
        "robustezza_bonus_eroi": [0, 0],
        "oggetti": {},
        "energia": 0,
        "mana_massimo": MANA_MASSIMO_BASE,
        "turno_numero": 0,
        "fase_turno": FASE_TURNO_APERTURA,
        "turno_flags": _turno_flags_vuoti(),
        "eroi_esauriti": [False, False],
        "mazzo": [],
        "scarto": [],
        "mano": [],
    }


def _schiera_leader_in_slot(
    duello: DuelloCarte,
    personaggio: Personaggio,
    stato_lato: dict,
    leader_cp_id: str | None,
    slot: int = 0,
):
    """Il Leader è un Personaggio: occupa uno slot eroe all'apertura."""
    if not leader_cp_id:
        return
    from personaggi.carte_collezionabili_models import CartaPosseduta

    cp = CartaPosseduta.objects.select_related("carta").get(pk=leader_cp_id)
    stato_lato["eroi"][slot] = str(leader_cp_id)
    stats = stats_combattimento_carta(
        duello, personaggio, cp.carta, carta_posseduta_id=leader_cp_id,
    )
    _imposta_salute_eroe_slot(stato_lato, slot, stats["robustezza"])


def _terra_condivisa(stato_gioco: dict) -> dict | None:
    """Terra condivisa: {carta_posseduta_id, giocatore_id}."""
    raw = stato_gioco.get("terra")
    if isinstance(raw, dict) and raw.get("carta_posseduta_id"):
        return raw
    return None


def _terra_cp_id(stato_gioco: dict) -> str | None:
    terra = _terra_condivisa(stato_gioco)
    return str(terra["carta_posseduta_id"]) if terra else None


def _sostituisci_terra_condivisa(
    duello: DuelloCarte,
    personaggio: Personaggio,
    nuova_cp_id: str,
) -> None:
    """Gioca/sostituisce la terra nello slot centrale condiviso."""
    stato = duello.stato_gioco
    pg_key = _pg_key(personaggio)
    vecchia = _terra_condivisa(stato)
    if vecchia:
        old_cp = str(vecchia["carta_posseduta_id"])
        old_key = str(vecchia.get("giocatore_id") or "")
        if old_key in stato and old_cp:
            stato[old_key].setdefault("scarto", []).append(old_cp)
    stato["terra"] = {"carta_posseduta_id": str(nuova_cp_id), "giocatore_id": pg_key}


def _inizializza_stato_gioco(duello: DuelloCarte) -> dict:
    k_a = _pg_key(duello.sfidante)
    k_b = _pg_key(duello.sfidato)
    stato = {
        k_a: _stato_lato_vuoto(),
        k_b: _stato_lato_vuoto(),
        "terra": None,
        "log": [],
    }
    leaders = {
        k_a: duello.leader_sfidante_id or None,
        k_b: duello.leader_sfidato_id or None,
    }
    mazzi = {
        k_a: duello.mazzo_sfidante_ids or [],
        k_b: duello.mazzo_sfidato_ids or [],
    }
    for key in (k_a, k_b):
        pg = duello.sfidante if key == k_a else duello.sfidato
        _schiera_leader_in_slot(duello, pg, stato[key], leaders.get(key), slot=0)
        stato[key]["mazzo"] = _mazzo_mescolato(mazzi[key])
        for _ in range(MANO_INIZIALE):
            if stato[key]["mazzo"]:
                stato[key]["mano"].append(stato[key]["mazzo"].pop())
    if leaders.get(k_a):
        _append_log(stato, f"Leader schierato: {duello.sfidante.nome} (slot 0).")
    if leaders.get(k_b):
        _append_log(stato, f"Leader schierato: {duello.sfidato.nome} (slot 0).")
    return stato


def _pesca_una(stato_gioco: dict, pg_key: str):
    lato = stato_gioco[pg_key]
    if lato.get("mazzo"):
        lato.setdefault("mano", []).append(lato["mazzo"].pop())


def _pesca_fino_a(stato_gioco: dict, pg_key: str, target: int = MANO_INIZIALE):
    """Riempie la mano fino a target (apertura / test legacy)."""
    lato = stato_gioco[pg_key]
    while len(lato.get("mano") or []) < target and lato.get("mazzo"):
        _pesca_una(stato_gioco, pg_key)


def _inizio_turno(duello: DuelloCarte, pg_key: str):
    """Rinnova mana (curva 1/2/max) e resetta limiti turno."""
    lato = duello.stato_gioco[pg_key]
    personaggio = _personaggio_da_key(duello, pg_key)
    turno_numero = int(lato.get("turno_numero") or 0) + 1
    mana_max = mana_massimo_giocatore(duello, personaggio)
    lato["turno_numero"] = turno_numero
    lato["mana_massimo"] = mana_max
    lato["energia"] = mana_disponibile_per_turno(turno_numero, mana_max)
    lato["turno_flags"] = _turno_flags_vuoti()
    lato["eroi_esauriti"] = [False, False]
    lato["fase_turno"] = FASE_TURNO_APERTURA


def _inizio_turno_completo(duello: DuelloCarte, personaggio: Personaggio):
    """Inizio turno: mana, pesca 1, keyword on_turn_start."""
    pg_key = _pg_key(personaggio)
    _inizio_turno(duello, pg_key)
    _pesca_una(duello.stato_gioco, pg_key)
    _trigger_turn_keywords(duello, personaggio, "on_turn_start")


def _append_log(stato_gioco: dict, msg: str):
    stato_gioco.setdefault("log", []).append({"t": timezone.now().isoformat(), "msg": msg})


def _rimuovi_eroe_da_campo(duello: DuelloCarte, owner_pg: Personaggio, hero_slot: int) -> dict | None:
    """
    Esaurisce l'eroe nello slot: oggetti legati a scarto, eventuale EffectScript on_exhaust.
    Ritorna effect_pending se serve scelta giocatore.
    """
    from personaggi.carte_collezionabili_models import CartaPosseduta

    pg_key = _pg_key(owner_pg)
    lato = duello.stato_gioco[pg_key]
    cp_id = lato["eroi"][hero_slot]
    if not cp_id:
        return None

    lato["eroi"][hero_slot] = None
    salute = lato.setdefault("salute_eroi", [None, None])
    while len(salute) < 2:
        salute.append(None)
    salute[hero_slot] = None
    oggetti = lato.get("oggetti") or {}
    if str(hero_slot) in oggetti:
        og_id = oggetti.pop(str(hero_slot))
        lato.setdefault("scarto", []).append(og_id)
        lato["oggetti"] = oggetti

    cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id)
    from personaggi.carte_effect_engine import trigger_card_effects_on_exhaust

    if carta_e_leader_partita(duello, owner_pg, cp_id):
        lato.setdefault("mano", []).append(str(cp_id))
        _append_log(duello.stato_gioco, f"{cp.carta.nome} (Leader) torna in mano.")
        return None

    pending = trigger_card_effects_on_exhaust(
        duello,
        owner_pg,
        carta=cp.carta,
        carta_posseduta_id=str(cp_id),
        hero_slot=hero_slot,
        testo_gioco=cp.carta.testo_gioco or "",
    )
    if pending:
        _append_log(
            duello.stato_gioco,
            f"{cp.carta.nome} si esaurisce — effetto keyword in coda.",
        )
        return pending

    lato.setdefault("scarto", []).append(str(cp_id))
    _append_log(duello.stato_gioco, f"{cp.carta.nome} lascia il campo.")
    return None


def _imposta_salute_eroe_slot(lato: dict, slot: int, salute: int):
    sal = lato.setdefault("salute_eroi", [None, None])
    while len(sal) < 2:
        sal.append(None)
    sal[slot] = max(1, int(salute or 1))


def _applica_danno_eroe(duello: DuelloCarte, owner_pg: Personaggio, hero_slot: int, amount: int) -> bool:
    """Riduce salute eroe; ritorna True se l'eroe si è esaurito."""
    amount = max(0, int(amount or 0))
    if amount <= 0:
        return False
    pg_key = _pg_key(owner_pg)
    lato = duello.stato_gioco[pg_key]
    if not lato.get("eroi", [None, None])[hero_slot]:
        return False
    sal = lato.setdefault("salute_eroi", [None, None])
    while len(sal) < 2:
        sal.append(None)
    cur = sal[hero_slot]
    if cur is None:
        from personaggi.carte_collezionabili_models import CartaPosseduta

        cp = CartaPosseduta.objects.select_related("carta").get(pk=lato["eroi"][hero_slot])
        cur = int(cp.carta.salute or 1)
    sal[hero_slot] = cur - amount
    if sal[hero_slot] <= 0:
        guscio = _guscio_eroi(lato)
        if guscio[hero_slot] > 0:
            guscio[hero_slot] -= 1
            lato["guscio_eroi"] = guscio
            sal[hero_slot] = 1
            from personaggi.carte_collezionabili_models import CartaPosseduta

            cp = CartaPosseduta.objects.select_related("carta").filter(pk=lato["eroi"][hero_slot]).first()
            nome = cp.carta.nome if cp else "Eroe"
            _append_log(
                duello.stato_gioco,
                f"{nome}: un segnalino Guscio assorbe il colpo letale.",
            )
            return False
        _rimuovi_eroe_da_campo(duello, owner_pg, hero_slot)
        return True
    return False


def _duello_ha_scelta_effetto_aperta(duello: DuelloCarte) -> bool:
    stato = duello.stato_gioco or {}
    queue = stato.get("effect_queue") or []
    if not queue:
        return False
    state = queue[0]
    steps = state.get("script", {}).get("steps") or []
    idx = int(state.get("step_index") or 0)
    return idx < len(steps) and steps[idx].get("type") == "player_choice"


def _carte_snapshot(ids: list[str]) -> dict[str, dict]:
    from personaggi.carte_carta_effects import lista_abilita_manuali_carta
    from personaggi.carte_collezionabili_models import CartaPosseduta

    rows = (
        CartaPosseduta.objects.filter(pk__in=ids)
        .select_related("carta")
        .prefetch_related("carta__tags")
    )
    out = {}
    for cp in rows:
        c = cp.carta
        out[str(cp.id)] = {
            "id": str(cp.id),
            "nome": c.nome,
            "tipo": c.tipo,
            "energia": c.energia,
            "attacco": c.attacco,
            "salute": c.salute,
            "iniziativa": c.iniziativa,
            "salute_attuale": c.salute,
            "costo_gioco": c.costo_gioco,
            "testo_gioco": c.testo_gioco,
            "tags": [
                {"codice": t.codice, "nome": t.nome}
                for t in c.tags.all()
                if t.attiva
            ],
            "abilita_manuali": lista_abilita_manuali_carta(c),
        }
    return out


def serializza_duello(duello: DuelloCarte, viewer: Personaggio | None = None) -> dict:
    stato = duello.stato_gioco or {}
    cp_ids: set[str] = set()
    for key in (_pg_key(duello.sfidante), _pg_key(duello.sfidato) if duello.sfidato_id else None):
        if not key or key not in stato:
            continue
        lato = stato[key]
        cp_ids.update(lato.get("mano") or [])
        for e in lato.get("eroi") or []:
            if e:
                cp_ids.add(e)
        for oid in (lato.get("oggetti") or {}).values():
            if oid:
                cp_ids.add(oid)
    terra_id = _terra_cp_id(stato)
    if terra_id:
        cp_ids.add(terra_id)

    viewer_key = _pg_key(viewer) if viewer else None
    ruolo = None
    if viewer and viewer.id == duello.sfidante_id:
        ruolo = "sfidante"
    elif viewer and duello.sfidato_id and viewer.id == duello.sfidato_id:
        ruolo = "sfidato"

    mani = {}
    if viewer_key and viewer_key in stato:
        mani[viewer_key] = list(stato[viewer_key].get("mano") or [])
    elif viewer is None:
        for k, lato in stato.items():
            if k in ("log", "terra"):
                continue
            if isinstance(lato, dict):
                mani[k] = list(lato.get("mano") or [])

    def _campo_serializzato(pg_key: str, lato: dict) -> dict:
        pg = _personaggio_da_key(duello, pg_key)
        leader_id = _leader_carta_posseduta_id(duello, pg) if pg else None
        eroi = lato.get("eroi") or [None, None]
        return {
            "eroi": eroi,
            "eroi_is_leader": [
                bool(eroi[0] and leader_id and str(eroi[0]) == str(leader_id)),
                bool(len(eroi) > 1 and eroi[1] and leader_id and str(eroi[1]) == str(leader_id)),
            ],
            "leader_carta_posseduta_id": leader_id,
            "leader_slot": slot_leader_in_campo(lato, leader_id),
            "salute_eroi": lato.get("salute_eroi"),
            "oggetti": lato.get("oggetti"),
            "energia": lato.get("energia"),
            "mana_massimo": lato.get("mana_massimo"),
            "turno_numero": lato.get("turno_numero"),
            "turno_flags": lato.get("turno_flags"),
            "fase_turno": lato.get("fase_turno") or FASE_TURNO_APERTURA,
            "fase_turno_label": FASE_TURNO_LABEL.get(
                lato.get("fase_turno") or FASE_TURNO_APERTURA,
                "Apertura",
            ),
            "guscio_eroi": _guscio_eroi(lato),
            "bonus_leader": bonus_leader_attivi(duello, pg) if pg else [],
            "eroi_esauriti": lato.get("eroi_esauriti") or [False, False],
            "aura_primaria": _aura_primaria(duello, pg) if pg else None,
            "difensore_slot": slot_difensore(lato),
            "mazzo_count": len(lato.get("mazzo") or []),
            "scarto_count": len(lato.get("scarto") or []),
        }

    payload = {
        "id": str(duello.id),
        "stato": duello.stato,
        "avvio_tipo": duello.avvio_tipo or None,
        "modalita_partita": duello.modalita_partita,
        "posta_cr": float(duello.posta_cr or 0),
        "stato_prematch": duello.stato_prematch or {},
        "mio_ruolo": ruolo,
        "qrcode_id": duello.qr_code_id,
        "codice_invito": duello.codice_invito,
        "sfidante": {"id": duello.sfidante_id, "nome": duello.sfidante.nome},
        "sfidato": (
            {"id": duello.sfidato_id, "nome": duello.sfidato.nome}
            if duello.sfidato_id
            else None
        ),
        "turno_personaggio_id": duello.turno_personaggio_id,
        "influenza_sfidante": duello.influenza_sfidante,
        "influenza_sfidato": duello.influenza_sfidato,
        "vincitore_id": duello.vincitore_id,
        "stato_gioco": {
            "campo": {
                k: _campo_serializzato(k, v)
                for k, v in stato.items()
                if k not in ("log", "terra") and isinstance(v, dict)
            },
            "terra_condivisa": _terra_condivisa(stato),
            "mani": mani,
            "log": (stato.get("log") or [])[-20:],
        },
        "carte": _carte_snapshot(list(cp_ids)),
        "updated_at": duello.updated_at.isoformat(),
        "richiede_mia_accettazione": bool(
            viewer
            and duello.stato == DUELLO_STATO_ATTESA
            and duello.sfidato_id == viewer.id
        ),
        "in_attesa_avversario": bool(
            viewer
            and duello.stato in (DUELLO_STATO_ATTESA, DUELLO_STATO_LOBBY, DUELLO_STATO_PREMATCH)
            and duello.sfidante_id == viewer.id
            and (
                duello.stato == DUELLO_STATO_LOBBY
                or (duello.stato == DUELLO_STATO_PREMATCH and not (duello.stato_prematch or {}).get("sfidato", {}).get("pronto"))
                or (duello.stato == DUELLO_STATO_ATTESA and duello.sfidato_id)
            )
        ),
        "in_prematch": duello.stato == DUELLO_STATO_PREMATCH,
        "in_lobby": duello.stato == DUELLO_STATO_LOBBY,
    }
    if viewer and duello.stato == DUELLO_STATO_IN_CORSO:
        from personaggi.carte_effect_engine import get_open_effect_choice

        pending = get_open_effect_choice(duello, viewer)
        if pending:
            payload["effect_pending"] = pending
        queue_len = len((duello.stato_gioco or {}).get("effect_queue") or [])
        if queue_len > 1:
            payload["effect_queue_depth"] = queue_len
    return payload


def _verifica_partecipante(duello: DuelloCarte, personaggio: Personaggio):
    if duello.stato == DUELLO_STATO_LOBBY:
        if personaggio.id != duello.sfidante_id:
            raise ValidationError("Non partecipi a questo duello.")
        return
    if personaggio.id not in (duello.sfidante_id, duello.sfidato_id):
        raise ValidationError("Non partecipi a questo duello.")


def _chiudi_se_vittoria(duello: DuelloCarte):
    if duello.influenza_sfidante <= 0 and duello.influenza_sfidato > 0:
        duello.vincitore = duello.sfidato
        duello.stato = DUELLO_STATO_FINITO
    elif duello.influenza_sfidato <= 0 and duello.influenza_sfidante > 0:
        duello.vincitore = duello.sfidante
        duello.stato = DUELLO_STATO_FINITO
    elif duello.influenza_sfidante <= 0 and duello.influenza_sfidato <= 0:
        duello.stato = DUELLO_STATO_FINITO
    if duello.stato == DUELLO_STATO_FINITO and duello.posta_cr and duello.posta_cr > 0:
        from personaggi.carte_lobby_service import liquida_posta_duello

        liquida_posta_duello(duello)


@transaction.atomic
def crea_invito_duello(
    sfidante: Personaggio,
    mazzo_ids: list,
    *,
    leader_id=None,
    sfidato_id=None,
    qrcode_id=None,
) -> dict:
    assert_personaggio_puo_accedere_carte(sfidante)
    ok, errs = valida_setup_duello(mazzo_ids, leader_id, sfidante)
    if not ok:
        raise ValidationError(" ".join(errs))

    modo = get_carte_accesso_modo(sfidante.campagna)
    sfidato = None

    if modo == CARTE_ACCESSO_OPEN:
        raise ValidationError(
            "In modalità aperta usa «Apri scontro» / «Unisciti allo scontro» dalla tab Carte."
        )
    elif modo == CARTE_ACCESSO_TEST:
        if qrcode_id:
            raise ValidationError("In modalità testing usa la lista avversari, non il QR.")
        if not sfidato_id:
            raise ValidationError("Seleziona un avversario dalla lista.")
        sfidato = Personaggio.objects.filter(pk=sfidato_id).first()
        if not sfidato:
            raise ValidationError("Avversario non trovato.")
    else:
        raise ValidationError("Il gioco carte non è attivo per i duelli.")

    _valida_coppia_duello(sfidante, sfidato)
    _blocca_invito_duplicato(sfidante, sfidato)

    duello = DuelloCarte.objects.create(
        campagna=sfidante.campagna,
        sfidante=sfidante,
        sfidato=sfidato,
        mazzo_sfidante_ids=[str(x) for x in mazzo_ids],
        leader_sfidante_id=str(leader_id),
        stato=DUELLO_STATO_ATTESA,
        avvio_tipo=DUELLO_AVVIO_TEST,
        codice_invito=_genera_codice_invito(),
    )
    payload = serializza_duello(duello, sfidante)
    broadcast_duello_update(duello.id, payload)
    _notify_duello_invito(duello)
    return payload


@transaction.atomic
def accetta_duello(duello_id, sfidato: Personaggio, mazzo_ids: list, *, leader_id=None) -> dict:
    assert_personaggio_puo_accedere_carte(sfidato)
    duello = DuelloCarte.objects.select_for_update().select_related("sfidante").get(pk=duello_id)
    if duello.stato != DUELLO_STATO_ATTESA:
        raise ValidationError("Il duello non è più in attesa.")
    if duello.sfidato_id and duello.sfidato_id != sfidato.id:
        raise ValidationError("Questo invito è per un altro personaggio.")
    if duello.sfidante_id == sfidato.id:
        raise ValidationError("Non puoi accettare il tuo invito.")
    if duello.sfidante.proprietario_id == sfidato.proprietario_id:
        raise ValidationError("Non puoi duellare contro un tuo personaggio.")

    ok, errs = valida_setup_duello(mazzo_ids, leader_id, sfidato)
    if not ok:
        raise ValidationError(" ".join(errs))

    duello.sfidato = sfidato
    duello.mazzo_sfidato_ids = [str(x) for x in mazzo_ids]
    duello.leader_sfidato_id = str(leader_id)
    duello.stato = DUELLO_STATO_IN_CORSO
    duello.influenza_sfidante = INFLUENZA_INIZIALE
    duello.influenza_sfidato = INFLUENZA_INIZIALE
    duello.stato_gioco = _inizializza_stato_gioco(duello)
    primo = random.choice([duello.sfidante, duello.sfidato])
    duello.turno_personaggio = primo
    _avvia_turno_con_effetti(duello, primo)
    _append_log(duello.stato_gioco, f"Inizia {primo.nome}.")
    duello.save()

    _notify_partita_iniziata(duello)
    payload = serializza_duello(duello, sfidato)
    broadcast_duello_update(duello.id, payload)
    return payload


@transaction.atomic
def accetta_duello_per_codice(sfidato: Personaggio, codice: str, mazzo_ids: list, *, leader_id=None) -> dict:
    if get_carte_accesso_modo(sfidato.campagna) == CARTE_ACCESSO_OPEN:
        raise ValidationError(
            "In modalità aperta accetta la sfida dalla notifica o dalla tab Carte."
        )
    codice = (codice or "").strip().upper()
    duello = (
        DuelloCarte.objects.select_for_update()
        .filter(codice_invito=codice, stato=DUELLO_STATO_ATTESA)
        .select_related("sfidante")
        .first()
    )
    if not duello:
        raise ValidationError("Codice invito non valido.")
    if duello.campagna_id != sfidato.campagna_id:
        raise ValidationError("Codice valido in un'altra campagna.")
    return accetta_duello(duello.id, sfidato, mazzo_ids, leader_id=leader_id)


@transaction.atomic
def annulla_duello(duello_id, personaggio: Personaggio) -> dict:
    duello = DuelloCarte.objects.select_for_update().get(pk=duello_id)
    _verifica_partecipante(duello, personaggio)
    if duello.stato not in (
        DUELLO_STATO_ATTESA,
        DUELLO_STATO_IN_CORSO,
        DUELLO_STATO_LOBBY,
        DUELLO_STATO_PREMATCH,
    ):
        raise ValidationError("Il duello non può essere annullato.")
    duello.stato = DUELLO_STATO_ANNULLATO
    duello.save(update_fields=["stato", "updated_at"])
    payload = serializza_duello(duello, personaggio)
    broadcast_duello_update(duello.id, payload)
    return payload


def _carta_cp_in_campo_giocatore(lato: dict, stato_gioco: dict, cp_id: str) -> bool:
    cp_id = str(cp_id)
    for e in lato.get("eroi") or []:
        if e and str(e) == cp_id:
            return True
    for oid in (lato.get("oggetti") or {}).values():
        if oid and str(oid) == cp_id:
            return True
    terra_id = _terra_cp_id(stato_gioco)
    return bool(terra_id and str(terra_id) == cp_id)


def _slot_eroe_per_cp(lato: dict, cp_id: str) -> int | None:
    cp_id = str(cp_id)
    for slot, e in enumerate(lato.get("eroi") or []):
        if e and str(e) == cp_id:
            return slot
    return None


def _carte_campo_ids(lato: dict, stato_gioco: dict | None = None) -> list[str]:
    ids: list[str] = []
    for cp_id in lato.get("eroi") or []:
        if cp_id:
            ids.append(str(cp_id))
    for cp_id in (lato.get("oggetti") or {}).values():
        if cp_id:
            ids.append(str(cp_id))
    if stato_gioco:
        terra_id = _terra_cp_id(stato_gioco)
        if terra_id:
            ids.append(terra_id)
    return ids


    ids: list[str] = []
    for cp_id in lato.get("eroi") or []:
        if cp_id:
            ids.append(str(cp_id))
    for cp_id in (lato.get("oggetti") or {}).values():
        if cp_id:
            ids.append(str(cp_id))
    if stato_gioco:
        terra_id = _terra_cp_id(stato_gioco)
        if terra_id:
            ids.append(terra_id)
    return ids


def _trigger_turn_card_effects(duello: DuelloCarte, personaggio: Personaggio, event: str):
    """Accoda effect_script (keyword + carta) con trigger turno per ogni carta sul campo."""
    from personaggi.carte_collezionabili_models import CartaPosseduta
    from personaggi.carte_effect_engine import trigger_card_effects_for_event

    pg_key = _pg_key(personaggio)
    stato = duello.stato_gioco or {}
    lato = stato.get(pg_key) or {}
    cp_ids = _carte_campo_ids(lato, stato)
    if not cp_ids:
        return
    for cp in CartaPosseduta.objects.filter(pk__in=cp_ids).select_related("carta"):
        trigger_card_effects_for_event(
            duello,
            personaggio,
            cp.carta,
            cp.carta.testo_gioco or "",
            event,
            context={"carta_posseduta_id": str(cp.id), "pg_key": pg_key},
        )


def _trigger_turn_keywords(duello: DuelloCarte, personaggio: Personaggio, event: str):
    """Alias retrocompatibile."""
    _trigger_turn_card_effects(duello, personaggio, event)


def _avvia_turno_con_effetti(duello: DuelloCarte, personaggio: Personaggio):
    """Primo turno / avvio: mana, pesca 1, keyword on_turn_start."""
    _inizio_turno_completo(duello, personaggio)


def _fine_turno(duello: DuelloCarte) -> bool:
    """
    Fine turno del giocatore corrente. Ritorna False se bloccato da effetto in attesa.
    """
    cur = duello.turno_personaggio
    if not cur:
        return True
    _trigger_turn_keywords(duello, cur, "on_turn_end")
    if _duello_ha_scelta_effetto_aperta(duello):
        return False
    _cura_eroi_fine_turno(duello, duello.sfidante)
    _cura_eroi_fine_turno(duello, duello.sfidato)
    altro = _altro_pg(duello, cur)
    duello.turno_personaggio = altro
    _inizio_turno_completo(duello, altro)
    return True


@transaction.atomic
def esegui_azione_duello(duello_id, personaggio: Personaggio, azione: str, payload: dict | None = None) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    duello = DuelloCarte.objects.select_for_update().get(pk=duello_id)
    duello = DuelloCarte.objects.select_related("sfidante", "sfidato", "turno_personaggio").get(pk=duello_id)
    if duello.stato != DUELLO_STATO_IN_CORSO:
        raise ValidationError("Il duello non è in corso.")
    _verifica_partecipante(duello, personaggio)

    payload = payload or {}
    azione = (azione or "").strip().lower()
    pg_key = _pg_key(personaggio)
    alt_key = _pg_key(_altro_pg(duello, personaggio))
    manuale = duello.modalita_partita == DUELLO_MODALITA_MANUALE

    if azione == "effect_choice":
        from personaggi.carte_effect_engine import submit_effect_choice

        choice_id = payload.get("choice_id")
        cp_id = payload.get("carta_posseduta_id")
        hero_target = payload.get("hero_target")
        if not choice_id:
            raise ValidationError("choice_id richiesto.")
        submit_effect_choice(
            duello,
            personaggio,
            str(choice_id),
            cp_id,
            hero_target=str(hero_target) if hero_target else None,
        )
        _chiudi_se_vittoria(duello)
        duello.save()
        out = serializza_duello(duello, personaggio)
        broadcast_duello_update(duello.id, out)
        return out

    if manuale and azione == "imposta_influenza":
        if payload.get("influenza_sfidante") is not None:
            duello.influenza_sfidante = max(0, int(payload["influenza_sfidante"]))
        if payload.get("influenza_sfidato") is not None:
            duello.influenza_sfidato = max(0, int(payload["influenza_sfidato"]))
        _append_log(duello.stato_gioco, f"{personaggio.nome} aggiorna influenza (manuale).")
        _chiudi_se_vittoria(duello)
        duello.save()
        out = serializza_duello(duello, personaggio)
        broadcast_duello_update(duello.id, out)
        return out

    if manuale and azione == "aggiorna_stato":
        lato = duello.stato_gioco.get(pg_key) or _stato_lato_vuoto()
        if "eroi" in payload and isinstance(payload["eroi"], list):
            nuovi = list(payload["eroi"])
            vecchi = list(lato.get("eroi") or [None, None])
            while len(vecchi) < 2:
                vecchi.append(None)
            while len(nuovi) < 2:
                nuovi.append(None)
            for slot in (0, 1):
                old_id, new_id = vecchi[slot], nuovi[slot]
                if old_id and not new_id:
                    _rimuovi_eroe_da_campo(duello, personaggio, slot)
                elif new_id and str(new_id) != str(old_id or ""):
                    lato_cur = duello.stato_gioco[pg_key]
                    cp_new = str(new_id)
                    lato_cur["eroi"][slot] = cp_new
                    if cp_new in (lato_cur.get("mano") or []):
                        lato_cur["mano"].remove(cp_new)
                    from personaggi.carte_collezionabili_models import CartaPosseduta

                    cp_obj = CartaPosseduta.objects.select_related("carta").get(pk=cp_new)
                    _imposta_salute_eroe_slot(lato_cur, slot, int(cp_obj.carta.salute or 1))
            lato = duello.stato_gioco[pg_key]
            payload = {k: v for k, v in payload.items() if k != "eroi"}
        for campo in ("eroi", "oggetti", "energia", "mano", "mazzo", "scarto"):
            if campo in payload:
                lato[campo] = payload[campo]
        if "terra" in payload:
            duello.stato_gioco["terra"] = payload["terra"]
        duello.stato_gioco[pg_key] = lato
        _append_log(duello.stato_gioco, f"{personaggio.nome} aggiorna il campo (manuale).")
        duello.save()
        out = serializza_duello(duello, personaggio)
        broadcast_duello_update(duello.id, out)
        return out

    if not manuale and duello.turno_personaggio_id != personaggio.id:
        raise ValidationError("Non è il tuo turno.")

    lato = duello.stato_gioco[pg_key]

    if azione == "gioca_carta":
        cp_id = str(payload.get("carta_posseduta_id") or "")
        if cp_id not in lato["mano"]:
            raise ValidationError("Carta non in mano.")
        from personaggi.carte_collezionabili_models import CartaPosseduta

        cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id, personaggio=personaggio)
        costo = costo_effettivo_carta(duello, personaggio, cp.carta)
        if lato["energia"] < costo:
            raise ValidationError("Mana insufficiente.")

        fase = lato.get("fase_turno") or FASE_TURNO_APERTURA
        if fase == FASE_TURNO_COMBATTIMENTO:
            raise ValidationError(
                "In fase combattimento non puoi giocare carte. Passa alla fase successiva."
            )
        if fase not in (FASE_TURNO_APERTURA, FASE_TURNO_CHIUSURA):
            raise ValidationError("Non puoi giocare carte in questa fase del turno.")

        tipo = cp.carta.tipo
        flags = lato.setdefault("turno_flags", _turno_flags_vuoti())
        if tipo in (CARTA_TIPO_PERSONAGGIO, CARTA_TIPO_LUOGO, CARTA_TIPO_OGGETTO):
            if flags.get("permanente_giocato"):
                raise ValidationError("Hai già giocato un permanente questo turno.")
        elif tipo == CARTA_TIPO_EVENTO:
            if flags.get("effetto_giocato"):
                raise ValidationError("Hai già giocato un effetto questo turno.")
        if tipo == CARTA_TIPO_PERSONAGGIO:
            slot = payload.get("slot_eroe")
            if slot is None or slot not in (0, 1):
                raise ValidationError("slot_eroe richiesto (0 o 1).")
            if lato["eroi"][slot]:
                raise ValidationError("Slot eroe occupato.")
            lato["eroi"][slot] = cp_id
            stats = stats_combattimento_carta(
                duello, personaggio, cp.carta, carta_posseduta_id=cp_id,
            )
            _imposta_salute_eroe_slot(lato, int(slot), stats["robustezza"])
        elif tipo == CARTA_TIPO_OGGETTO:
            slot = payload.get("slot_eroe")
            if slot is None or slot not in (0, 1) or not lato["eroi"][slot]:
                raise ValidationError("Serve un eroe nello slot.")
            lato["oggetti"][str(slot)] = cp_id
            stats_eq = _stats_eroe_slot(duello, personaggio, lato, int(slot))
            _aggiorna_salute_eroe_da_stats(lato, int(slot), stats_eq)
        elif tipo == CARTA_TIPO_LUOGO:
            _sostituisci_terra_condivisa(duello, personaggio, cp_id)
        elif tipo == CARTA_TIPO_EVENTO:
            from personaggi.carte_effect_engine import trigger_card_effects_for_event

            testo_evt = cp.carta.testo_gioco or ""
            script_evt = trigger_card_effects_for_event(
                duello,
                personaggio,
                cp.carta,
                testo_evt,
                "on_play",
                context={"carta_posseduta_id": cp_id},
            )
            if not script_evt:
                effetto = testo_evt.lower()
                if "influenza" in effetto and "-" in effetto:
                    try:
                        danno = int("".join(c for c in effetto.split("-")[-1] if c.isdigit()) or "1")
                    except ValueError:
                        danno = 1
                    if duello.sfidante_id == personaggio.id:
                        duello.influenza_sfidato = max(0, duello.influenza_sfidato - danno)
                    else:
                        duello.influenza_sfidante = max(0, duello.influenza_sfidante - danno)
            lato["scarto"].append(cp_id)
            lato["mano"].remove(cp_id)
            lato["energia"] -= costo
            flags["effetto_giocato"] = True
            _append_log(duello.stato_gioco, f"{personaggio.nome} gioca evento {cp.carta.nome}.")
            _chiudi_se_vittoria(duello)
            if duello.stato == DUELLO_STATO_FINITO:
                duello.save()
                out = serializza_duello(duello, personaggio)
                broadcast_duello_update(duello.id, out)
                return out
            duello.save()
            out = serializza_duello(duello, personaggio)
            broadcast_duello_update(duello.id, out)
            return out
        else:
            raise ValidationError("Tipo carta non supportato.")

        lato["mano"].remove(cp_id)
        lato["energia"] -= costo
        flags["permanente_giocato"] = True
        _append_log(duello.stato_gioco, f"{personaggio.nome} gioca {cp.carta.nome}.")
        from personaggi.carte_effect_engine import trigger_card_effects_for_event

        trigger_card_effects_for_event(
            duello,
            personaggio,
            cp.carta,
            cp.carta.testo_gioco or "",
            "on_play",
            context={
                "carta_posseduta_id": cp_id,
                "slot_eroe": payload.get("slot_eroe"),
            },
        )
        _chiudi_se_vittoria(duello)
        if duello.stato == DUELLO_STATO_FINITO:
            duello.save()
            out = serializza_duello(duello, personaggio)
            broadcast_duello_update(duello.id, out)
            return out

    elif azione == "attacca":
        fase = lato.get("fase_turno") or FASE_TURNO_APERTURA
        if fase == FASE_TURNO_CHIUSURA:
            raise ValidationError("In fase finale non puoi attaccare.")
        if fase == FASE_TURNO_APERTURA:
            lato["fase_turno"] = FASE_TURNO_COMBATTIMENTO
            _append_log(duello.stato_gioco, f"{personaggio.nome}: fase combattimento.")
        slot = payload.get("slot_eroe")
        if slot is None or slot not in (0, 1):
            raise ValidationError("slot_eroe richiesto (0 o 1).")
        if _eroi_esauriti(lato)[slot]:
            raise ValidationError("Questo personaggio è esaurito e non può attaccare.")
        cp_id = lato["eroi"][slot]
        if not cp_id:
            raise ValidationError("Nessun eroe nello slot.")
        from personaggi.carte_collezionabili_models import CartaPosseduta

        cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id)
        stats_att = _stats_eroe_slot(duello, personaggio, lato, slot)
        attacco = stats_att["forza"]
        bersaglio_eroe = payload.get("bersaglio_eroe_slot")
        alt_lato = duello.stato_gioco[alt_key]
        _valida_bersaglio_difensore(alt_lato, bersaglio_eroe)
        if bersaglio_eroe is not None and bersaglio_eroe in (0, 1) and alt_lato["eroi"][bersaglio_eroe]:
            owner_eroe = _altro_pg(duello, personaggio)
            _combatti_eroi(duello, personaggio, int(slot), owner_eroe, int(bersaglio_eroe))
        else:
            if duello.sfidante_id == personaggio.id:
                duello.influenza_sfidato = max(0, duello.influenza_sfidato - attacco)
            else:
                duello.influenza_sfidante = max(0, duello.influenza_sfidante - attacco)
            _append_log(duello.stato_gioco, f"{cp.carta.nome} colpisce Influenza ({attacco}).")
        _esaurisci_eroe(lato, int(slot))
        from personaggi.carte_effect_engine import trigger_card_effects_for_event

        trigger_card_effects_for_event(
            duello,
            personaggio,
            cp.carta,
            cp.carta.testo_gioco or "",
            "on_attack",
            context={
                "carta_posseduta_id": str(cp_id),
                "slot_eroe": slot,
                "attacco": attacco,
                "bersaglio_eroe_slot": bersaglio_eroe,
                "is_leader": stats_att.get("is_leader", False),
            },
        )
        _chiudi_se_vittoria(duello)

    elif azione == "attiva_abilita":
        from personaggi.carte_collezionabili_models import CartaPosseduta
        from personaggi.carte_effect_engine import trigger_carta_manual_effect

        cp_id = str(payload.get("carta_posseduta_id") or "")
        if not cp_id:
            raise ValidationError("carta_posseduta_id richiesto.")
        if not _carta_cp_in_campo_giocatore(lato, duello.stato_gioco or {}, cp_id):
            raise ValidationError("La carta non è sul tuo campo.")
        fase = lato.get("fase_turno") or FASE_TURNO_APERTURA
        if fase == FASE_TURNO_CHIUSURA:
            raise ValidationError("In fase finale non puoi attivare abilità.")
        cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id, personaggio=personaggio)
        hero_slot = _slot_eroe_per_cp(lato, cp_id)
        pending = trigger_carta_manual_effect(
            duello,
            personaggio,
            cp.carta,
            script_index=payload.get("script_index"),
            script_codice=payload.get("script_codice"),
            carta_posseduta_id=cp_id,
            context={"slot_eroe": hero_slot} if hero_slot is not None else {},
        )
        label = cp.carta.nome
        _append_log(duello.stato_gioco, f"{personaggio.nome} attiva abilità di {label}.")
        if pending:
            duello.save()
            out = serializza_duello(duello, personaggio)
            broadcast_duello_update(duello.id, out)
            return out

    elif azione == "passa":
        if manuale:
            raise ValidationError("In modalità manuale non ci sono turni da passare.")
        if _avanza_fase_turno(duello, personaggio):
            _append_log(duello.stato_gioco, f"{personaggio.nome} passa il turno.")
            _fine_turno(duello)
    else:
        raise ValidationError("Azione non valida.")

    if duello.stato == DUELLO_STATO_IN_CORSO:
        _chiudi_se_vittoria(duello)
    duello.save()
    out = serializza_duello(duello, personaggio)
    broadcast_duello_update(duello.id, out)
    return out


def lista_duelli_personaggio(personaggio: Personaggio) -> list[dict]:
    if not personaggio.campagna_id:
        return []
    qs = (
        DuelloCarte.objects.filter(campagna_id=personaggio.campagna_id)
        .filter(Q(sfidante=personaggio) | Q(sfidato=personaggio))
        .exclude(stato=DUELLO_STATO_ANNULLATO)
        .select_related("sfidante", "sfidato", "vincitore")
        .order_by("-updated_at")[:30]
    )
    return [serializza_duello(d, personaggio) for d in qs]


def get_duello_per_giocatore(duello_id, personaggio: Personaggio) -> dict:
    duello = DuelloCarte.objects.select_related("sfidante", "sfidato", "vincitore").get(pk=duello_id)
    allowed_ids = {duello.sfidante_id}
    if duello.sfidato_id:
        allowed_ids.add(duello.sfidato_id)
    elif duello.stato != DUELLO_STATO_LOBBY:
        pass
    if personaggio.id not in allowed_ids:
        raise ValidationError("Non autorizzato.")
    return serializza_duello(duello, personaggio)


def _notify_partita_iniziata(duello: DuelloCarte):
    """Notifica entrambi i giocatori che la partita live è iniziata."""
    if not duello.sfidato_id or duello.stato != DUELLO_STATO_IN_CORSO:
        return
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    for pg_id in (duello.sfidante_id, duello.sfidato_id):
        avversario = duello.sfidato if pg_id == duello.sfidante_id else duello.sfidante
        async_to_sync(channel_layer.group_send)(
            "kor35_notifications",
            {
                "type": "send_notification",
                "message": {
                    "action": "DUELLO_INIZIO",
                    "duello_id": str(duello.id),
                    "destinatario_personaggio_id": pg_id,
                    "avversario_nome": avversario.nome,
                },
            },
        )


def _notify_duello_invito(duello: DuelloCarte):
    if not duello.sfidato_id:
        return
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {
            "type": "send_notification",
            "message": {
                "action": "DUELLO_INVITO",
                "duello_id": str(duello.id),
                "codice_invito": duello.codice_invito,
                "sfidante_nome": duello.sfidante.nome,
                "destinatario_personaggio_id": duello.sfidato_id,
            },
        },
    )
