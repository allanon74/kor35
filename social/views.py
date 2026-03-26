from datetime import datetime

from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.models import Evento
from personaggi.models import Personaggio, PersonaggioKorpMembership

from .models import (
    SOCIAL_GROUP_ROLE_ADMIN,
    SOCIAL_GROUP_ROLE_MEMBER,
    SOCIAL_GROUP_STATUS_ACTIVE,
    SOCIAL_GROUP_STATUS_INVITED,
    SOCIAL_GROUP_STATUS_REJECTED,
    SOCIAL_GROUP_STATUS_REQUESTED,
    SOCIAL_VISIBILITY_KORP,
    SocialComment,
    SocialCommentTag,
    SocialGroup,
    SocialGroupMembership,
    SocialGroupMessage,
    SocialGroupPost,
    SocialLike,
    SocialPost,
    SocialPostTag,
    SocialProfile,
    extract_mentioned_personaggi_ids,
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


class SocialPostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 30


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


class SocialPostViewSet(viewsets.ModelViewSet):
    serializer_class = SocialPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = SocialPostPagination

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
        qs = visible_posts_queryset_for_personaggio(personaggio)
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
            paginator = SocialCommentPagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            serializer = SocialCommentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

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
        SocialCommentTag.objects.filter(comment=comment).exclude(personaggio_id__in=ids).delete()
        existing = set(SocialCommentTag.objects.filter(comment=comment).values_list("personaggio_id", flat=True))
        SocialCommentTag.objects.bulk_create(
            [SocialCommentTag(comment=comment, personaggio_id=pid) for pid in ids if pid not in existing]
        )


class SocialGroupViewSet(viewsets.ModelViewSet):
    serializer_class = SocialGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_personaggio(self):
        requested = self.request.query_params.get("personaggio_id") or self.request.data.get("personaggio_id")
        return resolve_active_personaggio(self.request.user, requested)

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
        qs = SocialGroup.objects.select_related("creatore").all()
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
        groups = SocialGroup.objects.filter(id__in=group_ids).select_related("creatore")
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
        qs = group.memberships.select_related("personaggio", "invited_by").all().order_by("-created_at")
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
            qs = group.posts.select_related("autore").all()
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
            qs = group.messages.select_related("autore").all()
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


class SocialNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requested = request.query_params.get("personaggio_id")
        personaggio = resolve_active_personaggio(request.user, requested)
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
            .select_related("autore", "post")
        )
        comments_qs = (
            SocialComment.objects.filter(post__autore=personaggio)
            .exclude(autore=personaggio)
            .select_related("autore", "post")
        )
        post_mentions_qs = (
            SocialPostTag.objects.filter(personaggio=personaggio)
            .exclude(post__autore=personaggio)
            .select_related("post", "post__autore")
        )
        comment_mentions_qs = (
            SocialCommentTag.objects.filter(personaggio=personaggio)
            .exclude(comment__autore=personaggio)
            .select_related("comment", "comment__autore", "comment__post")
        )

        events = []
        for like in likes_qs[:limit]:
            events.append(
                {
                    "kind": "like",
                    "created_at": like.created_at,
                    "post_id": like.post_id,
                    "post_title": like.post.titolo or "",
                    "actor_id": like.autore_id,
                    "actor_name": like.autore.nome if like.autore else "",
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
                    "actor_name": comment.autore.nome if comment.autore else "",
                    "text": comment.testo or "",
                }
            )
        # SocialPostTag non ha created_at (solo updated_at su SyncableModel): usiamo updated_at come istante menzione.
        for tag in post_mentions_qs[:limit]:
            events.append(
                {
                    "kind": "mention_post",
                    "created_at": tag.updated_at,
                    "post_id": tag.post_id,
                    "post_title": tag.post.titolo or "",
                    "actor_id": tag.post.autore_id,
                    "actor_name": tag.post.autore.nome if tag.post and tag.post.autore else "",
                    "text": tag.post.testo or "",
                }
            )
        for tag in comment_mentions_qs[:limit]:
            events.append(
                {
                    "kind": "mention_comment",
                    "created_at": tag.updated_at,
                    "post_id": tag.comment.post_id if tag.comment else None,
                    "post_title": tag.comment.post.titolo if tag.comment and tag.comment.post else "",
                    "actor_id": tag.comment.autore_id if tag.comment else None,
                    "actor_name": tag.comment.autore.nome if tag.comment and tag.comment.autore else "",
                    "text": tag.comment.testo if tag.comment else "",
                }
            )

        events.sort(key=lambda e: e["created_at"], reverse=True)
        events = events[:limit]

        since_param = request.query_params.get("since")
        unread_count = 0
        if since_param:
            try:
                since_dt = datetime.fromisoformat(since_param.replace("Z", "+00:00"))
                unread_count = sum(1 for e in events if e["created_at"] > since_dt)
            except (ValueError, TypeError):
                unread_count = 0

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
