from __future__ import annotations

from django.http import HttpResponseForbidden, JsonResponse

from gestione_plot.models import ConfigurazioneSito


class MaintenanceModeMiddleware:
    """
    Blocca aree applicative quando la manutenzione e attiva.
    - Solo superuser puo usare /admin/
    - Sezioni gioco/social/staff/pilotaggio bloccate per tutti
    """

    BLOCKED_API_PREFIXES = (
        "/api/personaggi/",
        "/api/social/",
        "/api/pilot/",
        "/api/plot/api/staff/",
        "/api/plot/api/eventi",
        "/api/plot/api/giorni",
        "/api/plot/api/quests",
        "/api/plot/api/mostri-istanza",
        "/api/plot/api/viste-setup",
        "/api/plot/api/png-assegnati",
        "/api/plot/api/fasi",
        "/api/plot/api/tasks",
        "/api/plot/iscrizioni-evento/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        config = ConfigurazioneSito.get_config()
        if not config.maintenance_mode:
            return self.get_response(request)

        path = request.path or "/"

        if path.startswith("/admin/"):
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)
            return HttpResponseForbidden("Maintenance mode: console riservata agli admin generali.")

        if path.startswith(self.BLOCKED_API_PREFIXES):
            return JsonResponse(
                {
                    "detail": "Sistema in manutenzione.",
                    "maintenance_mode": True,
                    "maintenance_message": config.maintenance_public_message,
                },
                status=503,
            )

        return self.get_response(request)
