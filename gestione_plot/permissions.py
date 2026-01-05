from rest_framework import permissions

class IsMasterOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Consenti l'accesso se l'utente è loggato ed è o superuser o staff
        return request.user and request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)