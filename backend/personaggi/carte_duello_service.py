"""
Duello carte live — stato partita, turni, sincronizzazione.
"""
from __future__ import annotations

import random
import secrets
import string

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
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
    valida_mazzo_duello,
)
from personaggi.carte_duello_ws import broadcast_duello_update
from personaggi.models import Personaggio

ENERGIA_MAX = 5
MANO_MAX = 4
MAX_EROI = 2


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
        "luogo": None,
        "eroi": [None, None],
        "salute_eroi": [None, None],
        "oggetti": {},
        "energia": 0,
        "mazzo": [],
        "scarto": [],
        "mano": [],
    }


def _inizializza_stato_gioco(duello: DuelloCarte) -> dict:
    k_a = _pg_key(duello.sfidante)
    k_b = _pg_key(duello.sfidato)
    stato = {
        k_a: _stato_lato_vuoto(),
        k_b: _stato_lato_vuoto(),
        "log": [],
    }
    stato[k_a]["mazzo"] = _mazzo_mescolato(duello.mazzo_sfidante_ids or [])
    stato[k_b]["mazzo"] = _mazzo_mescolato(duello.mazzo_sfidato_ids or [])
    for key in (k_a, k_b):
        for _ in range(MANO_MAX):
            if stato[key]["mazzo"]:
                stato[key]["mano"].append(stato[key]["mazzo"].pop())
    return stato


def _pesca_fino_a(stato_gioco: dict, pg_key: str, target: int = MANO_MAX):
    lato = stato_gioco[pg_key]
    while len(lato["mano"]) < target and lato["mazzo"]:
        lato["mano"].append(lato["mazzo"].pop())


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
    from personaggi.carte_effect_engine import trigger_keyword_effects_on_exhaust

    pending = trigger_keyword_effects_on_exhaust(
        duello,
        owner_pg,
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
    from personaggi.carte_collezionabili_models import CartaPosseduta

    rows = (
        CartaPosseduta.objects.filter(pk__in=ids)
        .select_related("carta")
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
            "salute_attuale": c.salute,
            "costo_gioco": c.costo_gioco,
            "testo_gioco": c.testo_gioco,
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
        if lato.get("luogo"):
            cp_ids.add(lato["luogo"])
        for oid in (lato.get("oggetti") or {}).values():
            if oid:
                cp_ids.add(oid)

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
            if k in ("log",):
                continue
            if isinstance(lato, dict):
                mani[k] = list(lato.get("mano") or [])

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
                k: {
                    "luogo": v.get("luogo"),
                    "eroi": v.get("eroi"),
                    "salute_eroi": v.get("salute_eroi"),
                    "oggetti": v.get("oggetti"),
                    "energia": v.get("energia"),
                    "mazzo_count": len(v.get("mazzo") or []),
                    "scarto_count": len(v.get("scarto") or []),
                }
                for k, v in stato.items()
                if k != "log" and isinstance(v, dict)
            },
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
    sfidato_id=None,
    qrcode_id=None,
) -> dict:
    assert_personaggio_puo_accedere_carte(sfidante)
    ok, errs = valida_mazzo_duello(mazzo_ids, sfidante)
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
        stato=DUELLO_STATO_ATTESA,
        avvio_tipo=DUELLO_AVVIO_TEST,
        codice_invito=_genera_codice_invito(),
    )
    payload = serializza_duello(duello, sfidante)
    broadcast_duello_update(duello.id, payload)
    _notify_duello_invito(duello)
    return payload


@transaction.atomic
def accetta_duello(duello_id, sfidato: Personaggio, mazzo_ids: list) -> dict:
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

    ok, errs = valida_mazzo_duello(mazzo_ids, sfidato)
    if not ok:
        raise ValidationError(" ".join(errs))

    duello.sfidato = sfidato
    duello.mazzo_sfidato_ids = [str(x) for x in mazzo_ids]
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
def accetta_duello_per_codice(sfidato: Personaggio, codice: str, mazzo_ids: list) -> dict:
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
    return accetta_duello(duello.id, sfidato, mazzo_ids)


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


def _personaggio_da_key(duello: DuelloCarte, pg_key: str) -> Personaggio | None:
    if str(duello.sfidante_id) == str(pg_key):
        return duello.sfidante
    if duello.sfidato_id and str(duello.sfidato_id) == str(pg_key):
        return duello.sfidato
    return None


def _carte_campo_ids(lato: dict) -> list[str]:
    ids: list[str] = []
    for cp_id in lato.get("eroi") or []:
        if cp_id:
            ids.append(str(cp_id))
    if lato.get("luogo"):
        ids.append(str(lato["luogo"]))
    for cp_id in (lato.get("oggetti") or {}).values():
        if cp_id:
            ids.append(str(cp_id))
    return ids


def _trigger_turn_keywords(duello: DuelloCarte, personaggio: Personaggio, event: str):
    """Accoda effect_script con trigger turno per ogni carta sul campo (catena FIFO)."""
    from personaggi.carte_collezionabili_models import CartaPosseduta
    from personaggi.carte_effect_engine import trigger_keyword_effects_for_event

    pg_key = _pg_key(personaggio)
    lato = (duello.stato_gioco or {}).get(pg_key) or {}
    cp_ids = _carte_campo_ids(lato)
    if not cp_ids:
        return
    for cp in CartaPosseduta.objects.filter(pk__in=cp_ids).select_related("carta"):
        trigger_keyword_effects_for_event(
            duello,
            personaggio,
            cp.carta.testo_gioco or "",
            event,
            context={"carta_posseduta_id": str(cp.id), "pg_key": pg_key},
        )


def _avvia_turno_con_effetti(duello: DuelloCarte, personaggio: Personaggio):
    """Energia turno + keyword on_turn_start sul campo."""
    _inizio_turno(duello, _pg_key(personaggio))
    _trigger_turn_keywords(duello, personaggio, "on_turn_start")


def _inizio_turno(duello: DuelloCarte, pg_key: str):
    lato = duello.stato_gioco[pg_key]
    lato["energia"] = min(ENERGIA_MAX, int(lato.get("energia") or 0) + 1)


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
    altro = _altro_pg(duello, cur)
    duello.turno_personaggio = altro
    _inizio_turno(duello, _pg_key(altro))
    _pesca_fino_a(duello.stato_gioco, _pg_key(altro))
    _trigger_turn_keywords(duello, altro, "on_turn_start")
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
        for campo in ("luogo", "eroi", "oggetti", "energia", "mano", "mazzo", "scarto"):
            if campo in payload:
                lato[campo] = payload[campo]
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
        costo = int(cp.carta.costo_gioco or 0)
        if lato["energia"] < costo:
            raise ValidationError("Energia insufficiente.")

        tipo = cp.carta.tipo
        if tipo == CARTA_TIPO_PERSONAGGIO:
            slot = payload.get("slot_eroe")
            if slot is None or slot not in (0, 1):
                raise ValidationError("slot_eroe richiesto (0 o 1).")
            if lato["eroi"][slot]:
                raise ValidationError("Slot eroe occupato.")
            lato["eroi"][slot] = cp_id
            _imposta_salute_eroe_slot(lato, int(slot), int(cp.carta.salute or 1))
        elif tipo == CARTA_TIPO_OGGETTO:
            slot = payload.get("slot_eroe")
            if slot is None or slot not in (0, 1) or not lato["eroi"][slot]:
                raise ValidationError("Serve un eroe nello slot.")
            lato["oggetti"][str(slot)] = cp_id
        elif tipo == CARTA_TIPO_LUOGO:
            lato["luogo"] = cp_id
        elif tipo == CARTA_TIPO_EVENTO:
            from personaggi.carte_effect_engine import trigger_keyword_effect_for_event

            testo_evt = cp.carta.testo_gioco or ""
            script_evt = trigger_keyword_effect_for_event(
                duello,
                personaggio,
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
            _append_log(duello.stato_gioco, f"{personaggio.nome} gioca evento {cp.carta.nome}.")
            _chiudi_se_vittoria(duello)
            if duello.stato == DUELLO_STATO_FINITO:
                duello.save()
                out = serializza_duello(duello, personaggio)
                broadcast_duello_update(duello.id, out)
                return out
            if not manuale and not _duello_ha_scelta_effetto_aperta(duello):
                _fine_turno(duello)
            duello.save()
            out = serializza_duello(duello, personaggio)
            broadcast_duello_update(duello.id, out)
            return out
        else:
            raise ValidationError("Tipo carta non supportato.")

        lato["mano"].remove(cp_id)
        lato["energia"] -= costo
        _append_log(duello.stato_gioco, f"{personaggio.nome} gioca {cp.carta.nome}.")
        from personaggi.carte_effect_engine import trigger_keyword_effect_for_event

        trigger_keyword_effect_for_event(
            duello,
            personaggio,
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
        if not manuale and not _duello_ha_scelta_effetto_aperta(duello):
            _fine_turno(duello)

    elif azione == "attacca":
        slot = payload.get("slot_eroe")
        if slot is None or slot not in (0, 1):
            raise ValidationError("slot_eroe richiesto.")
        cp_id = lato["eroi"][slot]
        if not cp_id:
            raise ValidationError("Nessun eroe nello slot.")
        from personaggi.carte_collezionabili_models import CartaPosseduta

        cp = CartaPosseduta.objects.select_related("carta").get(pk=cp_id)
        attacco = int(cp.carta.attacco or 1)
        bersaglio_eroe = payload.get("bersaglio_eroe_slot")
        alt_lato = duello.stato_gioco[alt_key]
        if bersaglio_eroe is not None and bersaglio_eroe in (0, 1) and alt_lato["eroi"][bersaglio_eroe]:
            owner_eroe = _altro_pg(duello, personaggio)
            esaurito = _applica_danno_eroe(duello, owner_eroe, int(bersaglio_eroe), attacco)
            if esaurito:
                _append_log(duello.stato_gioco, f"{cp.carta.nome} esaurisce un eroe avversario.")
            else:
                sal = duello.stato_gioco[_pg_key(owner_eroe)]["salute_eroi"][int(bersaglio_eroe)]
                _append_log(
                    duello.stato_gioco,
                    f"{cp.carta.nome} colpisce eroe avversario ({attacco} danni, salute {sal}).",
                )
        else:
            if duello.sfidante_id == personaggio.id:
                duello.influenza_sfidato = max(0, duello.influenza_sfidato - attacco)
            else:
                duello.influenza_sfidante = max(0, duello.influenza_sfidante - attacco)
            _append_log(duello.stato_gioco, f"{cp.carta.nome} colpisce Influenza ({attacco}).")
        from personaggi.carte_effect_engine import trigger_keyword_effect_for_event

        trigger_keyword_effect_for_event(
            duello,
            personaggio,
            cp.carta.testo_gioco or "",
            "on_attack",
            context={
                "carta_posseduta_id": str(cp_id),
                "slot_eroe": slot,
                "attacco": attacco,
                "bersaglio_eroe_slot": bersaglio_eroe,
            },
        )
        _chiudi_se_vittoria(duello)
        if duello.stato == DUELLO_STATO_IN_CORSO and not manuale and not _duello_ha_scelta_effetto_aperta(duello):
            _fine_turno(duello)

    elif azione == "passa":
        if manuale:
            raise ValidationError("In modalità manuale non ci sono turni da passare.")
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
