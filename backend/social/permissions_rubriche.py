"""Permessi rubriche InstaFame.

- Creare/modificare/eliminare rubriche: master+ (o superuser).
- Scrivere articoli: staff+ su qualsiasi rubrica; personaggi solo con permesso esplicito.
- Leggere: qualsiasi personaggio autenticato (gate modulo social).
"""

from rest_framework import permissions

from gestione_plot.permissions import _get_active_campaign_for_request
from personaggi.models import (
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
    CampagnaUtente,
)

RUOLI_STAFF = (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)
RUOLI_MASTER = (CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def ruolo_campagna_per_request(request):
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return None
    campagna = _get_active_campaign_for_request(request)
    if not campagna:
        return None
    return (
        CampagnaUtente.objects.filter(user=user, campagna=campagna, attivo=True)
        .values_list("ruolo", flat=True)
        .first()
    )


def is_staff_rubriche(request) -> bool:
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return False
    if user.is_superuser:
        return True
    return ruolo_campagna_per_request(request) in RUOLI_STAFF


def is_master_rubriche(request) -> bool:
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return False
    if user.is_superuser:
        return True
    return ruolo_campagna_per_request(request) in RUOLI_MASTER


def personaggio_puo_scrivere(rubrica, personaggio) -> bool:
    """Permesso in-game: il personaggio è stato autorizzato dallo staff su questa rubrica."""
    if not (rubrica and personaggio):
        return False
    return rubrica.permessi_scrittura.filter(personaggio=personaggio, attivo=True).exists()


def rubriche_scrivibili_ids(personaggio):
    from .models_rubriche import RubricaPermessoScrittura

    if not personaggio:
        return set()
    return set(
        RubricaPermessoScrittura.objects.filter(personaggio=personaggio, attivo=True).values_list(
            "rubrica_id", flat=True
        )
    )


class IsRubricaReadOrMaster(permissions.BasePermission):
    """Lettura per autenticati, scrittura sulle rubriche solo per master+."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_master_rubriche(request)


class IsArticoloAuthenticated(permissions.BasePermission):
    """Il controllo fine (staff vs permesso in-game) è nella view, per articolo."""

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated)
