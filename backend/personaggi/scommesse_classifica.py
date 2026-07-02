"""
Classifiche torneo calcolate dagli incontri liquidati.
"""
from personaggi.scommesse_logic import ESITO_CASA, ESITO_PAREGGIO, ESITO_TRASFERTA
from personaggi.scommesse_models import IncontroScommesse, SportScommesse, SquadraScommesse
from personaggi.scommesse_risultati import pareggio_consentito

PUNTI_VITTORIA = 3
PUNTI_PAREGGIO = 1
PUNTI_SCONFITTA = 0


def _init_riga(squadra: SquadraScommesse) -> dict:
    return {
        "squadra_id": squadra.id,
        "nome": squadra.nome,
        "potenza": squadra.potenza,
        "giocate": 0,
        "vinte": 0,
        "pareggiate": 0,
        "perse": 0,
        "gol_fatti": 0,
        "gol_subiti": 0,
        "punti": 0,
    }


def _registra_esito(stats: dict, squadra_id, gf: int, gs: int, punti: int, esito_char: str):
    row = stats[str(squadra_id)]
    row["giocate"] += 1
    row["gol_fatti"] += gf
    row["gol_subiti"] += gs
    row["punti"] += punti
    if esito_char == "V":
        row["vinte"] += 1
    elif esito_char == "P":
        row["pareggiate"] += 1
    else:
        row["perse"] += 1


def calcola_classifica_sport(sport_id) -> dict | None:
    """Aggrega V/P/S, gol e punti da calendari liquidati."""
    sport = (
        SportScommesse.objects.filter(pk=sport_id, attivo=True)
        .select_related("campagna")
        .first()
    )
    if not sport:
        return None

    allow_draw = pareggio_consentito(sport.tipo_risultato)
    squadre = list(sport.squadre.filter(attiva=True).order_by("nome"))
    stats = {str(sq.id): _init_riga(sq) for sq in squadre}

    incontri = (
        IncontroScommesse.objects.filter(
            calendario__sport_id=sport_id,
            calendario__liquidato=True,
            calendario__attivo=True,
        )
        .select_related("squadra_casa", "squadra_trasferta", "calendario")
        .order_by("calendario__data_risoluzione", "ordine")
    )

    giornate_ids = set()
    for inc in incontri:
        giornate_ids.add(inc.calendario_id)
        casa_id = str(inc.squadra_casa_id)
        trasf_id = str(inc.squadra_trasferta_id)
        if casa_id not in stats:
            stats[casa_id] = _init_riga(inc.squadra_casa)
        if trasf_id not in stats:
            stats[trasf_id] = _init_riga(inc.squadra_trasferta)

        gf_casa, gf_trasf = int(inc.gol_casa), int(inc.gol_trasferta)
        if inc.esito == ESITO_PAREGGIO:
            _registra_esito(stats, casa_id, gf_casa, gf_trasf, PUNTI_PAREGGIO, "P")
            _registra_esito(stats, trasf_id, gf_trasf, gf_casa, PUNTI_PAREGGIO, "P")
        elif inc.esito == ESITO_CASA:
            _registra_esito(stats, casa_id, gf_casa, gf_trasf, PUNTI_VITTORIA, "V")
            _registra_esito(stats, trasf_id, gf_trasf, gf_casa, PUNTI_SCONFITTA, "S")
        else:
            _registra_esito(stats, trasf_id, gf_trasf, gf_casa, PUNTI_VITTORIA, "V")
            _registra_esito(stats, casa_id, gf_casa, gf_trasf, PUNTI_SCONFITTA, "S")

    righe = list(stats.values())
    for r in righe:
        r["differenza_reti"] = r["gol_fatti"] - r["gol_subiti"]

    righe.sort(
        key=lambda r: (
            -r["punti"],
            -r["differenza_reti"],
            -r["gol_fatti"],
            r["nome"].lower(),
        )
    )
    for pos, r in enumerate(righe, start=1):
        r["posizione"] = pos

    return {
        "sport": {
            "id": sport.id,
            "nome": sport.nome,
            "tipo_risultato": sport.tipo_risultato,
        },
        "pareggio_consentito": allow_draw,
        "punti_vittoria": PUNTI_VITTORIA,
        "punti_pareggio": PUNTI_PAREGGIO if allow_draw else None,
        "giornate_liquidate": len(giornate_ids),
        "classifica": righe,
    }


def calcola_classifiche_attive() -> list[dict]:
    """Elenco classifiche per tutti gli sport attivi con almeno una giornata liquidata."""
    risultati = []
    for sport in SportScommesse.objects.filter(attivo=True).order_by("nome"):
        data = calcola_classifica_sport(sport.id)
        if data and data["giornate_liquidate"] > 0:
            risultati.append(data)
    return risultati
