"""
Minigiochi QR: sliding puzzle, memory, rotate tiles.
Gate sulla scansione + timer opzionale con esiti configurabili.
"""
from __future__ import annotations

import random
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from personaggi.requisiti_accesso import (
    gruppo_requisiti_soddisfatto,
    personaggio_soddisfa_requisiti,
)

MINIGIOCO_TIPO_SLIDING = "sliding_puzzle"
MINIGIOCO_TIPO_MEMORY = "memory"
MINIGIOCO_TIPO_ROTATE = "rotate_tiles"

MINIGIOCO_TIPI = (
    MINIGIOCO_TIPO_SLIDING,
    MINIGIOCO_TIPO_MEMORY,
    MINIGIOCO_TIPO_ROTATE,
)

TIMER_SCADENZA_ATTIVA = "attiva_qr"
TIMER_SCADENZA_BLOCCA = "blocca_qr"
TIMER_SCADENZA_RESET = "reset_minigioco"

SESSIONE_IN_CORSO = "in_corso"
SESSIONE_COMPLETATO = "completato"
SESSIONE_SCADUTO_ATTIVA = "scaduto_attiva"
SESSIONE_SCADUTO_BLOCCA = "scaduto_blocca"
SESSIONE_SCADUTO_RESET = "scaduto_reset"

STATI_SBLocco = frozenset({SESSIONE_COMPLETATO, SESSIONE_SCADUTO_ATTIVA})

_SLIDING_GRID = {1: 2, 2: 3, 3: 4, 4: 5}
_ROTATE_GRID = {1: 2, 2: 3, 3: 4, 4: 5}
_MEMORY_GRID = {1: (2, 2), 2: (3, 4), 3: (4, 4), 4: (4, 5)}


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def grid_size(tipo: str, difficolta: int) -> Tuple[int, int]:
    d = max(1, min(4, int(difficolta or 2)))
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return _MEMORY_GRID[d]
    n = _SLIDING_GRID[d] if tipo == MINIGIOCO_TIPO_SLIDING else _ROTATE_GRID[d]
    return n, n


def _sliding_neighbors(idx: int, size: int) -> List[int]:
    r, c = divmod(idx, size)
    out = []
    if r > 0:
        out.append((r - 1) * size + c)
    if r < size - 1:
        out.append((r + 1) * size + c)
    if c > 0:
        out.append(r * size + (c - 1))
    if c < size - 1:
        out.append(r * size + (c + 1))
    return out


def generate_sliding_state(size: int, seed: int) -> List[int]:
    """Lista indici pezzi; ultimo valore = buco (size*size-1)."""
    total = size * size
    tiles = list(range(total))
    rng = _rng(seed)
    empty = total - 1
    moves = size * size * 12
    for _ in range(moves):
        opts = [i for i in range(total) if i != empty and empty in _sliding_neighbors(i, size)]
        if not opts:
            continue
        pick = rng.choice(opts)
        tiles[empty], tiles[pick] = tiles[pick], tiles[empty]
        empty = pick
    return tiles


def generate_memory_state(cols: int, rows: int, seed: int) -> Dict[str, Any]:
    total = cols * rows
    if total % 2 != 0:
        raise ValueError("Memory richiede un numero pari di celle.")
    pair_count = total // 2
    symbols = list(range(pair_count))
    deck = symbols + symbols
    rng = _rng(seed)
    rng.shuffle(deck)
    return {"cols": cols, "rows": rows, "cards": deck, "matched": []}


def generate_rotate_state(size: int, seed: int) -> List[int]:
    """Rotazioni 0-3 per cella; almeno una cella non a zero."""
    rng = _rng(seed)
    rotations = [rng.randint(0, 3) for _ in range(size * size)]
    if all(r == 0 for r in rotations):
        rotations[rng.randrange(size * size)] = rng.choice([1, 2, 3])
    return rotations


def generate_game_state(tipo: str, difficolta: int, seed: int) -> Dict[str, Any]:
    cols, rows = grid_size(tipo, difficolta)
    if tipo == MINIGIOCO_TIPO_SLIDING:
        size = cols
        return {"tipo": tipo, "size": size, "tiles": generate_sliding_state(size, seed)}
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return {"tipo": tipo, **generate_memory_state(cols, rows, seed)}
    if tipo == MINIGIOCO_TIPO_ROTATE:
        size = cols
        return {"tipo": tipo, "size": size, "rotations": generate_rotate_state(size, seed)}
    raise ValueError(f"Tipo minigioco sconosciuto: {tipo}")


def verify_sliding(tiles: List[int], size: int) -> bool:
    expected = list(range(size * size))
    return list(tiles) == expected


def verify_memory(cards: List[int], matched: List[int], cols: int, rows: int) -> bool:
    total = cols * rows
    if len(cards) != total:
        return False
    matched_set = set(matched or [])
    if len(matched_set) != total:
        return False
    return all(i in matched_set for i in range(total))


def verify_rotate(rotations: List[int], size: int) -> bool:
    return len(rotations) == size * size and all(int(r) % 4 == 0 for r in rotations)


def verify_solution(tipo: str, difficolta: int, client_state: dict) -> bool:
    if not isinstance(client_state, dict):
        return False
    cols, rows = grid_size(tipo, difficolta)
    if tipo == MINIGIOCO_TIPO_SLIDING:
        size = cols
        return verify_sliding(client_state.get("tiles") or [], size)
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return verify_memory(
            client_state.get("cards") or [],
            client_state.get("matched") or [],
            cols,
            rows,
        )
    if tipo == MINIGIOCO_TIPO_ROTATE:
        size = cols
        return verify_rotate(client_state.get("rotations") or [], size)
    return False


def tipi_pool(config) -> List[str]:
    """Tipi di gioco ammessi per l'estrazione casuale."""
    raw = getattr(config, "tipi_abilitati", None) or []
    if isinstance(raw, list) and raw:
        tipi = [t for t in raw if t in MINIGIOCO_TIPI]
        if tipi:
            return tipi
    legacy = getattr(config, "tipo", None)
    if legacy in MINIGIOCO_TIPI:
        return [legacy]
    return list(MINIGIOCO_TIPI)


def difficolta_default(config) -> int:
    return max(1, min(4, int(getattr(config, "difficolta", 4) or 4)))


def risolvi_difficolta(personaggio, config) -> int:
    """
    Parte dalla difficoltà predefinita; per ogni regola condizionale che matcha
    applica il minimo (più favorevole al giocatore).
    """
    best = difficolta_default(config)
    for rule in getattr(config, "regole_difficolta", None) or []:
        if not isinstance(rule, dict):
            continue
        if not gruppo_requisiti_soddisfatto(personaggio, rule):
            continue
        try:
            d = max(1, min(4, int(rule.get("difficolta") or best)))
        except (TypeError, ValueError):
            continue
        best = min(best, d)
    return best


def deve_saltare_minigioco(personaggio, config) -> bool:
    """True = nessun minigioco, effetto QR immediato."""
    for gruppo in getattr(config, "esclusioni_minigioco", None) or []:
        if isinstance(gruppo, dict) and gruppo_requisiti_soddisfatto(personaggio, gruppo):
            return True
    return False


def scegli_tipo_e_difficolta(config, seed: int, personaggio=None) -> Tuple[str, int]:
    """Estrae tipo a caso; difficoltà da regole condizionali sul personaggio."""
    rng = _rng(seed)
    tipo = rng.choice(tipi_pool(config))
    if personaggio is not None:
        difficolta = risolvi_difficolta(personaggio, config)
    else:
        difficolta = difficolta_default(config)
    return tipo, difficolta


def _config_attiva(config) -> bool:
    if not config or not config.attivo:
        return False
    if not tipi_pool(config):
        return False
    return True


def personaggio_bloccato_su_qr(personaggio, qr_code) -> bool:
    from .models import MinigiocoQrBlocco

    return MinigiocoQrBlocco.objects.filter(personaggio=personaggio, qr_code=qr_code).exists()


def ha_sblocco_minigioco(personaggio, qr_code) -> bool:
    from .models import MinigiocoQrSession

    return MinigiocoQrSession.objects.filter(
        personaggio=personaggio,
        qr_code=qr_code,
        stato__in=STATI_SBLocco,
    ).exists()


def session_allows_bypass(session_id, personaggio, qr_code) -> bool:
    from .models import MinigiocoQrSession

    try:
        sess = MinigiocoQrSession.objects.get(pk=session_id)
    except MinigiocoQrSession.DoesNotExist:
        return False
    if sess.personaggio_id != personaggio.pk or sess.qr_code_id != qr_code.id:
        return False
    return sess.stato in STATI_SBLocco


def requisiti_minigioco_soddisfatti(personaggio, config) -> bool:
    ok, _ = personaggio_soddisfa_requisiti(personaggio, config.requisiti_attivazione or [])
    return ok


def immagine_url_per_config(config, request=None) -> str:
    if not config or not config.immagine:
        return ""
    try:
        url = config.immagine.url
    except Exception:
        return ""
    if request and url.startswith("/"):
        return request.build_absolute_uri(url)
    return url


def minigioco_ha_immagine_disponibile(config) -> bool:
    if config and config.immagine:
        return True
    if not config or not getattr(config, "usa_biblioteca_se_vuota", True):
        return False
    from personaggi.minigioco_biblioteca import biblioteca_immagine_count

    return biblioteca_immagine_count() > 0


def risolvi_immagine_sessione(config, request=None, seed: int | None = None):
    """
    Ritorna (url, biblioteca_row|None).
    Priorità: immagine dedicata QR → libreria casuale (seed).
    """
    from personaggi.minigioco_biblioteca import (
        immagine_biblioteca_url,
        scegli_immagine_biblioteca,
    )

    custom = immagine_url_per_config(config, request)
    if custom:
        return custom, None
    if not config or not getattr(config, "usa_biblioteca_se_vuota", True):
        return "", None
    if seed is None:
        seed = random.randint(1, 2_147_483_647)
    row = scegli_immagine_biblioteca(seed)
    if not row:
        return "", None
    return immagine_biblioteca_url(row, request), row


def descrizione_difficolta(tipo: str, difficolta: int) -> str:
    cols, rows = grid_size(tipo, difficolta)
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return f"{cols}×{rows} ({(cols * rows) // 2} coppie)"
    return f"{cols}×{rows}"


def _sessione_payload(sess, config, request=None) -> Dict[str, Any]:
    now = timezone.now()
    remaining = None
    if sess.scadenza_at:
        remaining = max(0, int((sess.scadenza_at - now).total_seconds()))
    stato_gioco = sess.stato_gioco or {}
    client_state = {k: v for k, v in stato_gioco.items() if k != "tipo"}
    return {
        "session_id": str(sess.id),
        "tipo": sess.tipo,
        "difficolta": sess.difficolta,
        "difficolta_label": descrizione_difficolta(sess.tipo, sess.difficolta),
        "immagine_url": sess.immagine_url or immagine_url_per_config(config, request),
        "stato_gioco": client_state,
        "timer_secondi_rimanenti": remaining,
        "scadenza_at": sess.scadenza_at.isoformat() if sess.scadenza_at else None,
        "messaggio_pre": (config.messaggio_pre or "").strip() or None,
        "timer_scadenza_azione": config.timer_scadenza_azione if config.timer_secondi else None,
    }


def _crea_sessione(personaggio, qr_code, config, request=None):
    from .models import MinigiocoQrSession

    seed = random.randint(1, 2_147_483_647)
    tipo, difficolta = scegli_tipo_e_difficolta(config, seed, personaggio=personaggio)
    game_seed = _rng(seed).randint(1, 2_147_483_647)
    stato = generate_game_state(tipo, difficolta, game_seed)
    img_url, bib_row = risolvi_immagine_sessione(config, request, seed=seed)
    scadenza_at = None
    if config.timer_secondi and int(config.timer_secondi) > 0:
        scadenza_at = timezone.now() + timedelta(seconds=int(config.timer_secondi))
    return MinigiocoQrSession.objects.create(
        personaggio=personaggio,
        qr_code=qr_code,
        user_id=getattr(personaggio, "proprietario_id", None),
        tipo=tipo,
        difficolta=difficolta,
        seed=seed,
        stato_gioco=stato,
        immagine_url=img_url,
        biblioteca_immagine=bib_row,
        scadenza_at=scadenza_at,
        stato=SESSIONE_IN_CORSO,
    )


def check_gate_minigioco(
    *,
    qr_code,
    personaggio,
    request=None,
    bypass_session_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Ritorna payload minigioco se il giocatore deve risolverlo, altrimenti None.
    """
    from .models import MinigiocoQrConfig, MinigiocoQrSession

    if bypass_session_id and session_allows_bypass(bypass_session_id, personaggio, qr_code):
        return None

    try:
        config = qr_code.configurazione_minigioco
    except MinigiocoQrConfig.DoesNotExist:
        return None

    if not _config_attiva(config):
        return None

    if not personaggio:
        return {
            "blocked": True,
            "error": "Parametro personaggio_id richiesto per questo QR con minigioco.",
        }

    if personaggio_bloccato_su_qr(personaggio, qr_code):
        return {
            "blocked": True,
            "error": "Questo QR non è più accessibile per il tuo personaggio.",
            "tipo_modello": "minigioco_bloccato",
        }

    if ha_sblocco_minigioco(personaggio, qr_code):
        return None

    if deve_saltare_minigioco(personaggio, config):
        return None

    if not requisiti_minigioco_soddisfatti(personaggio, config):
        return None

    if not minigioco_ha_immagine_disponibile(config):
        return None

    in_corso = (
        MinigiocoQrSession.objects.filter(
            personaggio=personaggio,
            qr_code=qr_code,
            stato=SESSIONE_IN_CORSO,
        )
        .order_by("-avviato_at")
        .first()
    )
    if in_corso:
        if in_corso.scadenza_at and timezone.now() >= in_corso.scadenza_at:
            return gestisci_scadenza_sessione(in_corso, config, request=request, personaggio=personaggio)
        return {
            "tipo_modello": "minigioco_richiesto",
            "messaggio": (config.messaggio_pre or "").strip() or "Completa il minigioco per sbloccare il QR.",
            "dati": _sessione_payload(in_corso, config, request),
            "qrcode_id": qr_code.id,
        }

    sess = _crea_sessione(personaggio, qr_code, config, request)
    return {
        "tipo_modello": "minigioco_richiesto",
        "messaggio": (config.messaggio_pre or "").strip() or "Completa il minigioco per sbloccare il QR.",
        "dati": _sessione_payload(sess, config, request),
        "qrcode_id": qr_code.id,
    }


@transaction.atomic
def completa_sessione(session_id, personaggio, client_state: dict) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    from .models import MinigiocoQrSession

    try:
        sess = MinigiocoQrSession.objects.select_for_update().get(pk=session_id)
    except MinigiocoQrSession.DoesNotExist:
        return False, "Sessione minigioco non trovata.", None

    if sess.personaggio_id != personaggio.pk:
        return False, "Sessione non valida per questo personaggio.", None

    if sess.stato != SESSIONE_IN_CORSO:
        if sess.stato in STATI_SBLocco:
            return True, "Già completato.", {
                "tipo_modello": "minigioco_superato",
                "minigioco_session_id": str(sess.id),
                "qrcode_id": sess.qr_code_id,
            }
        return False, "Sessione non più attiva.", None

    if sess.scadenza_at and timezone.now() >= sess.scadenza_at:
        try:
            config = sess.qr_code.configurazione_minigioco
        except Exception:
            config = None
        if config:
            payload = gestisci_scadenza_sessione(sess, config, personaggio=personaggio)
            if payload.get("tipo_modello") == "minigioco_superato":
                return True, payload.get("messaggio", ""), payload
            return False, payload.get("messaggio") or payload.get("error") or "Tempo scaduto.", payload

    if not verify_solution(sess.tipo, sess.difficolta, client_state):
        return False, "Soluzione non corretta.", None

    now = timezone.now()
    sess.stato = SESSIONE_COMPLETATO
    sess.completato_at = now
    sess.save(update_fields=["stato", "completato_at", "updated_at"])

    msg = ""
    try:
        msg = (sess.qr_code.configurazione_minigioco.messaggio_vittoria or "").strip()
    except Exception:
        pass

    return True, msg or "Minigioco completato!", {
        "tipo_modello": "minigioco_superato",
        "minigioco_session_id": str(sess.id),
        "messaggio": msg or "Minigioco completato! Scansiona di nuovo per l'effetto.",
        "qrcode_id": sess.qr_code_id,
    }


@transaction.atomic
def gestisci_scadenza_sessione(sess, config, *, request=None, personaggio=None) -> Dict[str, Any]:
    from .models import MinigiocoQrBlocco, MinigiocoQrSession

    if personaggio and sess.personaggio_id != personaggio.pk:
        return {"error": "Sessione non valida.", "tipo_modello": "minigioco_errore"}

    if sess.stato != SESSIONE_IN_CORSO:
        if sess.stato in STATI_SBLocco:
            return {
                "tipo_modello": "minigioco_superato",
                "minigioco_session_id": str(sess.id),
                "qrcode_id": sess.qr_code_id,
            }
        return {"error": "Sessione non attiva.", "tipo_modello": "minigioco_errore"}

    azione = (config.timer_scadenza_azione or TIMER_SCADENZA_RESET).strip()
    now = timezone.now()

    if azione == TIMER_SCADENZA_ATTIVA:
        sess.stato = SESSIONE_SCADUTO_ATTIVA
        sess.completato_at = now
        sess.save(update_fields=["stato", "completato_at", "updated_at"])
        return {
            "tipo_modello": "minigioco_superato",
            "minigioco_session_id": str(sess.id),
            "messaggio": "Tempo scaduto: il QR si attiva comunque.",
            "qrcode_id": sess.qr_code_id,
            "scadenza_esito": TIMER_SCADENZA_ATTIVA,
        }

    if azione == TIMER_SCADENZA_BLOCCA:
        sess.stato = SESSIONE_SCADUTO_BLOCCA
        sess.completato_at = now
        sess.save(update_fields=["stato", "completato_at", "updated_at"])
        MinigiocoQrBlocco.objects.get_or_create(
            personaggio_id=sess.personaggio_id,
            qr_code_id=sess.qr_code_id,
        )
        return {
            "tipo_modello": "minigioco_bloccato",
            "messaggio": "Tempo scaduto: questo QR non è più accessibile.",
            "qrcode_id": sess.qr_code_id,
            "scadenza_esito": TIMER_SCADENZA_BLOCCA,
        }

    # reset_minigioco (default)
    sess.stato = SESSIONE_SCADUTO_RESET
    sess.completato_at = now
    sess.save(update_fields=["stato", "completato_at", "updated_at"])
    nuova = _crea_sessione(sess.personaggio, sess.qr_code, config, request)
    return {
        "tipo_modello": "minigioco_richiesto",
        "messaggio": "Tempo scaduto: il minigioco riparte.",
        "dati": _sessione_payload(nuova, config, request),
        "qrcode_id": sess.qr_code_id,
        "scadenza_esito": TIMER_SCADENZA_RESET,
    }


@transaction.atomic
def expire_sessione(session_id, personaggio, request=None) -> Dict[str, Any]:
    from .models import MinigiocoQrSession

    try:
        sess = MinigiocoQrSession.objects.select_for_update().get(pk=session_id)
    except MinigiocoQrSession.DoesNotExist:
        return {"error": "Sessione non trovata.", "tipo_modello": "minigioco_errore"}

    if sess.personaggio_id != personaggio.pk:
        return {"error": "Sessione non valida.", "tipo_modello": "minigioco_errore"}

    try:
        config = sess.qr_code.configurazione_minigioco
    except Exception:
        return {"error": "Configurazione minigioco assente.", "tipo_modello": "minigioco_errore"}

    return gestisci_scadenza_sessione(sess, config, request=request, personaggio=personaggio)
