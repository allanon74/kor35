"""
Minigiochi QR: sliding puzzle, memory, rotate tiles, simon, pattern lock, pipe connect.
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
MINIGIOCO_TIPO_SIMON = "simon"
MINIGIOCO_TIPO_PATTERN = "pattern_lock"
MINIGIOCO_TIPO_PIPE = "pipe_connect"

MINIGIOCO_TIPI = (
    MINIGIOCO_TIPO_SLIDING,
    MINIGIOCO_TIPO_MEMORY,
    MINIGIOCO_TIPO_ROTATE,
    MINIGIOCO_TIPO_SIMON,
    MINIGIOCO_TIPO_PATTERN,
    MINIGIOCO_TIPO_PIPE,
)

MINIGIOCO_TIPI_SENZA_IMMAGINE = frozenset(
    {
        MINIGIOCO_TIPO_SIMON,
        MINIGIOCO_TIPO_PATTERN,
        MINIGIOCO_TIPO_PIPE,
    }
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

# Finestra per bypass immediato post-vittoria (caricamento effetto QR) in modalità ogni_scansione.
BYPASS_TRANSITO_SECONDI = 120

_SLIDING_GRID = {1: 2, 2: 3, 3: 4, 4: 5}
_ROTATE_GRID = {1: 2, 2: 3, 3: 4, 4: 5}
_MEMORY_GRID = {1: (2, 2), 2: (3, 4), 3: (4, 4), 4: (4, 5)}
_SIMON_LEN = {1: 3, 2: 4, 3: 5, 4: 6}
_SIMON_BUTTONS = {1: 4, 2: 4, 3: 5, 4: 6}
_PATTERN_LEN = {1: 4, 2: 5, 3: 6, 4: 7}
_PIPE_GRID = {1: 3, 2: 4, 3: 5, 4: 6}

# Maschere connessioni tubi: N=1, E=2, S=4, W=8
_PIPE_BASE_MASKS = (5, 10, 3, 6, 12, 9, 7, 14, 13, 11, 15)


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def grid_size(tipo: str, difficolta: int) -> Tuple[int, int]:
    d = max(1, min(4, int(difficolta or 2)))
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return _MEMORY_GRID[d]
    if tipo == MINIGIOCO_TIPO_SIMON:
        return _SIMON_BUTTONS[d], _SIMON_LEN[d]
    if tipo == MINIGIOCO_TIPO_PATTERN:
        return 3, 3
    if tipo == MINIGIOCO_TIPO_PIPE:
        n = _PIPE_GRID[d]
        return n, n
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


def generate_simon_state(difficolta: int, seed: int) -> Dict[str, Any]:
    d = max(1, min(4, int(difficolta or 2)))
    length = _SIMON_LEN[d]
    num_buttons = _SIMON_BUTTONS[d]
    rng = _rng(seed)
    sequence = [rng.randrange(num_buttons) for _ in range(length)]
    return {
        "num_buttons": num_buttons,
        "sequence": sequence,
        "player_input": [],
    }


def _pattern_neighbors_3x3(idx: int) -> List[int]:
    r, c = divmod(idx, 3)
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < 3 and 0 <= nc < 3:
                out.append(nr * 3 + nc)
    return out


def generate_pattern_lock_state(difficolta: int, seed: int) -> Dict[str, Any]:
    d = max(1, min(4, int(difficolta or 2)))
    target_len = _PATTERN_LEN[d]
    rng = _rng(seed)
    for _ in range(80):
        start = rng.randrange(9)
        pattern = [start]
        visited = {start}
        while len(pattern) < target_len:
            opts = [n for n in _pattern_neighbors_3x3(pattern[-1]) if n not in visited]
            if not opts:
                break
            nxt = rng.choice(opts)
            pattern.append(nxt)
            visited.add(nxt)
        if len(pattern) >= target_len:
            return {"pattern": pattern, "player_input": []}
    # fallback lineare
    return {"pattern": list(range(min(target_len, 9))), "player_input": []}


def _rotate_pipe_mask(mask: int, times: int) -> int:
    conn = int(mask) & 15
    for _ in range(times % 4):
        new = 0
        if conn & 1:
            new |= 2
        if conn & 2:
            new |= 4
        if conn & 4:
            new |= 8
        if conn & 8:
            new |= 1
        conn = new
    return conn


def _pipe_mask_for_cell(r: int, c: int, path_set: set[tuple[int, int]]) -> int:
    conn = 0
    if (r - 1, c) in path_set:
        conn |= 1
    if (r, c + 1) in path_set:
        conn |= 2
    if (r + 1, c) in path_set:
        conn |= 4
    if (r, c - 1) in path_set:
        conn |= 8
    return conn


def _encode_pipe_tile(mask: int, rng: random.Random) -> Tuple[int, int]:
    if mask == 0:
        return 0, rng.randint(0, 3)
    for base in _PIPE_BASE_MASKS:
        for rot in range(4):
            if _rotate_pipe_mask(base, rot) == mask:
                scramble = rng.randint(0, 3)
                return base, (rot + scramble) % 4
    return 15, rng.randint(0, 3)


def _generate_pipe_path(size: int, rng: random.Random) -> List[tuple[int, int]]:
    target = (size - 1, size - 1)

    def walk(pos: tuple[int, int], visited: set[tuple[int, int]], path: list[tuple[int, int]]) -> bool:
        if pos == target:
            return True
        r, c = pos
        opts = []
        for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size and (nr, nc) not in visited:
                dist = abs(nr - target[0]) + abs(nc - target[1])
                opts.append((dist, (nr, nc)))
        if not opts:
            return False
        opts.sort(key=lambda x: x[0])
        rng.shuffle(opts)
        for _, nxt in opts[:3]:
            visited.add(nxt)
            path.append(nxt)
            if walk(nxt, visited, path):
                return True
            path.pop()
            visited.remove(nxt)
        return False

    for _ in range(60):
        visited = {(0, 0)}
        path = [(0, 0)]
        if walk((0, 0), visited, path):
            return path
    # percorso L
    path = [(0, c) for c in range(size)]
    path += [(r, size - 1) for r in range(1, size)]
    return path


def generate_pipe_connect_state(difficolta: int, seed: int) -> Dict[str, Any]:
    d = max(1, min(4, int(difficolta or 2)))
    size = _PIPE_GRID[d]
    rng = _rng(seed)
    path = _generate_pipe_path(size, rng)
    path_set = set(path)
    bases: List[int] = []
    rotations: List[int] = []
    for r in range(size):
        for c in range(size):
            if (r, c) in path_set:
                mask = _pipe_mask_for_cell(r, c, path_set)
            else:
                mask = 0
            base, rot = _encode_pipe_tile(mask, rng)
            bases.append(base)
            rotations.append(rot)
    return {
        "size": size,
        "start": 0,
        "end": size * size - 1,
        "bases": bases,
        "rotations": rotations,
    }


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
    if tipo == MINIGIOCO_TIPO_SIMON:
        return {"tipo": tipo, **generate_simon_state(difficolta, seed)}
    if tipo == MINIGIOCO_TIPO_PATTERN:
        return {"tipo": tipo, **generate_pattern_lock_state(difficolta, seed)}
    if tipo == MINIGIOCO_TIPO_PIPE:
        return {"tipo": tipo, **generate_pipe_connect_state(difficolta, seed)}
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


def verify_simon(sequence: List[int], player_input: List[int]) -> bool:
    if not sequence:
        return False
    return list(player_input or []) == list(sequence)


def verify_pattern_lock(pattern: List[int], player_input: List[int]) -> bool:
    if not pattern:
        return False
    return list(player_input or []) == list(pattern)


def verify_pipe_connect(
    bases: List[int],
    rotations: List[int],
    size: int,
    start: int,
    end: int,
) -> bool:
    total = size * size
    if len(bases) != total or len(rotations) != total:
        return False
    conns = [_rotate_pipe_mask(int(bases[i]), int(rotations[i])) for i in range(total)]

    def idx_rc(idx: int) -> tuple[int, int]:
        return divmod(idx, size)

    def connected(a: int, b: int) -> bool:
        ar, ac = idx_rc(a)
        br, bc = idx_rc(b)
        if ar == br and ac + 1 == bc:
            return bool(conns[a] & 2 and conns[b] & 8)
        if ac == bc and ar + 1 == br:
            return bool(conns[a] & 4 and conns[b] & 1)
        return False

    stack = [start]
    seen = {start}
    while stack:
        cur = stack.pop()
        if cur == end:
            return True
        r, c = idx_rc(cur)
        for dr, dc, out_mask, in_mask in (
            (-1, 0, 1, 4),
            (0, 1, 2, 8),
            (1, 0, 4, 1),
            (0, -1, 8, 2),
        ):
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size:
                nxt = nr * size + nc
                if nxt not in seen and (conns[cur] & out_mask) and (conns[nxt] & in_mask):
                    seen.add(nxt)
                    stack.append(nxt)
    return False


def verify_solution(
    tipo: str,
    difficolta: int,
    client_state: dict,
    server_state: dict | None = None,
) -> bool:
    if not isinstance(client_state, dict):
        return False
    server_state = server_state or {}
    cols, rows = grid_size(tipo, difficolta)
    if tipo == MINIGIOCO_TIPO_SLIDING:
        size = cols
        return verify_sliding(client_state.get("tiles") or [], size)
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return verify_memory(
            client_state.get("cards") or server_state.get("cards") or [],
            client_state.get("matched") or [],
            cols,
            rows,
        )
    if tipo == MINIGIOCO_TIPO_ROTATE:
        size = cols
        return verify_rotate(client_state.get("rotations") or [], size)
    if tipo == MINIGIOCO_TIPO_SIMON:
        return verify_simon(
            server_state.get("sequence") or [],
            client_state.get("player_input") or [],
        )
    if tipo == MINIGIOCO_TIPO_PATTERN:
        return verify_pattern_lock(
            server_state.get("pattern") or [],
            client_state.get("player_input") or [],
        )
    if tipo == MINIGIOCO_TIPO_PIPE:
        size = int(server_state.get("size") or cols or 3)
        return verify_pipe_connect(
            server_state.get("bases") or [],
            client_state.get("rotations") or [],
            size,
            int(server_state.get("start") or 0),
            int(server_state.get("end") or (size * size - 1)),
        )
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


def tipi_pool_giocabili(config) -> List[str]:
    """Filtra tipi che richiedono immagine se non disponibile."""
    tipi = tipi_pool(config)
    if minigioco_ha_immagine_disponibile(config):
        return tipi
    senza_img = [t for t in tipi if t in MINIGIOCO_TIPI_SENZA_IMMAGINE]
    return senza_img


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
    pool = tipi_pool_giocabili(config)
    if not pool:
        pool = list(MINIGIOCO_TIPI_SENZA_IMMAGINE)
    tipo = rng.choice(pool)
    if personaggio is not None:
        difficolta = risolvi_difficolta(personaggio, config)
    else:
        difficolta = difficolta_default(config)
    return tipo, difficolta


def _config_attiva(config) -> bool:
    if not config or not config.attivo:
        return False
    if not tipi_pool_giocabili(config):
        return False
    return True


def _sezione_minigioco_attiva(config) -> bool:
    return bool(config and getattr(config, "sezione_attiva", False))


def verifica_accesso_qr_minigioco(personaggio, config) -> Tuple[bool, str]:
    """Con sezione attiva: (ok, messaggio) per i requisiti di accesso al QR."""
    ok, detail = personaggio_soddisfa_requisiti(personaggio, config.requisiti_attivazione or [])
    if ok:
        return True, ""
    custom = (getattr(config, "messaggio_accesso_negato", None) or "").strip()
    return False, custom or detail or "Non possiedi i requisiti per usare questo QR."


def personaggio_bloccato_su_qr(personaggio, qr_code) -> bool:
    from .models import MinigiocoQrBlocco

    return MinigiocoQrBlocco.objects.filter(personaggio=personaggio, qr_code=qr_code).exists()


def _modalita_sblocco_config(config) -> str:
    from .models import MinigiocoQrConfig

    if not config:
        return MinigiocoQrConfig.SBLOCCO_PERMANENTE
    return getattr(config, "modalita_sblocco", None) or MinigiocoQrConfig.SBLOCCO_PERMANENTE


def _sblocco_sessione_ancora_valido(config, sess) -> bool:
    """True se la sessione completata consente ancora di saltare il minigioco."""
    from .models import MinigiocoQrConfig

    if sess.stato not in STATI_SBLocco:
        return False
    modalita = _modalita_sblocco_config(config)
    if modalita == MinigiocoQrConfig.SBLOCCO_OGNI_SCANSIONE:
        return False
    if modalita == MinigiocoQrConfig.SBLOCCO_PERMANENTE:
        return True
    if modalita == MinigiocoQrConfig.SBLOCCO_TEMPORANEO:
        secondi = int(getattr(config, "sblocco_secondi", 0) or 0)
        if secondi <= 0 or not sess.completato_at:
            return False
        return timezone.now() < sess.completato_at + timedelta(seconds=secondi)
    return True


def ha_sblocco_minigioco(personaggio, qr_code, config=None) -> bool:
    from .models import MinigiocoQrConfig, MinigiocoQrSession

    if config is None:
        try:
            config = qr_code.configurazione_minigioco
        except MinigiocoQrConfig.DoesNotExist:
            return False

    if _modalita_sblocco_config(config) == MinigiocoQrConfig.SBLOCCO_OGNI_SCANSIONE:
        return False

    latest = (
        MinigiocoQrSession.objects.filter(
            personaggio=personaggio,
            qr_code=qr_code,
            stato__in=STATI_SBLocco,
        )
        .order_by("-completato_at", "-updated_at")
        .first()
    )
    if not latest:
        return False
    return _sblocco_sessione_ancora_valido(config, latest)


def session_allows_bypass(session_id, personaggio, qr_code) -> bool:
    from .models import MinigiocoQrConfig, MinigiocoQrSession

    try:
        sess = MinigiocoQrSession.objects.get(pk=session_id)
    except MinigiocoQrSession.DoesNotExist:
        return False
    if sess.personaggio_id != personaggio.pk or sess.qr_code_id != qr_code.id:
        return False
    if sess.stato not in STATI_SBLocco:
        return False

    try:
        config = qr_code.configurazione_minigioco
    except MinigiocoQrConfig.DoesNotExist:
        return True

    modalita = _modalita_sblocco_config(config)
    if modalita == MinigiocoQrConfig.SBLOCCO_OGNI_SCANSIONE:
        if not sess.completato_at:
            return False
        return timezone.now() < sess.completato_at + timedelta(seconds=BYPASS_TRANSITO_SECONDI)
    return _sblocco_sessione_ancora_valido(config, sess)


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
    if config and getattr(config, "immagine", None):
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
    d = max(1, min(4, int(difficolta or 2)))
    cols, rows = grid_size(tipo, difficolta)
    if tipo == MINIGIOCO_TIPO_MEMORY:
        return f"{cols}×{rows} ({(cols * rows) // 2} coppie)"
    if tipo == MINIGIOCO_TIPO_SIMON:
        return f"{_SIMON_LEN[d]} simboli · {_SIMON_BUTTONS[d]} tasti"
    if tipo == MINIGIOCO_TIPO_PATTERN:
        return f"{_PATTERN_LEN[d]} nodi"
    if tipo == MINIGIOCO_TIPO_PIPE:
        return f"{cols}×{rows} tubi"
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
    Se la sezione minigiochi è attiva: verifica requisiti di accesso al QR.
    Se il minigioco è attivo: ritorna payload minigioco da risolvere, altrimenti None
    (effetto QR normale dopo i controlli).
    """
    from .models import MinigiocoQrConfig, MinigiocoQrSession

    if bypass_session_id and session_allows_bypass(bypass_session_id, personaggio, qr_code):
        return None

    try:
        config = qr_code.configurazione_minigioco
    except MinigiocoQrConfig.DoesNotExist:
        return None

    if not _sezione_minigioco_attiva(config):
        return None

    richiede_personaggio = bool(config.requisiti_attivazione) or _config_attiva(config)
    if richiede_personaggio and not personaggio:
        return {
            "blocked": True,
            "error": "Parametro personaggio_id richiesto per questo QR con sezione minigiochi attiva.",
        }

    if personaggio and config.requisiti_attivazione:
        ok, msg = verifica_accesso_qr_minigioco(personaggio, config)
        if not ok:
            return {
                "tipo_modello": "minigioco_bloccato",
                "messaggio": msg,
                "qrcode_id": qr_code.id,
            }

    if not _config_attiva(config):
        return None

    if not personaggio:
        return {
            "blocked": True,
            "error": "Parametro personaggio_id richiesto per questo QR con minigioco attivo.",
        }

    if personaggio_bloccato_su_qr(personaggio, qr_code):
        return {
            "blocked": True,
            "error": "Questo QR non è più accessibile per il tuo personaggio.",
            "tipo_modello": "minigioco_bloccato",
        }

    if ha_sblocco_minigioco(personaggio, qr_code, config):
        return None

    if deve_saltare_minigioco(personaggio, config):
        return None

    if not tipi_pool_giocabili(config):
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

    if not verify_solution(sess.tipo, sess.difficolta, client_state, sess.stato_gioco or {}):
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
