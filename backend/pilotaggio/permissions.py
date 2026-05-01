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


class IsStaffUser(permissions.BasePermission):
    """Permission staff per CRUD configurazione (require is_staff)."""

    message = "Permesso staff richiesto."

    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and u.is_staff)
