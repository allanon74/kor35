from django.db.models import Count, Q
from rest_framework import serializers

from personaggi.models import (
    Personaggio,
    PersonaggioKorpMembership,
    Campagna,
    CampagnaFeaturePolicy,
    FEATURE_SOCIAL,
    FEATURE_MODE_SHARED,
)

from .models import (
    SOCIAL_GROUP_STATUS_ACTIVE,
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
    SocialStory,
    SocialStoryHighlight,
    SocialStoryHighlightItem,
    SocialStoryReaction,
    SocialStoryReply,
    SocialStoryTag,
    SocialStoryView,
    extract_hashtags,
)


class SocialProfileSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True)
    korp_nome = serializers.SerializerMethodField()
    segno_zodiacale = serializers.CharField(source="personaggio.segno_zodiacale.nome", read_only=True)

    class Meta:
        model = SocialProfile
        fields = (
            "id",
            "personaggio",
            "personaggio_nome",
            "foto_principale",
            "regione",
            "prefettura",
            "descrizione",
            "professioni",
            "era_provenienza",
            "korp_nome",
            "segno_zodiacale",
        )
        read_only_fields = ("personaggio", "personaggio_nome", "korp_nome", "segno_zodiacale")

    def get_korp_nome(self, obj):
        membership = obj.personaggio.korp_membership.filter(data_a__isnull=True).select_related("korp").first()
        return membership.korp.nome if membership else None


class SocialProfilePublicSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True)
    korp_nome = serializers.SerializerMethodField()
    segno_zodiacale = serializers.CharField(source="personaggio.segno_zodiacale.nome", read_only=True)

    class Meta:
        model = SocialProfile
        fields = (
            "id",
            "personaggio",
            "personaggio_nome",
            "foto_principale",
            "regione",
            "prefettura",
            "descrizione",
            "professioni",
            "era_provenienza",
            "korp_nome",
            "segno_zodiacale",
        )
        read_only_fields = fields

    def get_korp_nome(self, obj):
        membership = obj.personaggio.korp_membership.filter(data_a__isnull=True).select_related("korp").first()
        return membership.korp.nome if membership else None

    def get_korp_nome(self, obj):
        membership = obj.personaggio.korp_membership.filter(data_a__isnull=True).select_related("korp").first()
        return membership.korp.nome if membership else None


class SocialCommentSerializer(serializers.ModelSerializer):
    autore_nome = serializers.CharField(source="autore.nome", read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = SocialComment
        fields = ("id", "post", "autore", "autore_nome", "testo", "evento", "created_at", "tags")
        read_only_fields = ("post", "autore", "evento", "created_at")

    def get_tags(self, obj):
        return list(obj.tags.select_related("personaggio").values("personaggio_id", "personaggio__nome"))


class SocialPostSerializer(serializers.ModelSerializer):
    autore_nome = serializers.CharField(source="autore.nome", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
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
        return SocialLike.objects.filter(post=obj, autore=personaggio).exists()

    def validate(self, attrs):
        vis = attrs.get("visibilita", getattr(self.instance, "visibilita", None))
        korp = attrs.get("korp_visibilita", getattr(self.instance, "korp_visibilita", None))
        if vis == "KORP" and not korp:
            raise serializers.ValidationError("Per la visibilita KORP devi indicare una KORP.")
        return attrs

    def get_tags(self, obj):
        return list(obj.tags.select_related("personaggio").values("personaggio_id", "personaggio__nome"))

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
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True)
    invited_by_nome = serializers.CharField(source="invited_by.nome", read_only=True)

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


class SocialGroupSerializer(serializers.ModelSerializer):
    creatore_nome = serializers.CharField(source="creatore.nome", read_only=True)
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
    autore_nome = serializers.CharField(source="autore.nome", read_only=True)

    class Meta:
        model = SocialGroupPost
        fields = ("id", "group", "autore", "autore_nome", "titolo", "testo", "immagine", "video", "created_at")
        read_only_fields = ("group", "autore", "created_at")


class SocialGroupMessageSerializer(serializers.ModelSerializer):
    autore_nome = serializers.CharField(source="autore.nome", read_only=True)

    class Meta:
        model = SocialGroupMessage
        fields = ("id", "group", "autore", "autore_nome", "testo", "created_at")
        read_only_fields = ("group", "autore", "created_at")


class SocialStorySerializer(serializers.ModelSerializer):
    autore_nome = serializers.CharField(source="autore.nome", read_only=True)
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

    def get_hashtags(self, obj):
        text = f"{obj.testo or ''}".strip()
        return extract_hashtags(text)

    def get_tags(self, obj):
        return list(obj.tags.select_related("personaggio").values("personaggio_id", "personaggio__nome"))

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
    autore_nome = serializers.CharField(source="autore.nome", read_only=True)

    class Meta:
        model = SocialStoryReply
        fields = ("id", "story", "autore", "autore_nome", "testo", "created_at")
        read_only_fields = ("story", "autore", "created_at")


class SocialStoryHighlightItemSerializer(serializers.ModelSerializer):
    story = SocialStorySerializer(read_only=True)

    class Meta:
        model = SocialStoryHighlightItem
        fields = ("id", "highlight", "story", "added_at")
        read_only_fields = fields


class SocialStoryHighlightSerializer(serializers.ModelSerializer):
    owner_nome = serializers.CharField(source="owner.nome", read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = SocialStoryHighlight
        fields = ("id", "owner", "owner_nome", "titolo", "created_at", "items")
        read_only_fields = ("owner", "owner_nome", "created_at", "items")

    def get_items(self, obj):
        qs = obj.items.select_related("story", "story__autore", "story__evento", "story__korp_visibilita").all()
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


def resolve_active_personaggio(user, explicit_personaggio_id=None, request=None):
    active_campaign = _get_active_campaign_from_request(request)
    owned = Personaggio.objects.filter(proprietario=user)
    if active_campaign:
        owned = owned.filter(campagna=active_campaign)
    owned = owned.order_by("id")
    if explicit_personaggio_id:
        pg = owned.filter(id=explicit_personaggio_id).first()
        if pg:
            return pg
    return owned.first()


def get_active_korp(personaggio):
    if not personaggio:
        return None
    membership = (
        PersonaggioKorpMembership.objects.filter(personaggio=personaggio, data_a__isnull=True)
        .select_related("korp")
        .first()
    )
    return membership.korp if membership else None


def visible_posts_queryset_for_personaggio(personaggio, request=None):
    base = SocialPost.objects.select_related("autore", "evento", "korp_visibilita").annotate(
        likes_count=Count("likes", distinct=True),
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
