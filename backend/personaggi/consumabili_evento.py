"""Gate alchimia: i consumabili si creano solo a evento aperto, con il PG iscritto."""
from __future__ import annotations

from personaggi.transazioni_evento import get_evento_aperto_corso

MSG_EVENTO_CHIUSO = (
    "Puoi creare consumabili con l'alchimia solo durante un evento aperto."
)
MSG_NON_ISCRITTO = (
    "Puoi creare consumabili con l'alchimia solo se questo personaggio "
    "è iscritto all'evento aperto."
)


def esito_creazione_consumabile_alchimia(personaggio, now=None) -> tuple[bool, str]:
    """
    (True, "") se c'è un evento aperto e il personaggio è tra i partecipanti.
    Altrimenti (False, messaggio da mostrare al giocatore).
    """
    if personaggio is None:
        return False, MSG_EVENTO_CHIUSO
    evento = get_evento_aperto_corso(now)
    if evento is None:
        return False, MSG_EVENTO_CHIUSO
    if not evento.partecipanti.filter(pk=personaggio.pk).exists():
        return False, MSG_NON_ISCRITTO
    return True, ""
