from datetime import datetime
import logging

from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Exists, F, OuterRef, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.models import Evento
from personaggi.models import Messaggio, Personaggio, get_active_korp_ids, PersonaggioCarrieraMembership

from .post_media import apply_post_media_from_request
from .display_names import social_display_name
from .mention_notifications import format_mention_message, instafame_deep_link_path
from .models import (
    SOCIAL_GROUP_ROLE_ADMIN,
    SOCIAL_GROUP_ROLE_MEMBER,
    SOCIAL_GROUP_STATUS_ACTIVE,
    SOCIAL_GROUP_STATUS_INVITED,
    SOCIAL_GROUP_STATUS_REJECTED,
    SOCIAL_GROUP_STATUS_REQUESTED,
    SOCIAL_VISIBILITY_KORP,
    SocialComment,
    SocialCommentLike,
    SocialCommentTag,
    SocialGroup,
    SocialGroupMembership,
    SocialGroupMessage,
    SocialGroupPost,
    SocialLike,
    SocialPost,
    SocialPostImage,
    SocialPostTag,
    SocialProfile,
    SocialStory,
    SocialStoryHighlight,
    SocialStoryHighlightItem,
    SocialStoryReaction,
    SocialStoryReply,
    SocialStoryTag,
    SocialStoryView,
    extract_mentioned_personaggi_ids,
    social_story_active_q,
    social_story_expired_q,
)
from .influencer import (
    compute_like_peso,
    random_likes_base,
    rigenera_like_personaggio,
)
from .serializers import (
    SocialCommentSerializer,
    SocialGroupMembershipSerializer,
    SocialGroupMessageSerializer,
    SocialGroupPostSerializer,
    SocialGroupSerializer,
    SocialPostSerializer,
    SocialProfilePublicSerializer,
    SocialProfileSerializer,
    SocialStoryHighlightSerializer,
    SocialStoryReplySerializer,
    SocialStorySerializer,
    resolve_active_personaggio,
    visible_posts_queryset_for_personaggio,
)

logger = logging.getLogger(__name__)


def get_evento_in_corso(reference_dt=None):
    now = reference_dt or timezone.now()
    manuale = (
        Evento.objects.filter(started_at__isnull=False, ended_at__isnull=True)
        .order_by("started_at")
        .first()
    )
    if manuale:
        return manuale
    return Evento.objects.filter(data_inizio__lte=now, data_fine__gte=now).order_by("data_inizio").first()


class SocialPostPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 50


class SocialCommentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 30


class SocialGroupPostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 30


class SocialGroupMessagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class SocialGroupMemberPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class SocialStoryPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


def visible_stories_queryset_for_personaggio(personaggio):
    now = timezone.now()
    base = (
        SocialStory.objects.select_related("autore", "autore__social_profile", "evento", "korp_visibilita")
        .filter(social_story_active_q(now))
        .annotate(
            views_count=Count("views", distinct=True),
            reactions_count=Count("reactions", distinct=True),
        )
    )
    from .serializers import _apply_social_author_campaign_filter

    base = _apply_social_author_campaign_filter(base, getattr(personaggio, "_social_request", None))
    if not personaggio:
        return base.filter(visibilita="PUB")
    active_korp_ids = get_active_korp_ids(personaggio)
    if not active_korp_ids:
        return base.filter(visibilita="PUB")
    return base.filter(
        Q(visibilita="PUB") | Q(visibilita="KORP", korp_visibilita_id__in=active_korp_ids)
    ).distinct()


def sync_story_tags(story):
    ids = extract_mentioned_personaggi_ids(story.testo)
    existing = set(SocialStoryTag.objects.filter(story=story).values_list("personaggio_id", flat=True))
    new_ids = [pid for pid in ids if pid not in existing]
    SocialStoryTag.objects.filter(story=story).exclude(personaggio_id__in=ids).delete()
    SocialStoryTag.objects.bulk_create(
        [SocialStoryTag(story=story, personaggio_id=pid) for pid in new_ids]
    )
    if new_ids:
        from .mention_notifications import notify_instafame_mentions

        notify_instafame_mentions(story.autore, new_ids, "story", story=story)


def sync_post_tags(post):
    text = f"{post.titolo or ''}\n{post.testo or ''}".strip()
    ids = extract_mentioned_personaggi_ids(text)
    existing = set(SocialPostTag.objects.filter(post=post).values_list("personaggio_id", flat=True))
    new_ids = [pid for pid in ids if pid not in existing]
    SocialPostTag.objects.filter(post=post).exclude(personaggio_id__in=ids).delete()
    SocialPostTag.objects.bulk_create(
        [SocialPostTag(post=post, personaggio_id=pid) for pid in new_ids]
    )
    if new_ids:
        from .mention_notifications import notify_instafame_mentions

        notify_instafame_mentions(post.autore, new_ids, "post", post=post)


class SocialStoryViewSet(viewsets.ModelViewSet):
    serializer_class = SocialStorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = SocialStoryPagination

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAdminUser()]
        if self.action in {"create", "viewed", "react", "reply", "replies", "highlights", "add_to_highlight"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_personaggio(self):
        if not self.request.user.is_authenticated:
            return None
        requested = self.request.query_params.get("personaggio_id") or self.request.data.get("personaggio_id")
        personaggio = resolve_active_personaggio(self.request.user, requested, request=self.request)
        if personaggio:
            setattr(personaggio, "_social_request", self.request)
        return personaggio

    def get_queryset(self):
        personaggio = self.get_personaggio()
        # Non bloccare mai la fruizione stories se la conversione automatica fallisce.
        try:
            self._auto_convert_expired_stories()
        except Exception:
            logger.exception("Auto-conversione stories scadute fallita")
        return visible_stories_queryset_for_personaggio(personaggio)

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
                raise permissions.PermissionDenied("Serve una KORP per story riservata.")
            is_member = PersonaggioCarrieraMembership.objects.filter(
                personaggio=personaggio, carriera=korp_visibilita, data_a__isnull=True
            ).exists()
            if not is_member:
                raise permissions.PermissionDenied("Il personaggio non appartiene alla KORP selezionata.")
        story = serializer.save(autore=personaggio, evento=get_evento_in_corso())
        sync_story_tags(story)
        if story.auto_publish_mode == SocialStory.AUTO_PUBLISH_NOW:
            try:
                self._promote_story_to_post(story)
            except Exception:
                logger.exception("Conversione immediata story->post fallita (story_id=%s)", story.id)

    def perform_update(self, serializer):
        story = serializer.save()
        sync_story_tags(story)
        if story.auto_publish_mode == SocialStory.AUTO_PUBLISH_NOW and not story.converted_post_id:
            try:
                self._promote_story_to_post(story)
            except Exception:
                logger.exception("Conversione immediata story->post fallita in update (story_id=%s)", story.id)

    def _auto_convert_expired_stories(self):
        now = timezone.now()
        qs = SocialStory.objects.filter(
            auto_publish_mode=SocialStory.AUTO_PUBLISH_ON_EXPIRE,
            converted_post__isnull=True,
        ).filter(social_story_expired_q(now))[:50]
        for s in qs:
            try:
                self._promote_story_to_post(s)
            except Exception:
                logger.exception("Auto-conversione a scadenza fallita (story_id=%s)", s.id)

    def _promote_story_to_post(self, story):
        if story.converted_post_id:
            return story.converted_post
        titolo = (story.testo or "").strip().split("\n")[0][:180] if story.testo else "Story convertita"
        post = SocialPost.objects.create(
            autore=story.autore,
            titolo=titolo or "Story convertita",
            testo=story.testo or "",
            visibilita=story.visibilita,
            korp_visibilita=story.korp_visibilita if story.visibilita == SOCIAL_VISIBILITY_KORP else None,
            evento=story.evento,
            created_at=story.created_at,
            likes_base=random_likes_base(story.autore),
        )
        if story.media:
            name = str(story.media.name or "").lower()
            if name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                SocialPostImage.objects.create(post=post, immagine=story.media, ordine=0)
            else:
                post.video = story.media
                post.save(update_fields=["video", "updated_at"])
        sync_post_tags(post)

        # Migra replies -> commenti post
        for rp in story.replies.select_related("autore", "autore__social_profile").all():
            c = SocialComment.objects.create(
                post=post,
                autore=rp.autore,
                testo=rp.testo,
                evento=story.evento,
                created_at=rp.created_at,
                likes_base=random_likes_base(rp.autore),
            )
            ids = extract_mentioned_personaggi_ids(c.testo)
            existing = set(SocialCommentTag.objects.filter(comment=c).values_list("personaggio_id", flat=True))
            SocialCommentTag.objects.bulk_create(
                [SocialCommentTag(comment=c, personaggio_id=pid) for pid in ids if pid not in existing]
            )

        # Migra reactions -> like post (1 per autore)
        for r in story.reactions.select_related("autore", "autore__social_profile").all():
            peso = compute_like_peso(r.autore, post.autore)
            like, created = SocialLike.objects.get_or_create(
                post=post,
                autore=r.autore,
                defaults={"created_at": r.created_at, "peso_like": peso},
            )
            if not created and not like.peso_like:
                like.peso_like = peso
                like.save(update_fields=["peso_like", "updated_at"])

        story.converted_post = post
        story.save(update_fields=["converted_post", "updated_at"])
        return post

    @action(detail=True, methods=["post"])
    def viewed(self, request, pk=None):
        story = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        SocialStoryView.objects.update_or_create(
            story=story,
            viewer=personaggio,
            defaults={"viewed_at": timezone.now()},
        )
        return Response({"viewed": True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def react(self, request, pk=None):
        story = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        emoji = (request.data.get("emoji") or "❤️").strip()
        if len(emoji) > 16:
            return Response({"detail": "Emoji non valida."}, status=status.HTTP_400_BAD_REQUEST)
        existing = SocialStoryReaction.objects.filter(story=story, autore=personaggio).first()
        if existing and existing.emoji == emoji:
            existing.delete()
            return Response({"reacted": False}, status=status.HTTP_200_OK)
        SocialStoryReaction.objects.update_or_create(
            story=story,
            autore=personaggio,
            defaults={"emoji": emoji, "created_at": timezone.now()},
        )
        return Response({"reacted": True, "emoji": emoji}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def replies(self, request, pk=None):
        story = self.get_object()
        if request.method.lower() == "get":
            qs = story.replies.select_related("autore", "autore__social_profile").all()
            serializer = SocialStoryReplySerializer(qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SocialStoryReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = serializer.save(story=story, autore=personaggio)

        # Reply in DM (unified messaging): invia un INDV verso l'autore della story.
        send_dm = request.data.get("send_dm", True)
        try:
            send_dm = bool(send_dm)
        except Exception:
            send_dm = True
        if send_dm and story.autore_id and story.autore_id != personaggio.id:
            Messaggio.objects.create(
                mittente=request.user,
                mittente_personaggio=personaggio,
                tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
                destinatario_personaggio=story.autore,
                titolo=f"Risposta alla tua story",
                testo=reply.testo,
                salva_in_cronologia=True,
                campagna=personaggio.campagna,
            )
        return Response(SocialStoryReplySerializer(reply).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def highlights(self, request):
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response([], status=status.HTTP_200_OK)
        qs = SocialStoryHighlight.objects.filter(owner=personaggio)
        return Response(SocialStoryHighlightSerializer(qs, many=True, context={"personaggio": personaggio}).data)

    @action(detail=False, methods=["post"])
    def create_highlight(self, request):
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        titolo = (request.data.get("titolo") or "").strip()
        if not titolo:
            return Response({"detail": "Titolo obbligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        h = SocialStoryHighlight.objects.create(owner=personaggio, titolo=titolo)
        return Response(SocialStoryHighlightSerializer(h, context={"personaggio": personaggio}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path=r"highlights/(?P<highlight_id>[^/.]+)/add")
    def add_to_highlight(self, request, highlight_id=None):
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        highlight = SocialStoryHighlight.objects.filter(id=highlight_id, owner=personaggio).first()
        if not highlight:
            return Response({"detail": "Highlight non trovato."}, status=status.HTTP_404_NOT_FOUND)
        story_id = request.data.get("story_id")
        story = SocialStory.objects.filter(id=story_id, autore=personaggio).first()
        if not story:
            return Response({"detail": "Story non trovata."}, status=status.HTTP_404_NOT_FOUND)
        SocialStoryHighlightItem.objects.get_or_create(highlight=highlight, story=story)
        return Response({"ok": True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def convert_to_post(self, request, pk=None):
        story = self.get_object()
        personaggio = self.get_personaggio()
        can_convert = request.user.is_staff or request.user.is_superuser or (personaggio and story.autore_id == personaggio.id)
        if not can_convert:
            raise permissions.PermissionDenied("Permessi insufficienti.")
        try:
            post = self._promote_story_to_post(story)
        except Exception:
            logger.exception("Conversione manuale story->post fallita (story_id=%s)", story.id)
            return Response({"detail": "Errore durante la conversione story -> post."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"post_id": post.id, "story_id": story.id}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def my_activity(self, request):
        """
        Summary attività sulle mie stories:
        - visualizzazioni
        - reazioni
        - risposte/commenti (replies)
        """
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response(
                {
                    "totals": {"stories": 0, "views": 0, "reactions": 0, "replies": 0},
                    "stories": [],
                    "events": [],
                }
            )

        qs = (
            SocialStory.objects.filter(autore=personaggio)
            .select_related("autore", "autore__social_profile", "evento", "korp_visibilita")
            .annotate(
                views_count=Count("views", distinct=True),
                reactions_count=Count("reactions", distinct=True),
                replies_count=Count("replies", distinct=True),
            )
            .order_by("-created_at")
        )
        stories = list(qs[:100])

        recent_events = []
        for s in stories[:30]:
            for v in s.views.select_related("viewer", "viewer__social_profile").all()[:10]:
                recent_events.append(
                    {
                        "kind": "view",
                        "created_at": v.viewed_at,
                        "story_id": s.id,
                        "story_text": (s.testo or "")[:80],
                        "actor_id": v.viewer_id,
                        "actor_name": social_display_name(v.viewer),
                        "payload": "",
                    }
                )
            for r in s.reactions.select_related("autore", "autore__social_profile").all()[:10]:
                recent_events.append(
                    {
                        "kind": "reaction",
                        "created_at": r.created_at,
                        "story_id": s.id,
                        "story_text": (s.testo or "")[:80],
                        "actor_id": r.autore_id,
                        "actor_name": social_display_name(r.autore),
                        "payload": r.emoji or "",
                    }
                )
            for rp in s.replies.select_related("autore", "autore__social_profile").all()[:10]:
                recent_events.append(
                    {
                        "kind": "reply",
                        "created_at": rp.created_at,
                        "story_id": s.id,
                        "story_text": (s.testo or "")[:80],
                        "actor_id": rp.autore_id,
                        "actor_name": social_display_name(rp.autore),
                        "payload": (rp.testo or "")[:120],
                    }
                )

        recent_events.sort(key=lambda e: e["created_at"], reverse=True)
        recent_events = recent_events[:120]

        total_views = sum(int(getattr(s, "views_count", 0) or 0) for s in stories)
        total_reactions = sum(int(getattr(s, "reactions_count", 0) or 0) for s in stories)
        total_replies = sum(int(getattr(s, "replies_count", 0) or 0) for s in stories)

        return Response(
            {
                "totals": {
                    "stories": len(stories),
                    "views": total_views,
                    "reactions": total_reactions,
                    "replies": total_replies,
                },
                "stories": [
                    {
                        **SocialStorySerializer(s, context={"personaggio": personaggio, "request": request}).data,
                        "replies_count": int(getattr(s, "replies_count", 0) or 0),
                    }
                    for s in stories
                ],
                "events": [
                    {
                        **e,
                        "created_at": e["created_at"].isoformat() if e["created_at"] else None,
                    }
                    for e in recent_events
                ],
            }
        )

    @action(detail=False, methods=["get"])
    def my_history(self, request):
        """
        Storico stories del personaggio attivo.
        include_expired=true per includere anche scadute (default: true).
        """
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"count": 0, "results": []})
        include_expired = str(request.query_params.get("include_expired", "true")).lower() != "false"
        qs = (
            SocialStory.objects.filter(autore=personaggio)
            .select_related("autore", "autore__social_profile", "evento", "korp_visibilita")
            .annotate(
                views_count=Count("views", distinct=True),
                reactions_count=Count("reactions", distinct=True),
            )
            .order_by("-created_at")
        )
        if not include_expired:
            qs = qs.filter(social_story_active_q())
        rows = [SocialStorySerializer(s, context={"personaggio": personaggio, "request": request}).data for s in qs[:200]]
        return Response({"count": len(rows), "results": rows})


class SocialPostViewSet(viewsets.ModelViewSet):
    serializer_class = SocialPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = SocialPostPagination

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAdminUser()]
        if self.action in {"create", "like", "comments", "comment_like"}:
            return [permissions.IsAuthenticatedOrReadOnly()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_personaggio(self):
        if not self.request.user.is_authenticated:
            return None
        requested = self.request.query_params.get("personaggio_id") or self.request.data.get("personaggio_id")
        return resolve_active_personaggio(self.request.user, requested, request=self.request)

    def get_queryset(self):
        personaggio = self.get_personaggio()
        qs = visible_posts_queryset_for_personaggio(personaggio, request=self.request)
        if personaggio:
            qs = qs.annotate(
                liked_by_me_flag=Exists(
                    SocialLike.objects.filter(post_id=OuterRef("pk"), autore=personaggio)
                )
            )
        hashtag = (self.request.query_params.get("hashtag") or "").strip().lstrip("#")
        if hashtag:
            token = f"#{hashtag}"
            qs = qs.filter(Q(testo__icontains=token) | Q(titolo__icontains=token)).distinct()
        return qs

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
            is_member = PersonaggioCarrieraMembership.objects.filter(
                personaggio=personaggio, carriera=korp_visibilita, data_a__isnull=True
            ).exists()
            if not is_member:
                raise permissions.PermissionDenied("Il personaggio non appartiene alla KORP selezionata.")
        post = serializer.save(autore=personaggio, evento=get_evento_in_corso(), likes_base=random_likes_base(personaggio))
        try:
            apply_post_media_from_request(post, self.request, replace_gallery=True)
        except DjangoValidationError as exc:
            post.delete()
            raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc))
        post.refresh_from_db()
        post.full_clean()
        self._sync_tags_for_post(post)

    def perform_update(self, serializer):
        post = serializer.save()
        try:
            has_new_images = bool(self.request.FILES.getlist("immagini")) or bool(self.request.FILES.get("immagine"))
            apply_post_media_from_request(
                post,
                self.request,
                replace_gallery=has_new_images or str(self.request.data.get("clear_immagini", "")).lower() in {"1", "true", "yes"},
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc))
        post.refresh_from_db()
        post.full_clean()
        self._sync_tags_for_post(post)

    def _sync_tags_for_post(self, post):
        sync_post_tags(post)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        post = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        like = SocialLike.objects.filter(post=post, autore=personaggio).first()
        if like:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)
        peso = compute_like_peso(personaggio, post.autore)
        SocialLike.objects.create(post=post, autore=personaggio, peso_like=peso)
        return Response({"liked": True, "peso_like": peso}, status=status.HTTP_201_CREATED)

    def _comments_queryset(self, post, personaggio=None):
        qs = (
            post.comments.select_related("autore", "autore__social_profile", "evento")
            .annotate(
                _likes_user_sum=Coalesce(Sum("likes__peso_like"), Value(0)),
                likes_total=F("likes_base") + F("_likes_user_sum"),
            )
        )
        if personaggio:
            qs = qs.annotate(
                liked_by_me_flag=Exists(
                    SocialCommentLike.objects.filter(comment_id=OuterRef("pk"), autore=personaggio)
                )
            )
        return qs

    @action(detail=True, methods=["get", "post"], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        post = self.get_object()
        personaggio = self.get_personaggio()
        if request.method.lower() == "get":
            qs = self._comments_queryset(post, personaggio=personaggio)
            paginator = SocialCommentPagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            serializer = SocialCommentSerializer(page, many=True, context=self.get_serializer_context())
            return paginator.get_paginated_response(serializer.data)

        if not request.user.is_authenticated:
            raise permissions.PermissionDenied("Login richiesto.")
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SocialCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(
            post=post,
            autore=personaggio,
            evento=get_evento_in_corso(),
            likes_base=random_likes_base(personaggio),
        )
        self._sync_tags_for_comment(comment)
        return Response(
            SocialCommentSerializer(comment, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path=r"comments/(?P<comment_id>[^/.]+)/like",
    )
    def comment_like(self, request, pk=None, comment_id=None):
        post = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        comment = SocialComment.objects.filter(id=comment_id, post=post).select_related("autore").first()
        if not comment:
            return Response({"detail": "Commento non trovato."}, status=status.HTTP_404_NOT_FOUND)
        like = SocialCommentLike.objects.filter(comment=comment, autore=personaggio).first()
        if like:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)
        peso = compute_like_peso(personaggio, comment.autore)
        SocialCommentLike.objects.create(comment=comment, autore=personaggio, peso_like=peso)
        return Response({"liked": True, "peso_like": peso}, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path=r"comments/(?P<comment_id>[^/.]+)",
    )
    def comment_detail(self, request, pk=None, comment_id=None):
        post = self.get_object()
        personaggio = self.get_personaggio()
        comment = SocialComment.objects.filter(id=comment_id, post=post).first()
        if not comment:
            return Response({"detail": "Commento non trovato."}, status=status.HTTP_404_NOT_FOUND)

        can_moderate = request.user.is_staff or request.user.is_superuser
        can_edit_own = personaggio and comment.autore_id == personaggio.id
        if not (can_moderate or can_edit_own):
            raise permissions.PermissionDenied("Permessi insufficienti per modificare il commento.")

        if request.method.lower() == "delete":
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = SocialCommentSerializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_comment = serializer.save()
        self._sync_tags_for_comment(updated_comment)
        return Response(SocialCommentSerializer(updated_comment).data, status=status.HTTP_200_OK)

    def _sync_tags_for_comment(self, comment):
        ids = extract_mentioned_personaggi_ids(comment.testo)
        existing = set(SocialCommentTag.objects.filter(comment=comment).values_list("personaggio_id", flat=True))
        new_ids = [pid for pid in ids if pid not in existing]
        SocialCommentTag.objects.filter(comment=comment).exclude(personaggio_id__in=ids).delete()
        SocialCommentTag.objects.bulk_create(
            [SocialCommentTag(comment=comment, personaggio_id=pid) for pid in new_ids]
        )
        if new_ids:
            from .mention_notifications import notify_instafame_mentions

            notify_instafame_mentions(comment.autore, new_ids, "comment", comment=comment, post=comment.post)


class SocialGroupViewSet(viewsets.ModelViewSet):
    serializer_class = SocialGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_personaggio(self):
        requested = self.request.query_params.get("personaggio_id") or self.request.data.get("personaggio_id")
        return resolve_active_personaggio(self.request.user, requested, request=self.request)

    def _membership(self, group, personaggio):
        if not personaggio:
            return None
        return group.memberships.filter(personaggio=personaggio).first()

    def _is_active_member(self, group, personaggio):
        m = self._membership(group, personaggio)
        return bool(m and m.status == SOCIAL_GROUP_STATUS_ACTIVE)

    def _is_group_admin(self, group, personaggio):
        m = self._membership(group, personaggio)
        return bool(m and m.status == SOCIAL_GROUP_STATUS_ACTIVE and m.ruolo == SOCIAL_GROUP_ROLE_ADMIN)

    def _active_admin_count(self, group):
        return group.memberships.filter(status=SOCIAL_GROUP_STATUS_ACTIVE, ruolo=SOCIAL_GROUP_ROLE_ADMIN).count()

    def get_queryset(self):
        personaggio = self.get_personaggio()
        qs = SocialGroup.objects.select_related("creatore", "creatore__social_profile").all()
        if self.request.user.is_staff:
            return qs
        if not personaggio:
            return qs.filter(is_hidden=False)
        member_group_ids = SocialGroupMembership.objects.filter(
            personaggio=personaggio, status=SOCIAL_GROUP_STATUS_ACTIVE
        ).values_list("group_id", flat=True)
        return qs.filter(Q(is_hidden=False) | Q(id__in=member_group_ids)).distinct()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["personaggio"] = self.get_personaggio()
        return ctx

    def perform_create(self, serializer):
        personaggio = self.get_personaggio()
        if not personaggio:
            raise permissions.PermissionDenied("Nessun personaggio selezionabile per questo utente.")
        group = serializer.save(creatore=personaggio)
        SocialGroupMembership.objects.get_or_create(
            group=group,
            personaggio=personaggio,
            defaults={"ruolo": SOCIAL_GROUP_ROLE_ADMIN, "status": SOCIAL_GROUP_STATUS_ACTIVE},
        )

    @action(detail=False, methods=["get"])
    def my(self, request):
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response([], status=status.HTTP_200_OK)
        group_ids = SocialGroupMembership.objects.filter(
            personaggio=personaggio, status=SOCIAL_GROUP_STATUS_ACTIVE
        ).values_list("group_id", flat=True)
        groups = SocialGroup.objects.filter(id__in=group_ids).select_related("creatore", "creatore__social_profile")
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def request_join(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        m, created = SocialGroupMembership.objects.get_or_create(group=group, personaggio=personaggio)
        if not created and m.status == SOCIAL_GROUP_STATUS_ACTIVE:
            return Response({"detail": "Sei gia membro del gruppo."}, status=status.HTTP_200_OK)
        m.status = SOCIAL_GROUP_STATUS_REQUESTED if group.requires_approval else SOCIAL_GROUP_STATUS_ACTIVE
        m.save()
        return Response(SocialGroupMembershipSerializer(m).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_group_admin(group, personaggio)):
            raise permissions.PermissionDenied("Solo admin gruppo o staff possono invitare membri.")
        target_id = request.data.get("personaggio_target_id")
        target = Personaggio.objects.filter(id=target_id).first()
        if not target:
            return Response({"detail": "Personaggio target non trovato."}, status=status.HTTP_404_NOT_FOUND)
        m, _ = SocialGroupMembership.objects.get_or_create(group=group, personaggio=target)
        m.status = SOCIAL_GROUP_STATUS_INVITED if group.requires_approval else SOCIAL_GROUP_STATUS_ACTIVE
        m.invited_by = personaggio
        m.save()
        return Response(SocialGroupMembershipSerializer(m).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def approve_member(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_group_admin(group, personaggio)):
            raise permissions.PermissionDenied("Solo admin gruppo o staff possono approvare membri.")
        target_id = request.data.get("personaggio_target_id")
        membership = SocialGroupMembership.objects.filter(group=group, personaggio_id=target_id).first()
        if not membership:
            return Response({"detail": "Membership non trovata."}, status=status.HTTP_404_NOT_FOUND)
        membership.status = SOCIAL_GROUP_STATUS_ACTIVE
        membership.save()
        return Response(SocialGroupMembershipSerializer(membership).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject_member(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_group_admin(group, personaggio)):
            raise permissions.PermissionDenied("Solo admin gruppo o staff possono rifiutare membri.")
        target_id = request.data.get("personaggio_target_id")
        membership = SocialGroupMembership.objects.filter(group=group, personaggio_id=target_id).first()
        if not membership:
            return Response({"detail": "Membership non trovata."}, status=status.HTTP_404_NOT_FOUND)
        if (
            membership.status == SOCIAL_GROUP_STATUS_ACTIVE
            and membership.ruolo == SOCIAL_GROUP_ROLE_ADMIN
            and self._active_admin_count(group) <= 1
        ):
            return Response({"detail": "Impossibile rimuovere l'ultimo admin del gruppo."}, status=status.HTTP_400_BAD_REQUEST)
        membership.status = SOCIAL_GROUP_STATUS_REJECTED
        membership.save()
        return Response(SocialGroupMembershipSerializer(membership).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def set_member_role(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_group_admin(group, personaggio)):
            raise permissions.PermissionDenied("Solo admin gruppo o staff possono modificare ruoli.")
        target_id = request.data.get("personaggio_target_id")
        ruolo = request.data.get("ruolo")
        if ruolo not in {SOCIAL_GROUP_ROLE_ADMIN, SOCIAL_GROUP_ROLE_MEMBER}:
            return Response({"detail": "Ruolo non valido."}, status=status.HTTP_400_BAD_REQUEST)
        membership = SocialGroupMembership.objects.filter(
            group=group, personaggio_id=target_id, status=SOCIAL_GROUP_STATUS_ACTIVE
        ).first()
        if not membership:
            return Response({"detail": "Membro attivo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        if (
            membership.ruolo == SOCIAL_GROUP_ROLE_ADMIN
            and ruolo != SOCIAL_GROUP_ROLE_ADMIN
            and self._active_admin_count(group) <= 1
        ):
            return Response({"detail": "Impossibile degradare l'ultimo admin del gruppo."}, status=status.HTTP_400_BAD_REQUEST)
        membership.ruolo = ruolo
        membership.save()
        return Response(SocialGroupMembershipSerializer(membership).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_active_member(group, personaggio) or not group.is_hidden):
            raise permissions.PermissionDenied("Gruppo non accessibile.")
        qs = group.memberships.select_related("personaggio", "personaggio__social_profile", "invited_by", "invited_by__social_profile").all().order_by("-created_at")
        paginator = SocialGroupMemberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = SocialGroupMembershipSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def accept_invite(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        membership = SocialGroupMembership.objects.filter(group=group, personaggio=personaggio).first()
        if not membership or membership.status != SOCIAL_GROUP_STATUS_INVITED:
            return Response({"detail": "Nessun invito attivo trovato."}, status=status.HTTP_404_NOT_FOUND)
        membership.status = SOCIAL_GROUP_STATUS_ACTIVE
        membership.save()
        return Response(SocialGroupMembershipSerializer(membership).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def decline_invite(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        membership = SocialGroupMembership.objects.filter(group=group, personaggio=personaggio).first()
        if not membership or membership.status != SOCIAL_GROUP_STATUS_INVITED:
            return Response({"detail": "Nessun invito attivo trovato."}, status=status.HTTP_404_NOT_FOUND)
        membership.status = SOCIAL_GROUP_STATUS_REJECTED
        membership.save()
        return Response(SocialGroupMembershipSerializer(membership).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        membership = SocialGroupMembership.objects.filter(
            group=group, personaggio=personaggio, status=SOCIAL_GROUP_STATUS_ACTIVE
        ).first()
        if not membership:
            return Response({"detail": "Non sei membro attivo di questo gruppo."}, status=status.HTTP_400_BAD_REQUEST)
        if membership.ruolo == SOCIAL_GROUP_ROLE_ADMIN and self._active_admin_count(group) <= 1:
            return Response({"detail": "Impossibile uscire: sei l'ultimo admin del gruppo."}, status=status.HTTP_400_BAD_REQUEST)
        membership.status = SOCIAL_GROUP_STATUS_REJECTED
        membership.save()
        return Response({"detail": "Uscita dal gruppo effettuata."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"])
    def posts(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_active_member(group, personaggio)):
            raise permissions.PermissionDenied("Solo i membri possono vedere/scrivere post nel gruppo.")
        if request.method.lower() == "get":
            qs = group.posts.select_related("autore", "autore__social_profile").all()
            paginator = SocialGroupPostPagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            serializer = SocialGroupPostSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = SocialGroupPostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(group=group, autore=personaggio)
        return Response(SocialGroupPostSerializer(obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path=r"posts/(?P<post_id>[^/.]+)")
    def update_post(self, request, pk=None, post_id=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        post = SocialGroupPost.objects.filter(id=post_id, group=group).first()
        if not post:
            return Response({"detail": "Post di gruppo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        can_moderate = request.user.is_staff or self._is_group_admin(group, personaggio)
        can_edit_own = personaggio and post.autore_id == personaggio.id
        if not (can_moderate or can_edit_own):
            raise permissions.PermissionDenied("Permessi insufficienti per modificare il post.")
        serializer = SocialGroupPostSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path=r"posts/(?P<post_id>[^/.]+)")
    def delete_post(self, request, pk=None, post_id=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        post = SocialGroupPost.objects.filter(id=post_id, group=group).first()
        if not post:
            return Response({"detail": "Post di gruppo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        can_moderate = request.user.is_staff or self._is_group_admin(group, personaggio)
        can_delete_own = personaggio and post.autore_id == personaggio.id
        if not (can_moderate or can_delete_own):
            raise permissions.PermissionDenied("Permessi insufficienti per eliminare il post.")
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        if not (request.user.is_staff or self._is_active_member(group, personaggio)):
            raise permissions.PermissionDenied("Solo i membri possono vedere/scrivere messaggi nel gruppo.")
        if request.method.lower() == "get":
            qs = group.messages.select_related("autore", "autore__social_profile").all()
            paginator = SocialGroupMessagePagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            serializer = SocialGroupMessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = SocialGroupMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(group=group, autore=personaggio)
        return Response(SocialGroupMessageSerializer(obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"messages/(?P<message_id>[^/.]+)")
    def delete_message(self, request, pk=None, message_id=None):
        group = self.get_object()
        personaggio = self.get_personaggio()
        message = SocialGroupMessage.objects.filter(id=message_id, group=group).first()
        if not message:
            return Response({"detail": "Messaggio di gruppo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        can_moderate = request.user.is_staff or self._is_group_admin(group, personaggio)
        can_delete_own = personaggio and message.autore_id == personaggio.id
        if not (can_moderate or can_delete_own):
            raise permissions.PermissionDenied("Permessi insufficienti per eliminare il messaggio.")
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SocialProfileMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_or_create_profile(self, request):
        requested = request.query_params.get("personaggio_id") or request.data.get("personaggio_id")
        personaggio = resolve_active_personaggio(request.user, requested, request=request)
        if not personaggio:
            return None
        profile, _ = SocialProfile.objects.select_related(
            "personaggio",
            "personaggio__era",
            "personaggio__prefettura",
            "personaggio__prefettura__regione",
            "personaggio__segno_zodiacale",
        ).get_or_create(personaggio=personaggio)
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
        profile, _ = SocialProfile.objects.select_related(
            "personaggio",
            "personaggio__era",
            "personaggio__prefettura",
            "personaggio__prefettura__regione",
            "personaggio__segno_zodiacale",
        ).get_or_create(personaggio=personaggio)
        return Response(SocialProfilePublicSerializer(profile, context={"request": request}).data)


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


class SocialNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requested = request.query_params.get("personaggio_id")
        personaggio = resolve_active_personaggio(request.user, requested, request=request)
        if not personaggio:
            return Response({"detail": "Nessun personaggio trovato."}, status=status.HTTP_400_BAD_REQUEST)

        limit = request.query_params.get("limit")
        try:
            limit = max(1, min(int(limit or 30), 100))
        except (TypeError, ValueError):
            limit = 30

        likes_qs = (
            SocialLike.objects.filter(post__autore=personaggio)
            .exclude(autore=personaggio)
            .select_related("autore", "autore__social_profile", "post")
        )
        comments_qs = (
            SocialComment.objects.filter(post__autore=personaggio)
            .exclude(autore=personaggio)
            .select_related("autore", "autore__social_profile", "post")
        )
        post_mentions_qs = (
            SocialPostTag.objects.filter(personaggio=personaggio)
            .exclude(post__autore=personaggio)
            .select_related("post", "post__autore", "post__autore__social_profile")
        )
        comment_mentions_qs = (
            SocialCommentTag.objects.filter(personaggio=personaggio)
            .exclude(comment__autore=personaggio)
            .select_related(
                "comment",
                "comment__autore",
                "comment__autore__social_profile",
                "comment__post",
                "personaggio",
                "personaggio__social_profile",
            )
        )
        story_mentions_qs = (
            SocialStoryTag.objects.filter(personaggio=personaggio)
            .exclude(story__autore=personaggio)
            .select_related(
                "story",
                "story__autore",
                "story__autore__social_profile",
                "personaggio",
                "personaggio__social_profile",
            )
        )

        def _mention_event(kind, created_at, actor, target_pg, source_kind, post_id=None, post_title="", text="", comment_id=None, story_id=None):
            actor_name = social_display_name(actor) if actor else ""
            target_name = social_display_name(target_pg) if target_pg else ""
            return {
                "kind": kind,
                "created_at": created_at,
                "post_id": post_id,
                "post_title": post_title or "",
                "comment_id": comment_id,
                "story_id": story_id,
                "actor_id": getattr(actor, "id", None),
                "actor_name": actor_name,
                "target_id": getattr(target_pg, "id", None),
                "target_name": target_name,
                "text": text or "",
                "message": format_mention_message(actor_name, target_name, source_kind) if actor_name and target_name else "",
                "link": instafame_deep_link_path(post_id=post_id, comment_id=comment_id, story_id=story_id),
            }

        events = []
        for like in likes_qs[:limit]:
            events.append(
                {
                    "kind": "like",
                    "created_at": like.created_at,
                    "post_id": like.post_id,
                    "post_title": like.post.titolo or "",
                    "actor_id": like.autore_id,
                    "actor_name": social_display_name(like.autore),
                    "text": "",
                }
            )
        for comment in comments_qs[:limit]:
            events.append(
                {
                    "kind": "comment",
                    "created_at": comment.created_at,
                    "post_id": comment.post_id,
                    "post_title": comment.post.titolo or "",
                    "actor_id": comment.autore_id,
                    "actor_name": social_display_name(comment.autore),
                    "text": comment.testo or "",
                }
            )
        for tag in post_mentions_qs[:limit]:
            events.append(
                _mention_event(
                    "mention_post",
                    tag.updated_at,
                    tag.post.autore if tag.post else None,
                    personaggio,
                    "post",
                    post_id=tag.post_id,
                    post_title=tag.post.titolo if tag.post else "",
                    text=tag.post.testo if tag.post else "",
                )
            )
        for tag in comment_mentions_qs[:limit]:
            events.append(
                _mention_event(
                    "mention_comment",
                    tag.updated_at,
                    tag.comment.autore if tag.comment else None,
                    personaggio,
                    "comment",
                    post_id=tag.comment.post_id if tag.comment else None,
                    post_title=tag.comment.post.titolo if tag.comment and tag.comment.post else "",
                    text=tag.comment.testo if tag.comment else "",
                    comment_id=tag.comment_id,
                )
            )
        for tag in story_mentions_qs[:limit]:
            events.append(
                _mention_event(
                    "mention_story",
                    tag.created_at,
                    tag.story.autore if tag.story else None,
                    personaggio,
                    "story",
                    text=tag.story.testo if tag.story else "",
                    story_id=tag.story_id,
                )
            )

        events.sort(key=lambda e: e["created_at"], reverse=True)
        events = events[:limit]

        since_param = request.query_params.get("since")
        unread_count = 0
        if since_param:
            try:
                since_dt = datetime.fromisoformat(since_param.replace("Z", "+00:00"))
                if timezone.is_naive(since_dt):
                    since_dt = timezone.make_aware(since_dt)
                unread_count = sum(
                    1
                    for e in events
                    if e["created_at"] and e["created_at"] > since_dt
                )
            except (ValueError, TypeError):
                unread_count = len(events)
        else:
            unread_count = len(events)

        return Response(
            {
                "count": len(events),
                "unread_count": unread_count,
                "results": [
                    {
                        **e,
                        "created_at": e["created_at"].isoformat() if e["created_at"] else None,
                    }
                    for e in events
                ],
            }
        )
