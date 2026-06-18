"""
Tipi di risultato e generatori di punteggio per sport diversi (sistema scommesse).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from personaggi.scommesse_logic import ESITO_CASA, ESITO_PAREGGIO, ESITO_TRASFERTA

TIPO_CALCIO = "calcio"
TIPO_RUGBY = "rugby"
TIPO_BASKET = "basket"
TIPO_FOOTBALL_USA = "football_usa"
TIPO_BASEBALL = "baseball"
TIPO_TENNIS = "tennis"
TIPO_VOLLEY = "volley"
TIPO_HOCKEY = "hockey"

TIPO_RISULTATO_CHOICES = [
    (TIPO_CALCIO, "Calcio"),
    (TIPO_RUGBY, "Rugby"),
    (TIPO_BASKET, "Basket"),
    (TIPO_FOOTBALL_USA, "Football americano"),
    (TIPO_BASEBALL, "Baseball"),
    (TIPO_TENNIS, "Tennis"),
    (TIPO_VOLLEY, "Pallavolo"),
    (TIPO_HOCKEY, "Hockey su ghiaccio"),
]

TIPI_RISULTATO_VALIDI = {c[0] for c in TIPO_RISULTATO_CHOICES}


@dataclass(frozen=True)
class TipoRisultatoMeta:
    label: str
    pareggio_consentito: bool
    unita_breve: str


TIPO_RISULTATO_META: dict[str, TipoRisultatoMeta] = {
    TIPO_CALCIO: TipoRisultatoMeta("Calcio", True, "gol"),
    TIPO_RUGBY: TipoRisultatoMeta("Rugby", True, "pt"),
    TIPO_BASKET: TipoRisultatoMeta("Basket", False, "pt"),
    TIPO_FOOTBALL_USA: TipoRisultatoMeta("Football americano", False, "pt"),
    TIPO_BASEBALL: TipoRisultatoMeta("Baseball", False, "run"),
    TIPO_TENNIS: TipoRisultatoMeta("Tennis", False, "set"),
    TIPO_VOLLEY: TipoRisultatoMeta("Pallavolo", False, "set"),
    TIPO_HOCKEY: TipoRisultatoMeta("Hockey su ghiaccio", False, "gol"),
}


def normalizza_tipo_risultato(tipo: str | None) -> str:
    if tipo in TIPI_RISULTATO_VALIDI:
        return tipo
    return TIPO_CALCIO


def meta_tipo_risultato(tipo: str | None) -> TipoRisultatoMeta:
    return TIPO_RISULTATO_META[normalizza_tipo_risultato(tipo)]


def pareggio_consentito(tipo: str | None) -> bool:
    return meta_tipo_risultato(tipo).pareggio_consentito


def formatta_risultato(tipo: str | None, punteggio_casa: int, punteggio_trasferta: int) -> str:
    """Testo leggibile del punteggio (es. '2-1 set', '98-87 pt')."""
    meta = meta_tipo_risultato(tipo)
    return f"{punteggio_casa}-{punteggio_trasferta} {meta.unita_breve}"


def _marginale(rng: random.Random, min_m: int, max_m: int) -> int:
    return rng.randint(min_m, max_m)


def _punteggio_calcio(esito: str, rng: random.Random) -> tuple[int, int]:
    if esito == ESITO_PAREGGIO:
        gol = rng.randint(0, 4)
        return gol, gol
    if esito == ESITO_CASA:
        gol_trasferta = rng.randint(0, 3)
        return gol_trasferta + _marginale(rng, 1, 3), gol_trasferta
    gol_casa = rng.randint(0, 3)
    return gol_casa, gol_casa + _marginale(rng, 1, 3)


def _punteggio_rugby(esito: str, rng: random.Random) -> tuple[int, int]:
    """Punteggi tipici rugby (multipli di 3 o 5)."""
    if esito == ESITO_PAREGGIO:
        base = rng.choice([6, 9, 12, 15, 18, 21])
        return base, base
    if esito == ESITO_CASA:
        lose = rng.choice([0, 3, 6, 9, 12, 15, 18])
        win = lose + rng.choice([3, 5, 7, 10, 14])
        return win, lose
    lose = rng.choice([0, 3, 6, 9, 12, 15, 18])
    win = lose + rng.choice([3, 5, 7, 10, 14])
    return lose, win


def _punteggio_basket(esito: str, rng: random.Random) -> tuple[int, int]:
    base = rng.randint(78, 108)
    margin = _marginale(rng, 1, 22)
    if esito == ESITO_CASA:
        return base + margin, base
    return base, base + margin


def _punteggio_football_usa(esito: str, rng: random.Random) -> tuple[int, int]:
    """Punteggi NFL-style (multipli di 3 o 7)."""
    scores = [0, 3, 6, 7, 10, 13, 14, 17, 20, 21, 24, 27, 28, 31, 35, 38, 42]
    if esito == ESITO_CASA:
        lose = rng.choice(scores[:12])
        win = lose + rng.choice([3, 4, 7, 8, 10, 14])
        return win, lose
    lose = rng.choice(scores[:12])
    win = lose + rng.choice([3, 4, 7, 8, 10, 14])
    return lose, win


def _punteggio_baseball(esito: str, rng: random.Random) -> tuple[int, int]:
    if esito == ESITO_CASA:
        lose = rng.randint(0, 9)
        return lose + _marginale(rng, 1, 6), lose
    lose = rng.randint(0, 9)
    return lose, lose + _marginale(rng, 1, 6)


def _punteggio_tennis(esito: str, rng: random.Random) -> tuple[int, int]:
    """Best of 3: vincitore 2 set, perdente 0 o 1."""
    if esito == ESITO_CASA:
        sets_perd = rng.choice([0, 1])
        return 2, sets_perd
    sets_perd = rng.choice([0, 1])
    return sets_perd, 2


def _punteggio_volley(esito: str, rng: random.Random) -> tuple[int, int]:
    """Best of 5: vincitore 3 set."""
    if esito == ESITO_CASA:
        sets_perd = rng.choice([0, 1, 2])
        return 3, sets_perd
    sets_perd = rng.choice([0, 1, 2])
    return sets_perd, 3


def _punteggio_hockey(esito: str, rng: random.Random) -> tuple[int, int]:
    if esito == ESITO_CASA:
        lose = rng.randint(0, 4)
        return lose + _marginale(rng, 1, 4), lose
    lose = rng.randint(0, 4)
    return lose, lose + _marginale(rng, 1, 4)


_GENERATORI = {
    TIPO_CALCIO: _punteggio_calcio,
    TIPO_RUGBY: _punteggio_rugby,
    TIPO_BASKET: _punteggio_basket,
    TIPO_FOOTBALL_USA: _punteggio_football_usa,
    TIPO_BASEBALL: _punteggio_baseball,
    TIPO_TENNIS: _punteggio_tennis,
    TIPO_VOLLEY: _punteggio_volley,
    TIPO_HOCKEY: _punteggio_hockey,
}


def genera_punteggio_incontro(tipo_risultato: str | None, esito: str, rng: random.Random) -> tuple[int, int]:
    """Genera punteggio casa/trasferta coerente con esito e sport."""
    tipo = normalizza_tipo_risultato(tipo_risultato)
    if esito == ESITO_PAREGGIO and not pareggio_consentito(tipo):
        raise ValueError(f"Pareggio non consentito per sport {tipo}")
    gen = _GENERATORI[tipo]
    return gen(esito, rng)
