from django.db.models import Count, Q
from rest_framework import serializers

from personaggi.models import Personaggio, PersonaggioKorpMembership

from .models import (
    SocialComment,
    SocialCommentTag,
    SocialLike,
    SocialPost,
    SocialPostTag,
    SocialProfile,
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
            "created_at",
            "likes_count",
            "comments_count",
            "liked_by_me",
            "tags",
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


def resolve_active_personaggio(user, explicit_personaggio_id=None):
    owned = Personaggio.objects.filter(proprietario=user).order_by("id")
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


def visible_posts_queryset_for_personaggio(personaggio):
    base = SocialPost.objects.select_related("autore", "evento", "korp_visibilita").annotate(
        likes_count=Count("likes", distinct=True),
        comments_count=Count("comments", distinct=True),
    )
    if not personaggio:
        return base.filter(visibilita="PUB")
    active_korp = get_active_korp(personaggio)
    if not active_korp:
        return base.filter(visibilita="PUB")
    return base.filter(
        Q(visibilita="PUB")
        | Q(visibilita="KORP", korp_visibilita=active_korp)
    )
