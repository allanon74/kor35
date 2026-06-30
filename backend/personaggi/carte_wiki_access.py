"""
Visibilità Wiki regolamento carte in base a accesso_modo della campagna.
"""
from __future__ import annotations

from django.contrib.auth.models import AnonymousUser

from personaggi.carte_collezionabili_models import CARTE_ACCESSO_OPEN
from personaggi.carte_collezionabili_service import get_carte_accesso_modo
from personaggi.models import (
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
)

CARTE_WIKI_SECTION_SLUG = "gioco-carte"
CARTE_WIKI_REGOLAMENTO_SLUG = "carte-collezionabili-regolamento"
CARTE_WIKI_KEYWORDS_STAFF_SLUG = "carte-keywords-staff"
CARTE_WIKI_SLUGS = frozenset({
    CARTE_WIKI_SECTION_SLUG,
    CARTE_WIKI_REGOLAMENTO_SLUG,
})


def _wiki_effective_user(request):
    if request.user.is_authenticated:
        return request.user
    auth_header = (request.headers.get("Authorization") or "").strip()
    if auth_header.lower().startswith("token ") and request.user.is_authenticated:
        return request.user
    return AnonymousUser()


def utente_puo_vedere_wiki_carte_regolamento(request, user=None) -> bool:
    """
    Staff campagna: sempre.
    Giocatori: solo se accesso_modo == OPEN per la campagna attiva (header X-Campagna).
    """
    from gestione_plot.views import (
        _campaign_role_for_request,
        _get_active_campaign_for_request,
        _is_global_admin,
    )

    effective = user if user is not None else _wiki_effective_user(request)
    if _is_global_admin(effective):
        return True
    role = _campaign_role_for_request(request, user_override=effective)
    if role in (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER):
        return True

    campagna = _get_active_campaign_for_request(request)
    if not campagna:
        return False
    return get_carte_accesso_modo(campagna) == CARTE_ACCESSO_OPEN


def filtra_queryset_wiki_carte(queryset, request, user=None):
    if utente_puo_vedere_wiki_carte_regolamento(request, user=user):
        return queryset
    return queryset.exclude(slug__in=CARTE_WIKI_SLUGS)
