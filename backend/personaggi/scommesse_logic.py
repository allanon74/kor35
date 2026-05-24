"""
Logica di calcolo quote e risultati per il sistema scommesse in-game.
"""
import hashlib
import random
import secrets
import string
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from personaggi.scommesse_config import DEFAULT_SCOMMESSE_CONFIG, ScommesseConfig, get_config_scommesse

ALLIBRATORE_SIGLA = "ALL"
CODICE_LENGTH = 5

# Retrocompatibilità per import esistenti
IMPORTO_MAX_SENZA_CODICE_DEFAULT = DEFAULT_SCOMMESSE_CONFIG.importo_max_senza_codice_default
SCADENZA_CALENDARIO_ORE = DEFAULT_SCOMMESSE_CONFIG.scadenza_calendario_ore
COMMISSIONE_ALLIBRATORE_PCT = DEFAULT_SCOMMESSE_CONFIG.commissione_allibratore_pct
MARGINE_BOOK_DEFAULT = DEFAULT_SCOMMESSE_CONFIG.margine_book_default
MARGINE_BOOK_MIN = DEFAULT_SCOMMESSE_CONFIG.margine_book_min

ESITO_CASA = "1"
ESITO_PAREGGIO = "X"
ESITO_TRASFERTA = "2"
ESITI_VALIDI = {ESITO_CASA, ESITO_PAREGGIO, ESITO_TRASFERTA}


def _decimal2(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rng_from_seed(seed: str) -> random.Random:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def potenza_effettiva(potenza: int, rng: random.Random, variabilita_pct: int = 10) -> Decimal:
    """Applica variabilità ±N% al valore di potenza."""
    delta = max(0, min(variabilita_pct, 50)) / 100.0
    fattore = Decimal(str(rng.uniform(1 - delta, 1 + delta)))
    return _decimal2(max(Decimal("1"), Decimal(potenza) * fattore))


def calcola_probabilita_esito(potenza_casa_eff: Decimal, potenza_trasferta_eff: Decimal):
    """Restituisce (p_casa, p_pareggio, p_trasferta) normalizzate."""
    pc = float(potenza_casa_eff)
    pt = float(potenza_trasferta_eff)
    if pc <= 0 and pt <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    ratio = min(pc, pt) / max(pc, pt) if max(pc, pt) > 0 else 1.0
    draw_base = 0.15 + 0.15 * ratio
    total = pc + pt
    p_casa = (pc / total) * (1 - draw_base)
    p_trasf = (pt / total) * (1 - draw_base)
    p_pareggio = draw_base
    s = p_casa + p_trasf + p_pareggio
    return (p_casa / s, p_pareggio / s, p_trasf / s)


def calcola_quote(
    potenza_casa: int,
    potenza_trasferta: int,
    seed: str,
    margine: Decimal | None = None,
    variabilita_pct: int | None = None,
) -> dict:
    """Calcola quote decimali 1/X/2 con variabilità sulle potenze."""
    cfg = get_config_scommesse()
    rng = _rng_from_seed(f"quote:{seed}")
    var_pct = variabilita_pct if variabilita_pct is not None else cfg.variabilita_potenza_pct
    pc_eff = potenza_effettiva(potenza_casa, rng, var_pct)
    pt_eff = potenza_effettiva(potenza_trasferta, rng, var_pct)
    p_casa, p_pareggio, p_trasf = calcola_probabilita_esito(pc_eff, pt_eff)
    m = margine or cfg.margine_book_default
    return {
        "potenza_casa_effettiva": pc_eff,
        "potenza_trasferta_effettiva": pt_eff,
        "quota_casa": _decimal2(m / Decimal(str(p_casa))),
        "quota_pareggio": _decimal2(m / Decimal(str(p_pareggio))),
        "quota_trasferta": _decimal2(m / Decimal(str(p_trasf))),
    }


def margine_allibratore(valore_all: int, cfg: ScommesseConfig | None = None) -> Decimal:
    """Quote più favorevoli per scommesse con codice allibratore."""
    cfg = cfg or get_config_scommesse()
    riduzione = Decimal(str(max(0, valore_all))) * cfg.riduzione_margine_per_punto_all
    return max(cfg.margine_book_min, cfg.margine_book_default - riduzione)


def genera_esito_incontro(
    potenza_casa_eff: Decimal,
    potenza_trasferta_eff: Decimal,
    seed: str,
) -> dict:
    """Genera esito e punteggio con RNG deterministico."""
    rng = _rng_from_seed(f"esito:{seed}")
    p_casa, p_pareggio, p_trasf = calcola_probabilita_esito(potenza_casa_eff, potenza_trasferta_eff)
    r = rng.random()
    if r < p_casa:
        esito = ESITO_CASA
    elif r < p_casa + p_pareggio:
        esito = ESITO_PAREGGIO
    else:
        esito = ESITO_TRASFERTA

    if esito == ESITO_PAREGGIO:
        gol = rng.randint(0, 4)
        gol_casa, gol_trasferta = gol, gol
    elif esito == ESITO_CASA:
        gol_trasferta = rng.randint(0, 3)
        gol_casa = gol_trasferta + rng.randint(1, 3)
    else:
        gol_casa = rng.randint(0, 3)
        gol_trasferta = gol_casa + rng.randint(1, 3)

    return {
        "esito": esito,
        "gol_casa": gol_casa,
        "gol_trasferta": gol_trasferta,
    }


def genera_codice_scommessa() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(CODICE_LENGTH))


def accoppia_squadre_random(squadre, seed: str) -> list[tuple]:
    """Accoppia le squadre in modo casuale; l'ultima resta fuori se dispari."""
    rng = _rng_from_seed(f"pair:{seed}")
    ids = list(squadre)
    rng.shuffle(ids)
    coppie = []
    for i in range(0, len(ids) - 1, 2):
        coppie.append((ids[i], ids[i + 1]))
    return coppie


def calendario_visibile_fino(data_risoluzione, campagna=None):
    if not data_risoluzione:
        return None
    ore = get_config_scommesse(campagna).scadenza_calendario_ore
    return data_risoluzione + timezone.timedelta(hours=ore)


def risultati_pubblicati(data_risoluzione) -> bool:
    if not data_risoluzione:
        return False
    return timezone.now() >= data_risoluzione


def calendario_ancora_visibile(calendario) -> bool:
    if not calendario.attivo:
        return False
    campagna_id = getattr(getattr(calendario, "sport", None), "campagna_id", None)
    limite = calendario_visibile_fino(calendario.data_risoluzione, campagna=campagna_id)
    if limite is None:
        return True
    return timezone.now() <= limite


POTENZA_FATTORE_SORPRESA_MAX = 5.0


def calcola_fattore_variazione_potenza(potenza_vincitrice: int, potenza_perdente: int) -> float:
    """
    Fattore moltiplicativo per il delta potenza post-incontro.
    - Favorito vince: fattore = rapporto (debole/forte) → variazione minima se gap grande.
    - Sfavorito vince: fattore = 1/rapporto (cappato) → variazione maggiore se upset.
    """
    p_win = max(1, int(potenza_vincitrice))
    p_lose = max(1, int(potenza_perdente))
    ratio = min(p_win, p_lose) / max(p_win, p_lose)
    if ratio <= 0:
        return 1.0
    if p_win >= p_lose:
        return ratio
    return min(POTENZA_FATTORE_SORPRESA_MAX, 1.0 / ratio)


def calcola_delta_potenza_incontro(potenza_vincitrice: int, potenza_perdente: int, base_vittoria: int, base_sconfitta: int) -> tuple[int, int]:
    """Restituisce (delta_vincitrice, delta_perdente) arrotondati."""
    fattore = calcola_fattore_variazione_potenza(potenza_vincitrice, potenza_perdente)
    delta_win = round(base_vittoria * fattore) if base_vittoria > 0 else 0
    delta_lose = round(base_sconfitta * fattore) if base_sconfitta > 0 else 0
    if delta_win == 0 and base_vittoria > 0 and fattore >= 0.15:
        delta_win = 1
    if delta_lose == 0 and base_sconfitta > 0 and fattore >= 0.15:
        delta_lose = 1
    return delta_win, delta_lose


def applica_variazione_potenza_dopo_incontro(incontro, cfg=None) -> bool:
    """
    Dopo la risoluzione, varia la potenza in base al rapporto tra le squadre:
    upset = delta grande, risultato atteso = delta piccolo. Pareggio = nessun cambiamento.
    """
    from personaggi.scommesse_config import (
        DEFAULT_SCOMMESSE_CONFIG,
        POTENZA_SQUADRA_MAX,
        POTENZA_SQUADRA_MIN,
        get_config_scommesse,
    )

    cfg = cfg or get_config_scommesse()
    if incontro.esito == ESITO_PAREGGIO:
        return False

    base_win = getattr(cfg, "potenza_delta_vittoria", DEFAULT_SCOMMESSE_CONFIG.potenza_delta_vittoria)
    base_lose = getattr(cfg, "potenza_delta_sconfitta", DEFAULT_SCOMMESSE_CONFIG.potenza_delta_sconfitta)
    if base_win <= 0 and base_lose <= 0:
        return False

    if incontro.esito == ESITO_CASA:
        vincitrice = incontro.squadra_casa
        perdente = incontro.squadra_trasferta
    elif incontro.esito == ESITO_TRASFERTA:
        vincitrice = incontro.squadra_trasferta
        perdente = incontro.squadra_casa
    else:
        return False

    delta_win, delta_lose = calcola_delta_potenza_incontro(
        vincitrice.potenza,
        perdente.potenza,
        base_win,
        base_lose,
    )

    changed = False
    if delta_win > 0:
        nuova = min(POTENZA_SQUADRA_MAX, int(vincitrice.potenza) + delta_win)
        if nuova != vincitrice.potenza:
            vincitrice.potenza = nuova
            vincitrice.save(update_fields=["potenza", "updated_at"])
            changed = True
    if delta_lose > 0:
        nuova = max(POTENZA_SQUADRA_MIN, int(perdente.potenza) - delta_lose)
        if nuova != perdente.potenza:
            perdente.potenza = nuova
            perdente.save(update_fields=["potenza", "updated_at"])
            changed = True
    return changed
