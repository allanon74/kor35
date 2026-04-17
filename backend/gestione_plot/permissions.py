from rest_framework import permissions

from personaggi.models import (
    Campagna,
    CampagnaUtente,
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
)


def _get_active_campaign_for_request(request):
    slug = (request.headers.get("X-Campagna") or request.query_params.get("campagna") or "kor35").strip().lower()
    campagna = Campagna.objects.filter(slug=slug, attiva=True).first()
    if campagna:
        return campagna
    return Campagna.objects.filter(attiva=True, is_default=True).first() or Campagna.objects.filter(slug="kor35").first()


class IsStaffOrMaster(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True
        active_campaign = _get_active_campaign_for_request(request)
        if not active_campaign:
            return False
        role = (
            CampagnaUtente.objects.filter(user=user, campagna=active_campaign, attivo=True)
            .values_list("ruolo", flat=True)
            .first()
        )
        return role in (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)