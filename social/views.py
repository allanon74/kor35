from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from gestione_plot.models import Evento
from personaggi.models import PersonaggioKorpMembership

from .models import SOCIAL_VISIBILITY_KORP, SocialComment, SocialLike, SocialPost, SocialProfile
from .serializers import (
    SocialCommentSerializer,
    SocialPostSerializer,
    SocialProfileSerializer,
    get_active_korp,
    resolve_active_personaggio,
    visible_posts_queryset_for_personaggio,
)


def get_evento_in_corso(reference_dt=None):
    now = reference_dt or timezone.now()
    return (
        Evento.objects.filter(data_inizio__lte=now, data_fine__gte=now)
        .order_by("data_inizio")
        .first()
    )


class SocialPostViewSet(viewsets.ModelViewSet):
    serializer_class = SocialPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_personaggio(self):
        if not self.request.user.is_authenticated:
            return None
        requested = self.request.query_params.get("personaggio_id") or self.request.data.get("personaggio_id")
        return resolve_active_personaggio(self.request.user, requested)

    def get_queryset(self):
        personaggio = self.get_personaggio()
        return visible_posts_queryset_for_personaggio(personaggio)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["personaggio"] = self.get_personaggio()
        return ctx

    def perform_create(self, serializer):
        personaggio = self.get_personaggio()
        if not personaggio:
            raise permissions.PermissionDenied("Nessun personaggio selezionabile per questo utente.")
        visibilita = serializer.validated_data.get("visibilita")
        korp_visibilita = serializer.validated_data.get("korp_visibilita")
        if visibilita == SOCIAL_VISIBILITY_KORP:
            if not korp_visibilita:
                raise permissions.PermissionDenied("Serve una KORP per post riservato.")
            is_member = PersonaggioKorpMembership.objects.filter(
                personaggio=personaggio, korp=korp_visibilita, data_a__isnull=True
            ).exists()
            if not is_member:
                raise permissions.PermissionDenied("Il personaggio non appartiene alla KORP selezionata.")
        serializer.save(autore=personaggio, evento=get_evento_in_corso())

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        like, created = SocialLike.objects.get_or_create(post=post, autore=personaggio)
        if not created:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)
        return Response({"liked": True}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        post = self.get_object()
        if request.method.lower() == "get":
            qs = post.comments.select_related("autore", "evento").all()
            serializer = SocialCommentSerializer(qs, many=True)
            return Response(serializer.data)

        if not request.user.is_authenticated:
            raise permissions.PermissionDenied("Login richiesto.")
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SocialCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post, autore=personaggio, evento=get_evento_in_corso())
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SocialProfileMeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_or_create_profile(self, request):
        requested = request.query_params.get("personaggio_id") or request.data.get("personaggio_id")
        personaggio = resolve_active_personaggio(request.user, requested)
        if not personaggio:
            return None, None
        profile, _ = SocialProfile.objects.get_or_create(personaggio=personaggio)
        return personaggio, profile

    def list(self, request):
        _, profile = self._get_or_create_profile(request)
        if not profile:
            return Response({"detail": "Nessun personaggio trovato."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SocialProfileSerializer(profile).data)

    def update(self, request, pk=None):
        _, profile = self._get_or_create_profile(request)
        if not profile:
            return Response({"detail": "Nessun personaggio trovato."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SocialProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
