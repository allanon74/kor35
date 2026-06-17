from django.db.models import Count, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import serializers

from personaggi.models import (
    Personaggio,
    get_active_korp,
    get_active_korp_membership,
    Campagna,
    CampagnaFeaturePolicy,
    FEATURE_SOCIAL,
    FEATURE_MODE_SHARED,
)

from .display_names import social_display_name, social_display_name_from_profile
from personaggi.serializers import _personaggio_avatar_url
from .models import (
    SOCIAL_GROUP_STATUS_ACTIVE,
    SocialComment,
    SocialCommentLike,
    SocialCommentTag,
    SocialGroup,
    SocialGroupMembership,
    SocialGroupMessage,
    SocialGroupPost,
    SocialLike,
    SocialPost,
    SocialPostTag,
    SocialProfile,
    SocialStory,
    SocialStoryHighlight,
    SocialStoryHighlightItem,
    SocialStoryReaction,
    SocialStoryReply,
    SocialStoryTag,
    SocialStoryView,
    extract_hashtags,
)


def _personaggio_tag_rows(tag_manager):
    rows = []
    for tag in tag_manager.select_related("personaggio", "personaggio__social_profile").all():
        rows.append(
            {
                "personaggio_id": tag.personaggio_id,
                "personaggio__nome": social_display_name(tag.personaggio),
            }
        )
    return rows


class SocialProfileSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True)
    nome_pubblico = serializers.SerializerMethodField()
    korp_nome = serializers.SerializerMethodField()
    segno_zodiacale = serializers.CharField(source="personaggio.segno_zodiacale.nome", read_only=True)
    era = serializers.IntegerField(source="personaggio.era_id", read_only=True, allow_null=True)
    era_nome = serializers.CharField(source="personaggio.era.nome", read_only=True, allow_null=True)
    prefettura = serializers.IntegerField(source="personaggio.prefettura_id", read_only=True, allow_null=True)
    prefettura_nome = serializers.CharField(source="personaggio.prefettura.nome", read_only=True, allow_null=True)
    prefettura_regione_sigla = serializers.CharField(
        source="personaggio.prefettura.regione.sigla", read_only=True, allow_null=True
    )
    prefettura_esterna = serializers.BooleanField(source="personaggio.prefettura_esterna", read_only=True)
    can_edit_era = serializers.SerializerMethodField()
    regione = serializers.SerializerMethodField()
    era_provenienza = serializers.SerializerMethodField()

    class Meta:
        model = SocialProfile
        fields = (
            "id",
            "personaggio",
            "personaggio_nome",
            "nickname",
            "nome_pubblico",
            "foto_principale",
            "regione",
            "prefettura",
            "prefettura_nome",
            "prefettura_regione_sigla",
            "prefettura_esterna",
            "descrizione",
            "professioni",
            "era_provenienza",
            "era",
            "era_nome",
            "can_edit_era",
            "korp_nome",
            "segno_zodiacale",
        )
        read_only_fields = (
            "personaggio",
            "personaggio_nome",
            "nome_pubblico",
            "korp_nome",
            "segno_zodiacale",
            "regione",
            "prefettura",
            "prefettura_nome",
            "prefettura_regione_sigla",
            "prefettura_esterna",
            "era_provenienza",
            "era",
            "era_nome",
            "can_edit_era",
        )

    def get_nome_pubblico(self, obj):
        return social_display_name_from_profile(obj)

    def validate_nickname(self, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def get_korp_nome(self, obj):
        membership = get_active_korp_membership(obj.personaggio)
        return membership.carriera.nome if membership else None

    def get_can_edit_era(self, obj):
        try:
            return obj.personaggio.can_edit_era_prefettura()
        except Exception:
            return False

    def get_regione(self, obj):
        pref = getattr(obj.personaggio, "prefettura", None)
        if pref and getattr(pref, "regione", None):
            return pref.regione.sigla or pref.regione.nome
        return obj.regione

    def get_era_provenienza(self, obj):
        era = getattr(obj.personaggio, "era", None)
        if era:
            return era.nome
        return obj.era_provenienza


class SocialProfilePublicSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.SerializerMethodField()
    korp_nome = serializers.SerializerMethodField()
    segno_zodiacale = serializers.CharField(source="personaggio.segno_zodiacale.nome", read_only=True)
    era_nome = serializers.CharField(source="personaggio.era.nome", read_only=True, allow_null=True)
    prefettura_nome = serializers.CharField(source="personaggio.prefettura.nome", read_only=True, allow_null=True)
    prefettura_regione_sigla = serializers.CharField(
        source="personaggio.prefettura.regione.sigla", read_only=True, allow_null=True
    )
    regione = serializers.SerializerMethodField()
    era_provenienza = serializers.SerializerMethodField()

    class Meta:
        model = SocialProfile
        fields = (
            "id",
            "personaggio",
            "personaggio_nome",
            "foto_principale",
            "regione",
            "prefettura_nome",
            "prefettura_regione_sigla",
            "descrizione",
            "professioni",
            "era_provenienza",
            "era_nome",
            "korp_nome",
            "segno_zodiacale",
        )
        read_only_fields = fields

    def get_personaggio_nome(self, obj):
        return social_display_name_from_profile(obj)

    def get_korp_nome(self, obj):
        membership = get_active_korp_membership(obj.personaggio)
        return membership.carriera.nome if membership else None

    def get_regione(self, obj):
        pref = getattr(obj.personaggio, "prefettura", None)
        if pref and getattr(pref, "regione", None):
            return pref.regione.sigla or pref.regione.nome
        return obj.regione

    def get_era_provenienza(self, obj):
        era = getattr(obj.personaggio, "era", None)
        if era:
            return era.nome
        return obj.era_provenienza


class SocialCommentSerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()
    autore_avatar = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = SocialComment
        fields = (
            "id",
            "post",
            "autore",
            "autore_nome",
            "autore_avatar",
            "testo",
            "evento",
            "created_at",
            "likes_count",
            "liked_by_me",
            "tags",
        )
        read_only_fields = ("post", "autore", "evento", "created_at", "likes_count", "liked_by_me")

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)

    def get_autore_avatar(self, obj):
        return _personaggio_avatar_url(obj.autore, self.context.get("request"))

    def get_tags(self, obj):
        return _personaggio_tag_rows(obj.tags)

    def get_likes_count(self, obj):
        if hasattr(obj, "likes_total"):
            return int(obj.likes_total or 0)
        from .influencer import total_comment_likes

        return total_comment_likes(obj)

    def get_liked_by_me(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return False
        if hasattr(obj, "liked_by_me_flag"):
            return bool(obj.liked_by_me_flag)
        return SocialCommentLike.objects.filter(comment=obj, autore=personaggio).exists()


class SocialPostSerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()
    autore_avatar = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(read_only=True)
    liked_by_me = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    evento_titolo = serializers.CharField(source="evento.titolo", read_only=True)
    hashtags = serializers.SerializerMethodField()

    class Meta:
        model = SocialPost
        fields = (
            "id",
            "autore",
            "autore_nome",
            "autore_avatar",
            "titolo",
            "testo",
            "immagine",
            "video",
            "visibilita",
            "korp_visibilita",
            "evento",
            "evento_titolo",
            "created_at",
            "likes_count",
            "comments_count",
            "liked_by_me",
            "tags",
            "hashtags",
            "public_url",
        )
        read_only_fields = ("autore", "evento", "created_at", "likes_count", "comments_count", "liked_by_me")

    def get_liked_by_me(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return False
        if hasattr(obj, "liked_by_me_flag"):
            return bool(obj.liked_by_me_flag)
        return SocialLike.objects.filter(post=obj, autore=personaggio).exists()

    def get_likes_count(self, obj):
        if hasattr(obj, "likes_total"):
            return int(obj.likes_total or 0)
        from .influencer import total_post_likes

        return total_post_likes(obj)

    def get_autore_avatar(self, obj):
        return _personaggio_avatar_url(obj.autore, self.context.get("request"))

    def validate(self, attrs):
        vis = attrs.get("visibilita", getattr(self.instance, "visibilita", None))
        korp = attrs.get("korp_visibilita", getattr(self.instance, "korp_visibilita", None))
        if vis == "KORP" and not korp:
            raise serializers.ValidationError("Per la visibilita KORP devi indicare una KORP.")
        return attrs

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)

    def get_tags(self, obj):
        return _personaggio_tag_rows(obj.tags)

    def get_public_url(self, obj):
        if obj.visibilita != "PUB":
            return None
        request = self.context.get("request")
        path = f"/social/post/{obj.public_slug}"
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_hashtags(self, obj):
        text = f"{obj.titolo or ''} {obj.testo or ''}".strip()
        return extract_hashtags(text)


class SocialGroupMembershipSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.SerializerMethodField()
    invited_by_nome = serializers.SerializerMethodField()

    class Meta:
        model = SocialGroupMembership
        fields = (
            "id",
            "group",
            "personaggio",
            "personaggio_nome",
            "ruolo",
            "status",
            "invited_by",
            "invited_by_nome",
            "joined_at",
            "created_at",
        )
        read_only_fields = ("joined_at", "created_at")

    def get_personaggio_nome(self, obj):
        return social_display_name(obj.personaggio)

    def get_invited_by_nome(self, obj):
        return social_display_name(obj.invited_by)


class SocialGroupSerializer(serializers.ModelSerializer):
    creatore_nome = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    my_membership_status = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = SocialGroup
        fields = (
            "id",
            "nome",
            "slug",
            "descrizione",
            "creatore",
            "creatore_nome",
            "is_hidden",
            "requires_approval",
            "created_at",
            "members_count",
            "my_membership_status",
            "my_role",
        )
        read_only_fields = ("slug", "creatore", "created_at", "members_count", "my_membership_status", "my_role")

    def get_creatore_nome(self, obj):
        return social_display_name(obj.creatore)

    def get_members_count(self, obj):
        return obj.memberships.filter(status=SOCIAL_GROUP_STATUS_ACTIVE).count()

    def get_my_membership_status(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return None
        m = obj.memberships.filter(personaggio=personaggio).first()
        return m.status if m else None

    def get_my_role(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return None
        m = obj.memberships.filter(personaggio=personaggio).first()
        return m.ruolo if m else None


class SocialGroupPostSerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()

    class Meta:
        model = SocialGroupPost
        fields = ("id", "group", "autore", "autore_nome", "titolo", "testo", "immagine", "video", "created_at")
        read_only_fields = ("group", "autore", "created_at")

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)


class SocialGroupMessageSerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()

    class Meta:
        model = SocialGroupMessage
        fields = ("id", "group", "autore", "autore_nome", "testo", "created_at")
        read_only_fields = ("group", "autore", "created_at")

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)


class SocialStorySerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()
    evento_titolo = serializers.CharField(source="evento.titolo", read_only=True)
    hashtags = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    viewed_by_me = serializers.SerializerMethodField()
    views_count = serializers.IntegerField(read_only=True)
    reactions_count = serializers.IntegerField(read_only=True)
    reacted_by_me = serializers.SerializerMethodField()
    my_reaction = serializers.SerializerMethodField()
    converted_post_id = serializers.IntegerField(source="converted_post.id", read_only=True)

    class Meta:
        model = SocialStory
        fields = (
            "id",
            "autore",
            "autore_nome",
            "testo",
            "media",
            "text_size",
            "visibilita",
            "korp_visibilita",
            "evento",
            "evento_titolo",
            "auto_publish_mode",
            "converted_post_id",
            "created_at",
            "expires_at",
            "tags",
            "hashtags",
            "views_count",
            "viewed_by_me",
            "reactions_count",
            "reacted_by_me",
            "my_reaction",
        )
        read_only_fields = (
            "autore",
            "evento",
            "created_at",
            "expires_at",
            "tags",
            "hashtags",
            "converted_post_id",
            "views_count",
            "viewed_by_me",
            "reactions_count",
            "reacted_by_me",
            "my_reaction",
        )

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)

    def get_hashtags(self, obj):
        text = f"{obj.testo or ''}".strip()
        return extract_hashtags(text)

    def get_tags(self, obj):
        return _personaggio_tag_rows(obj.tags)

    def get_viewed_by_me(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return False
        return SocialStoryView.objects.filter(story=obj, viewer=personaggio).exists()

    def get_reacted_by_me(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return False
        return SocialStoryReaction.objects.filter(story=obj, autore=personaggio).exists()

    def get_my_reaction(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return None
        r = SocialStoryReaction.objects.filter(story=obj, autore=personaggio).first()
        return r.emoji if r else None


class SocialStoryReplySerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()

    class Meta:
        model = SocialStoryReply
        fields = ("id", "story", "autore", "autore_nome", "testo", "created_at")
        read_only_fields = ("story", "autore", "created_at")

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)


class SocialStoryHighlightItemSerializer(serializers.ModelSerializer):
    story = SocialStorySerializer(read_only=True)

    class Meta:
        model = SocialStoryHighlightItem
        fields = ("id", "highlight", "story", "added_at")
        read_only_fields = fields


class SocialStoryHighlightSerializer(serializers.ModelSerializer):
    owner_nome = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()

    class Meta:
        model = SocialStoryHighlight
        fields = ("id", "owner", "owner_nome", "titolo", "created_at", "items")
        read_only_fields = ("owner", "owner_nome", "created_at", "items")

    def get_owner_nome(self, obj):
        return social_display_name(obj.owner)

    def get_items(self, obj):
        qs = obj.items.select_related(
            "story", "story__autore", "story__autore__social_profile", "story__evento", "story__korp_visibilita"
        ).all()
        # Context: passa personaggio per viewed/reacted.
        personaggio = self.context.get("personaggio")
        return SocialStoryHighlightItemSerializer(qs, many=True, context={"personaggio": personaggio}).data


def _get_default_campaign():
    return Campagna.objects.filter(slug="kor35").first() or Campagna.objects.filter(is_default=True).first()


def _get_active_campaign_from_request(request):
    if not request:
        return _get_default_campaign()
    slug = (request.headers.get("X-Campagna") or request.query_params.get("campagna") or "kor35").strip().lower()
    return Campagna.objects.filter(slug=slug, attiva=True).first() or _get_default_campaign()


def _social_mode_for_campaign(campagna):
    if not campagna or campagna.slug == "kor35":
        return FEATURE_MODE_SHARED
    row = CampagnaFeaturePolicy.objects.filter(campagna=campagna, feature_key=FEATURE_SOCIAL).first()
    return row.mode if row else FEATURE_MODE_SHARED


def owned_personaggi_queryset_for_user(user, request=None):
    """Personaggi del giocatore nel contesto campagna attiva (allineato a PersonaggioListView)."""
    active_campaign = _get_active_campaign_from_request(request)
    default_campaign = _get_default_campaign()
    owned = Personaggio.objects.filter(proprietario=user)
    if not active_campaign:
        return owned.order_by("id")
    if default_campaign and active_campaign.id != default_campaign.id:
        return owned.filter(
            Q(campagna=active_campaign) | Q(campagna=default_campaign, tipologia__giocante=False)
        ).order_by("id")
    return owned.filter(campagna=active_campaign).order_by("id")


def resolve_active_personaggio(user, explicit_personaggio_id=None, request=None):
    if explicit_personaggio_id not in (None, ""):
        try:
            explicit_id = int(explicit_personaggio_id)
        except (TypeError, ValueError):
            return None
        # InstaFame: like/commenti/post agiscono sempre come il personaggio scelto, non come giocatore.
        return Personaggio.objects.filter(proprietario=user, id=explicit_id).first()
    return owned_personaggi_queryset_for_user(user, request).first()


def visible_posts_queryset_for_personaggio(personaggio, request=None):
    base = SocialPost.objects.select_related("autore", "autore__social_profile", "evento", "korp_visibilita").annotate(
        _likes_user_sum=Coalesce(Sum("likes__peso_like"), Value(0)),
        likes_total=F("likes_base") + F("_likes_user_sum"),
        comments_count=Count("comments", distinct=True),
    )
    active_campaign = _get_active_campaign_from_request(request)
    default_campaign = _get_default_campaign()
    mode = _social_mode_for_campaign(active_campaign)
    if active_campaign:
        png_kor35_q = Q(
            autore__campagna=default_campaign,
            autore__tipologia__giocante=False,
        )
        if mode == FEATURE_MODE_SHARED and default_campaign:
            base = base.filter(Q(autore__campagna=active_campaign) | Q(autore__campagna=default_campaign) | png_kor35_q)
        else:
            base = base.filter(Q(autore__campagna=active_campaign) | png_kor35_q)
    if not personaggio:
        return base.filter(visibilita="PUB")
    active_korp = get_active_korp(personaggio)
    if not active_korp:
        return base.filter(visibilita="PUB")
    return base.filter(
        Q(visibilita="PUB")
        | Q(visibilita="KORP", korp_visibilita=active_korp)
    )
