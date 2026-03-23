from django.utils import timezone
from django.db.models import Count
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.models import Evento
from personaggi.models import Personaggio, PersonaggioKorpMembership

from .models import (
    SOCIAL_VISIBILITY_KORP,
    SocialComment,
    SocialCommentTag,
    SocialLike,
    SocialPost,
    SocialPostTag,
    SocialProfile,
    extract_mentioned_personaggi_ids,
)
from .serializers import (
    SocialCommentSerializer,
    SocialPostSerializer,
    SocialProfilePublicSerializer,
    SocialProfileSerializer,
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

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAdminUser()]
        if self.action in {"create", "like", "comments"}:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return [permissions.IsAuthenticatedOrReadOnly()]

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
        post = serializer.save(autore=personaggio, evento=get_evento_in_corso())
        self._sync_tags_for_post(post)

    def perform_update(self, serializer):
        post = serializer.save()
        self._sync_tags_for_post(post)

    def _sync_tags_for_post(self, post):
        ids = extract_mentioned_personaggi_ids(post.testo)
        SocialPostTag.objects.filter(post=post).exclude(personaggio_id__in=ids).delete()
        existing = set(SocialPostTag.objects.filter(post=post).values_list("personaggio_id", flat=True))
        SocialPostTag.objects.bulk_create(
            [SocialPostTag(post=post, personaggio_id=pid) for pid in ids if pid not in existing]
        )

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
        comment = serializer.save(post=post, autore=personaggio, evento=get_evento_in_corso())
        self._sync_tags_for_comment(comment)
        return Response(SocialCommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    def _sync_tags_for_comment(self, comment):
        ids = extract_mentioned_personaggi_ids(comment.testo)
        SocialCommentTag.objects.filter(comment=comment).exclude(personaggio_id__in=ids).delete()
        existing = set(SocialCommentTag.objects.filter(comment=comment).values_list("personaggio_id", flat=True))
        SocialCommentTag.objects.bulk_create(
            [SocialCommentTag(comment=comment, personaggio_id=pid) for pid in ids if pid not in existing]
        )


class SocialProfileMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_or_create_profile(self, request):
        requested = request.query_params.get("personaggio_id") or request.data.get("personaggio_id")
        personaggio = resolve_active_personaggio(request.user, requested)
        if not personaggio:
            return None
        profile, _ = SocialProfile.objects.get_or_create(personaggio=personaggio)
        return profile

    def get(self, request):
        profile = self._get_or_create_profile(request)
        if not profile:
            return Response({"detail": "Nessun personaggio trovato."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SocialProfileSerializer(profile).data)

    def put(self, request):
        profile = self._get_or_create_profile(request)
        if not profile:
            return Response({"detail": "Nessun personaggio trovato."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SocialProfileSerializer(profile, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        profile = self._get_or_create_profile(request)
        if not profile:
            return Response({"detail": "Nessun personaggio trovato."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SocialProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SocialProfileDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, personaggio_id):
        personaggio = Personaggio.objects.filter(id=personaggio_id).first()
        if not personaggio:
            return Response({"detail": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        profile, _ = SocialProfile.objects.get_or_create(personaggio=personaggio)
        return Response(SocialProfilePublicSerializer(profile).data)


class SocialPublicPostDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        post = SocialPost.objects.filter(public_slug=slug, visibilita="PUB").first()
        if not post:
            return Response({"detail": "Post pubblico non trovato."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SocialPostSerializer(post, context={"request": request, "personaggio": None})
        return Response(serializer.data)


class SocialStaffEventReportView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        evento_id = request.query_params.get("evento_id")
        eventi_qs = Evento.objects.order_by("-data_inizio")
        if evento_id:
            eventi_qs = eventi_qs.filter(id=evento_id)

        eventi = list(eventi_qs.values("id", "titolo", "data_inizio", "data_fine"))
        evento_ids = [e["id"] for e in eventi]

        if not evento_ids:
            return Response({"eventi": [], "rows": [], "totali": {"post": 0, "commenti": 0}})

        post_counts = (
            SocialPost.objects.filter(evento_id__in=evento_ids)
            .values("evento_id", "autore_id", "autore__nome")
            .annotate(post_count=Count("id"))
        )
        comment_counts = (
            SocialComment.objects.filter(evento_id__in=evento_ids)
            .values("evento_id", "autore_id", "autore__nome")
            .annotate(comment_count=Count("id"))
        )

        rows_map = {}
        for row in post_counts:
            key = (row["evento_id"], row["autore_id"])
            rows_map[key] = {
                "evento_id": row["evento_id"],
                "personaggio_id": row["autore_id"],
                "personaggio_nome": row["autore__nome"],
                "post_count": row["post_count"],
                "comment_count": 0,
            }

        for row in comment_counts:
            key = (row["evento_id"], row["autore_id"])
            if key not in rows_map:
                rows_map[key] = {
                    "evento_id": row["evento_id"],
                    "personaggio_id": row["autore_id"],
                    "personaggio_nome": row["autore__nome"],
                    "post_count": 0,
                    "comment_count": row["comment_count"],
                }
            else:
                rows_map[key]["comment_count"] = row["comment_count"]

        rows = sorted(
            [
                {
                    **r,
                    "totale": int(r["post_count"]) + int(r["comment_count"]),
                }
                for r in rows_map.values()
            ],
            key=lambda x: (x["evento_id"], -x["totale"], x["personaggio_nome"] or ""),
        )

        return Response(
            {
                "eventi": eventi,
                "rows": rows,
                "totali": {
                    "post": sum(int(r["post_count"]) for r in rows),
                    "commenti": sum(int(r["comment_count"]) for r in rows),
                },
            }
        )
