"""
Motore compattatore: energia da sottosistema Z, compressione/decompressione 2:1, risonanza.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from .componenti_nave_constants import AURA_COMPONENTI_SIGLA
from .componenti_stiva import (
    azzera_stiva_colori,
    azzera_stiva_tranne_colori,
    build_stiva_payload,
    colori_presenti_in_stiva,
    consuma_mattoni_stiva,
    indice_colore_componente,
    mattone_per_indice_colore,
    staff_modifica_stiva,
    _aggiungi_mattone,
    _colori_componente_ordinati,
)


def _ring_next(indice: int) -> int:
    return (int(indice) + 1) % 10


def _ring_prev(indice: int) -> int:
    return (int(indice) - 1) % 10


def _sottosistema_compattatore():
    from .models import SottosistemaNave

    return (
        SottosistemaNave.objects.filter(attivo=True, tipo="compattatore")
        .order_by("codice")
        .first()
    )


def _livello_compattatore() -> int:
    from .stato_nave import stato_operativo_sottosistema

    ss = _sottosistema_compattatore()
    if ss is None:
        return 0
    stato = stato_operativo_sottosistema(ss, None)
    if stato is None or not getattr(stato, "online", True):
        return 0
    if getattr(stato, "espulso", False):
        return 0
    return max(0, min(9, int(getattr(stato, "livello_attuale", 0) or 0)))


def _stato_compattatore():
    from .models import CompattatoreStatoNave

    return CompattatoreStatoNave.get_solo()


def tick_energia_compattatore() -> None:
    """Chiamato a fine tick pilota: accumula energia in base al livello Z."""
    livello = _livello_compattatore()
    if livello <= 0:
        return
    stato = _stato_compattatore()
    stato.energia_accumulata = float(stato.energia_accumulata or 0) + float(livello)
    stato.save(update_fields=["energia_accumulata", "updated_at"])


def _operazione_disponibile() -> bool:
    cfg = __import__("pilotaggio.models", fromlist=["PilotRuntimeConfig"]).PilotRuntimeConfig.get_solo()
    if not cfg.compattatore_console_abilitata:
        return False
    if _livello_compattatore() <= 0:
        return False
    stato = _stato_compattatore()
    return float(stato.energia_accumulata or 0) >= 9.0


def _consuma_energia_operazione() -> None:
    stato = _stato_compattatore()
    stato.energia_accumulata = max(0.0, float(stato.energia_accumulata or 0) - 9.0)
    stato.save(update_fields=["energia_accumulata", "updated_at"])


def _mattone_stiva(mattone_id):
    from personaggi.models import Mattone

    return Mattone.objects.filter(pk=mattone_id, aura__sigla=AURA_COMPONENTI_SIGLA).first()


def build_compattatore_state_payload() -> dict:
    from .models import PilotRuntimeConfig
    from .stato_nave import stato_operativo_sottosistema

    cfg = PilotRuntimeConfig.get_solo()
    ss = _sottosistema_compattatore()
    livello = _livello_compattatore()
    stato = _stato_compattatore()
    operativo = bool(cfg.compattatore_console_abilitata and ss is not None and livello > 0)
    if ss is not None:
        st = stato_operativo_sottosistema(ss, None)
        if st is None or not st.online or getattr(st, "espulso", False):
            operativo = False

    return {
        "abilitato": bool(cfg.compattatore_console_abilitata),
        "operativo": operativo,
        "sottosistema": {"id": str(ss.pk), "codice": ss.codice, "nome": ss.nome} if ss else None,
        "livello_energia": livello,
        "energia_accumulata": float(stato.energia_accumulata or 0),
        "energia_soglia_operazione": 9.0,
        "operazione_disponibile": _operazione_disponibile(),
        "quantico_abilitato": bool(cfg.compattatore_quantico_abilitato),
        "quantico_disponibile": bool(
            cfg.compattatore_quantico_abilitato and _operazione_disponibile()
        ),
        "stiva": build_stiva_payload(),
    }


@transaction.atomic
def operazione_compressione(*, mattone_id: str, quantita: int = 2) -> dict:
    if quantita != 2:
        raise ValueError("La compressione richiede esattamente 2 unità.")
    if not _operazione_disponibile():
        raise ValueError("Compattatore non operativo o energia insufficiente.")

    src = _mattone_stiva(mattone_id)
    if src is None or src.indice_componente is None:
        raise ValueError("Mattone sorgente non valido.")
    dst_indice = _ring_next(src.indice_componente)
    from personaggi.models import Mattone

    dst = Mattone.objects.filter(
        aura__sigla=AURA_COMPONENTI_SIGLA,
        indice_componente=dst_indice,
    ).first()
    if dst is None:
        raise ValueError("Mattone destinazione non trovato nel catalogo.")

    consuma_mattoni_stiva([{"mattone_id": str(src.pk), "quantita": 2}])
    staff_modifica_stiva(mattone_id=str(dst.pk), delta=1)
    _consuma_energia_operazione()
    return build_compattatore_state_payload()


@transaction.atomic
def operazione_decompressione(*, mattone_id: str, quantita: int = 1) -> dict:
    if quantita != 1:
        raise ValueError("La decompressione richiede 1 unità.")
    if not _operazione_disponibile():
        raise ValueError("Compattatore non operativo o energia insufficiente.")

    src = _mattone_stiva(mattone_id)
    if src is None or src.indice_componente is None:
        raise ValueError("Mattone sorgente non valido.")
    dst_indice = _ring_prev(src.indice_componente)
    from personaggi.models import Mattone

    dst = Mattone.objects.filter(
        aura__sigla=AURA_COMPONENTI_SIGLA,
        indice_componente=dst_indice,
    ).first()
    if dst is None:
        raise ValueError("Mattone destinazione non trovato nel catalogo.")

    consuma_mattoni_stiva([{"mattone_id": str(src.pk), "quantita": 1}])
    staff_modifica_stiva(mattone_id=str(dst.pk), delta=2)
    _consuma_energia_operazione()
    return build_compattatore_state_payload()


def _ring_offset(indice: int, delta: int) -> int:
    return (int(indice) + int(delta)) % 10


def _indici_rimanenti(indice_input: int) -> List[int]:
    usati = {
        indice_input,
        _ring_offset(indice_input, -1),
        _ring_offset(indice_input, 1),
        _ring_offset(indice_input, -2),
        _ring_offset(indice_input, 2),
    }
    return [i for i in range(10) if i not in usati]


def _roll_slot_colore(
    *,
    indice_input: int,
    glitch_slot: bool,
    quota_altri_pct: float,
    rng: random.Random,
) -> Tuple[str, Optional[int]]:
    """
    Ritorna (tipo_esito, indice_colore).
    tipo_esito: glitch | stesso | adiacente | distanza2 | anomalia
    """
    r = rng.random() * 100.0
    if glitch_slot:
        if r < 2.0:
            return "glitch", None
        soglia_stesso = 2.0 + 35.0
        soglia_adj_sx = soglia_stesso + 20.0
        soglia_adj_dx = soglia_adj_sx + 20.0
        soglia_d2_sx = soglia_adj_dx + 10.0
        soglia_d2_dx = soglia_d2_sx + 10.0
    else:
        soglia_stesso = 35.0
        soglia_adj_sx = soglia_stesso + 20.0
        soglia_adj_dx = soglia_adj_sx + 20.0
        soglia_d2_sx = soglia_adj_dx + 10.0
        soglia_d2_dx = soglia_d2_sx + 10.0

    soglia_altri = soglia_d2_dx + float(quota_altri_pct)

    if r < soglia_stesso:
        return "stesso", indice_input
    if r < soglia_adj_sx:
        return "adiacente", _ring_offset(indice_input, -1)
    if r < soglia_adj_dx:
        return "adiacente", _ring_offset(indice_input, 1)
    if r < soglia_d2_sx:
        return "distanza2", _ring_offset(indice_input, -2)
    if r < soglia_d2_dx:
        return "distanza2", _ring_offset(indice_input, 2)
    if r < soglia_altri:
        altri = _indici_rimanenti(indice_input)
        if not altri:
            return "stesso", indice_input
        return "anomalia", rng.choice(altri)
    return "stesso", indice_input


def _applica_glitch(slot: str, rng: random.Random) -> dict:
    colori = _colori_componente_ordinati()
    if len(colori) < 2:
        return {"slot": slot, "tipo": "glitch", "dettaglio": "catalogo_colori_insufficiente"}

    scelti = rng.sample(colori, 2)
    ids = [c.pk for c in scelti]
    if slot == "A":
        rimossi = azzera_stiva_colori(ids)
        return {
            "slot": slot,
            "tipo": "glitch",
            "nome": "Sbalzo di Risonanza",
            "colori_colpiti": [c.sigla or c.nome for c in scelti],
            "unita_rimosse": rimossi,
        }

    rimossi = azzera_stiva_tranne_colori(ids)
    return {
        "slot": slot,
        "tipo": "glitch",
        "nome": "Inversione Quantistica",
        "colori_preservati": [c.sigla or c.nome for c in scelti],
        "unita_rimosse": rimossi,
    }


def _serializza_slot(
  slot: str,
  tipo_esito: str,
  indice_colore: Optional[int],
  colore_input_indice: int,
) -> dict:
    if tipo_esito == "glitch":
        return {"slot": slot, "esito": "glitch"}

    colore = _colori_componente_ordinati()[indice_colore]
    mattone = mattone_per_indice_colore(indice_colore)
    return {
        "slot": slot,
        "esito": tipo_esito,
        "indice_colore": indice_colore,
        "colore_id": str(colore.pk),
        "colore_sigla": colore.sigla,
        "colore_nome": colore.nome,
        "mattone_id": str(mattone.pk) if mattone else None,
        "stesso_input": indice_colore == colore_input_indice,
    }


@transaction.atomic
def operazione_risonanza(*, mattone_id: str, rng: Optional[random.Random] = None) -> dict:
    if not _operazione_disponibile():
        raise ValueError("Compattatore non operativo o energia insufficiente.")

    src = _mattone_stiva(mattone_id)
    if src is None or src.indice_componente is None or src.caratteristica_associata is None:
        raise ValueError("Mattone sorgente non valido.")

    rng = rng or random.Random()
    colore_input_indice = indice_colore_componente(src.caratteristica_associata)
    colore_input_id = src.caratteristica_associata_id
    presenti_prima = colori_presenti_in_stiva()

    consuma_mattoni_stiva([{"mattone_id": str(src.pk), "quantita": 1}])
    _consuma_energia_operazione()

    glitch_eventi: List[dict] = []
    slot_risultati: List[dict] = []
    premi_generati: List[dict] = []
    bonus: List[dict] = []

    for slot, glitch_slot, quota_altri in (
        ("A", True, 3.0),
        ("B", False, 5.0),
    ):
        tipo_esito, indice_colore = _roll_slot_colore(
            indice_input=colore_input_indice,
            glitch_slot=glitch_slot,
            quota_altri_pct=quota_altri,
            rng=rng,
        )
        if tipo_esito == "glitch":
            ev = _applica_glitch(slot, rng)
            glitch_eventi.append(ev)
            slot_risultati.append({"slot": slot, "esito": "glitch", "nome": ev.get("nome")})
            continue

        info = _serializza_slot(slot, tipo_esito, indice_colore, colore_input_indice)
        slot_risultati.append(info)
        mattone = mattone_per_indice_colore(indice_colore)
        if mattone:
            _aggiungi_mattone(mattone, 1)
            premi_generati.append(info)

    if not glitch_eventi:
        if len(slot_risultati) == 2:
            a, b = slot_risultati[0], slot_risultati[1]
            if a.get("colore_id") and a.get("colore_id") == b.get("colore_id"):
                m = mattone_per_indice_colore(a["indice_colore"])
                if m:
                    _aggiungi_mattone(m, 1)
                    bonus.append({"tipo": "risonanza_additiva", "mattone_id": str(m.pk), "quantita": 1})

        for info in slot_risultati:
            cid = info.get("colore_id")
            if cid and cid in presenti_prima:
                m = mattone_per_indice_colore(info["indice_colore"])
                if m:
                    _aggiungi_mattone(m, 1)
                    bonus.append(
                        {
                            "tipo": "riproduzione_quantistica",
                            "mattone_id": str(m.pk),
                            "quantita": 1,
                            "slot": info["slot"],
                        }
                    )
            if info.get("stesso_input"):
                m = mattone_per_indice_colore(info["indice_colore"])
                if m:
                    _aggiungi_mattone(m, 1)
                    bonus.append(
                        {
                            "tipo": "eco_input",
                            "mattone_id": str(m.pk),
                            "quantita": 1,
                            "slot": info["slot"],
                        }
                    )

    payload = build_compattatore_state_payload()
    payload["risonanza"] = {
        "input": {
            "mattone_id": str(src.pk),
            "indice_colore": colore_input_indice,
            "colore_id": str(colore_input_id),
        },
        "slot_a": slot_risultati[0] if len(slot_risultati) > 0 else None,
        "slot_b": slot_risultati[1] if len(slot_risultati) > 1 else None,
        "glitch": glitch_eventi,
        "bonus": bonus,
        "premi": premi_generati,
    }
    return payload


@transaction.atomic
def operazione_compattatore_quantico(
    *,
    nome_oggetto: Optional[str] = None,
    qr_id: Optional[str] = None,
    personaggio_id: Optional[str] = None,
) -> dict:
    from personaggi.models import Personaggio, QrCode

    from .compattatore_quantico import (
        consuma_oggetto_da_qr_inventario,
        genera_componenti_da_nome,
        risolvi_nome_da_qr,
    )
    from .models import PilotRuntimeConfig

    cfg = PilotRuntimeConfig.get_solo()
    if not cfg.compattatore_quantico_abilitato:
        raise ValueError(
            "Compattatore Quantico disabilitato — attivare da staff per l'evento."
        )
    if not _operazione_disponibile():
        raise ValueError("Compattatore non operativo o energia insufficiente.")

    oggetto_eliminato = None
    nome_finale = (nome_oggetto or "").strip()

    if qr_id:
        qr = QrCode.objects.select_related("vista").filter(pk=str(qr_id).strip()).first()
        if qr is None:
            raise ValueError("QR non trovato.")
        if personaggio_id:
            pg = Personaggio.objects.filter(pk=personaggio_id).first()
            if pg is None:
                raise ValueError("Personaggio non valido.")
            oggetto_eliminato = consuma_oggetto_da_qr_inventario(personaggio=pg, qr_code=qr)
            nome_finale = oggetto_eliminato
        else:
            nome_finale = risolvi_nome_da_qr(qr)

    if not nome_finale:
        raise ValueError("Fornire nome_oggetto (testo) oppure qr_id (con personaggio_id per eliminare l'oggetto).")

    generazione = genera_componenti_da_nome(nome_finale)
    for alloc in generazione["allocazioni"]:
        staff_modifica_stiva(mattone_id=alloc["mattone_id"], delta=int(alloc["quantita"]))

    _consuma_energia_operazione()
    payload = build_compattatore_state_payload()
    payload["quantico"] = {
        **generazione,
        "nome_input": nome_finale,
        "oggetto_eliminato": oggetto_eliminato,
        "modalita": "qr" if qr_id else "testo",
    }
    return payload
