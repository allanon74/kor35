"""
Permission DRF per l'app pilotaggio.
"""
from __future__ import annotations

from rest_framework import permissions

from .models import PilotConsoleToken


class IsPilotConsole(permissions.BasePermission):
    """Richiede un token console pilota valido."""

    message = "Token console pilota richiesto."

    def has_permission(self, request, view):
        token = getattr(request, "auth", None)
        return isinstance(token, PilotConsoleToken) and token.attivo


class IsScientificConsole(permissions.BasePermission):
    """Token console valido + statistica scientifica sul personaggio."""

    message = "Accesso console scientifica non autorizzato."

    def has_permission(self, request, view):
        from .navigation_stats import scientifica_stat_sigla
        from .models import PilotRuntimeConfig

        token = getattr(request, "auth", None)
        if not isinstance(token, PilotConsoleToken) or not token.attivo:
            return False
        cfg = PilotRuntimeConfig.get_solo()
        if not cfg.scientifica_console_abilitata:
            return False
        pilota = token.pilota
        if pilota is None:
            return False
        return int(pilota.get_valore_statistica(scientifica_stat_sigla(cfg)) or 0) > 0


class IsStaffUser(permissions.BasePermission):
    """Permission staff per CRUD configurazione (require is_staff)."""

    message = "Permesso staff richiesto."

    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and u.is_staff)
