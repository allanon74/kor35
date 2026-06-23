"""
Filtri e validazioni per il catalogo Accademia (negozio ufficiale in app Personaggio).
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import QuerySet

MSG_NON_VENDIBILE = "Questo contenuto non è vendibile."
MSG_ESCLUSO_ACCADEMIA = "Disponibile solo presso negozi speciali (non in Accademia)."


def oggetto_base_accademia_qs() -> QuerySet:
    from .models import OggettoBase

    return OggettoBase.objects.filter(
        in_vendita=True,
        escluso_negozio_ufficiale=False,
        non_vendibile=False,
    )


def abilita_accademia_filter(qs: QuerySet | None = None) -> QuerySet:
    from .models import Abilita

    base = qs if qs is not None else Abilita.objects.all()
    return base.filter(
        escluso_negozio_ufficiale=False,
        non_vendibile=False,
    )


def tecnica_visibile_in_accademia(tecnica) -> bool:
    """True se la tecnica può comparire nel catalogo Accademia (tab Nuove / acquisti)."""
    if getattr(tecnica, "non_vendibile", False):
        return False
    if getattr(tecnica, "escluso_negozio_ufficiale", False):
        return False
    if getattr(tecnica, "non_acquistabile", False):
        return False
    return True


def tecnica_in_catalogo_accademia_ufficiale(tecnica) -> bool:
    """Alias esplicito per regole scambio: tecnica ancora vendibile dall'Accademia ufficiale."""
    return tecnica_visibile_in_accademia(tecnica)


def oggetto_in_catalogo_accademia_ufficiale(oggetto) -> bool:
    """True se l'oggetto (o il suo template) è nel catalogo Accademia ufficiale."""
    ob = getattr(oggetto, "oggetto_base", None)
    if ob is not None:
        return oggetto_base_accademia_qs().filter(pk=ob.pk).exists()
    return bool(
        getattr(oggetto, "in_vendita", False)
        and not getattr(oggetto, "escluso_negozio_ufficiale", False)
        and not getattr(oggetto, "non_vendibile", False)
    )


def verifica_oggetto_base_accademia(template) -> None:
    if getattr(template, "non_vendibile", False):
        raise ValidationError(MSG_NON_VENDIBILE)
    if getattr(template, "escluso_negozio_ufficiale", False):
        raise ValidationError(MSG_ESCLUSO_ACCADEMIA)
    if not template.in_vendita:
        raise ValidationError("Questo oggetto non è più in vendita.")


def verifica_abilita_accademia(abilita) -> None:
    if getattr(abilita, "non_vendibile", False):
        raise ValidationError(MSG_NON_VENDIBILE)
    if getattr(abilita, "escluso_negozio_ufficiale", False):
        raise ValidationError(MSG_ESCLUSO_ACCADEMIA)


def verifica_tecnica_accademia(tecnica) -> None:
    if getattr(tecnica, "non_vendibile", False):
        raise ValidationError(MSG_NON_VENDIBILE)
    if getattr(tecnica, "escluso_negozio_ufficiale", False):
        raise ValidationError(MSG_ESCLUSO_ACCADEMIA)
    if getattr(tecnica, "non_acquistabile", False):
        raise ValidationError(
            "Questa tecnica non è acquistabile dall'Accademia: usa negozi speciali o QR."
        )
