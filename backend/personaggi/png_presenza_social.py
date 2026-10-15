"""
Presenza social opzionale dei PnG.

I personaggi giocanti ignorano i flag e restano sempre taggabili, chiamabili,
destinatari di messaggi e abilitati a pubblicare su InstaFame.

Funzioni lasciate sempre attive (non c'è un interruttore dedicato):
- commenti, like e reazioni alle storie;
- chat e inviti dei gruppi InstaFame (il post nel gruppo segue invece la pubblicazione);
- rubriche (autore e permessi li assegna lo staff);
- cessioni, innesti, negozio e le altre ricerche di gioco;
- messaggi inviati dallo staff dal tool messaggi (non dalla composizione del giocatore).
"""

from __future__ import annotations

from django.db.models import Q

CAMPO_TAG = "png_tag_instafame"
CAMPO_CHIAMATA = "png_chiamabile"
CAMPO_MESSAGGIO = "png_destinatario_messaggi"
CAMPO_PUBBLICAZIONE = "png_pubblica_instafame"

CAMPI_USO = {
    "menzione": CAMPO_TAG,
    "chiamata": CAMPO_CHIAMATA,
    "messaggio": CAMPO_MESSAGGIO,
    "pubblicazione": CAMPO_PUBBLICAZIONE,
}

CHIAVI_PAYLOAD = {
    "tag_instafame": CAMPO_TAG,
    "chiamabile": CAMPO_CHIAMATA,
    "destinatario_messaggi": CAMPO_MESSAGGIO,
    "pubblica_instafame": CAMPO_PUBBLICAZIONE,
}


def personaggio_e_png(personaggio) -> bool:
    if personaggio is None:
        return False
    tipologia = getattr(personaggio, "tipologia", None)
    if tipologia is None:
        return False
    return not bool(tipologia.giocante)


def funzione_social_abilitata(personaggio, campo: str) -> bool:
    """True per i PG. Per i PnG vale il flag salvato."""
    if personaggio is None:
        return False
    if not personaggio_e_png(personaggio):
        return True
    return bool(getattr(personaggio, campo, True))


def queryset_presenza_social(qs, uso: str | None):
    """Restringe una ricerca personaggi all'uso social richiesto. Senza uso non filtra."""
    campo = CAMPI_USO.get((uso or "").strip().lower())
    if not campo:
        return qs
    return qs.filter(
        Q(tipologia__giocante=True) | Q(tipologia__isnull=True) | Q(**{campo: True})
    )


def filtra_ids_funzione(ids, campo: str) -> list[int]:
    if not ids:
        return []
    return list(
        qs_ids(ids).filter(
            Q(tipologia__giocante=True) | Q(tipologia__isnull=True) | Q(**{campo: True})
        ).values_list("id", flat=True)
    )


def qs_ids(ids):
    from personaggi.models import Personaggio

    return Personaggio.objects.filter(id__in=list(ids))


def _come_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    testo = str(value or "").strip().lower()
    if testo in {"1", "true", "yes", "on", "si", "sì"}:
        return True
    if testo in {"0", "false", "no", "off"}:
        return False
    return bool(value)


def presenza_social_payload(personaggio, *, user=None) -> dict:
    from personaggi.chiamate_vocali import user_is_campaign_staff

    e_png = personaggio_e_png(personaggio)
    autenticato = bool(user and getattr(user, "is_authenticated", False))
    modificabile = bool(
        e_png and autenticato and user_is_campaign_staff(user, getattr(personaggio, "campagna", None))
    )
    return {
        "e_png": e_png,
        "modificabile": modificabile,
        "tag_instafame": funzione_social_abilitata(personaggio, CAMPO_TAG),
        "chiamabile": funzione_social_abilitata(personaggio, CAMPO_CHIAMATA),
        "destinatario_messaggi": funzione_social_abilitata(personaggio, CAMPO_MESSAGGIO),
        "pubblica_instafame": funzione_social_abilitata(personaggio, CAMPO_PUBBLICAZIONE),
    }


def applica_presenza_social(personaggio, raw, user) -> bool:
    """
    Aggiorna i flag sul PnG se l'utente è staff di campagna.
    ``raw`` è il dict ``presenza_social`` (chiavi corte).
    """
    from personaggi.chiamate_vocali import user_is_campaign_staff

    if not isinstance(raw, dict):
        return False
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if not user_is_campaign_staff(user, getattr(personaggio, "campagna", None)):
        return False
    if not personaggio_e_png(personaggio):
        return False
    changed = []
    for chiave, campo in CHIAVI_PAYLOAD.items():
        if chiave not in raw or raw[chiave] is None:
            continue
        setattr(personaggio, campo, _come_bool(raw[chiave]))
        changed.append(campo)
    if not changed:
        return False
    personaggio.save(update_fields=changed + ["updated_at"])
    return True


def messaggio_verso_personaggio_consentito(mittente, destinatario) -> tuple[bool, str]:
    """
    Il PnG escluso dai destinatari non compare nelle nuove conversazioni.
    Se ha già scritto al mittente, la risposta resta consentita.
    """
    if destinatario is None or mittente is None:
        return True, ""
    if funzione_social_abilitata(destinatario, CAMPO_MESSAGGIO):
        return True, ""
    from personaggi.models import Messaggio

    gia_scritto = Messaggio.objects.filter(
        mittente_personaggio=destinatario,
        destinatario_personaggio=mittente,
        tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
    ).exists()
    if gia_scritto:
        return True, ""
    nome = getattr(destinatario, "nome", None) or "Questo personaggio"
    return False, f"{nome} non compare tra i destinatari dei messaggi."


def richiedi_pubblicazione_instafame(personaggio):
    from rest_framework.exceptions import PermissionDenied

    if funzione_social_abilitata(personaggio, CAMPO_PUBBLICAZIONE):
        return
    nome = getattr(personaggio, "nome", None) or "Questo personaggio"
    raise PermissionDenied(f"{nome} non può pubblicare su InstaFame.")
