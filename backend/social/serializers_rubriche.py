"""Serializers rubriche InstaFame (lettura in-game, gestione staff, anteprima nei post)."""

from rest_framework import serializers

from personaggi.serializers import _personaggio_avatar_url

from .author_display import get_personaggio_badge_instafame, social_firma_for_personaggio
from .display_names import social_display_name
from .influencer import total_likes_contenuto
from .models_rubriche import (
    RUBRICA_ARTICOLO_PUBBLICATO,
    Rubrica,
    RubricaArticolo,
    RubricaArticoloComment,
    RubricaArticoloCommentLike,
    RubricaArticoloLike,
    RubricaPermessoScrittura,
    testo_semplice_da_html,
)


def _file_url(field_file, request=None):
    if not field_file or not getattr(field_file, "name", ""):
        return None
    try:
        if not field_file.storage.exists(field_file.name):
            return None
    except Exception:
        return None
    url = field_file.url
    if request:
        return request.build_absolute_uri(url)
    return url


def _sommario_effettivo(articolo) -> str:
    if (articolo.sommario or "").strip():
        return articolo.sommario.strip()
    testo = testo_semplice_da_html(articolo.corpo)
    return f"{testo[:220]}…" if len(testo) > 220 else testo


class RubricaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    articoli_count = serializers.SerializerMethodField()
    can_write = serializers.SerializerMethodField()
    wiki_parent_titolo = serializers.CharField(source="wiki_parent.titolo", read_only=True, allow_null=True)
    wiki_pagina_slug = serializers.CharField(source="wiki_pagina.slug", read_only=True, allow_null=True)

    class Meta:
        model = Rubrica
        fields = (
            "id",
            "nome",
            "slug",
            "sottotitolo",
            "descrizione",
            "logo",
            "logo_url",
            "colore_accento",
            "attiva",
            "ordine",
            "created_at",
            "pubblica_in_wiki",
            "wiki_parent",
            "wiki_parent_titolo",
            "wiki_titolo",
            "wiki_ordine",
            "wiki_visibilita",
            "wiki_pagina_slug",
            "articoli_count",
            "can_write",
        )
        read_only_fields = ("slug", "created_at", "logo_url", "articoli_count", "can_write", "wiki_pagina_slug")

    def get_logo_url(self, obj):
        return _file_url(obj.logo, self.context.get("request"))

    def get_articoli_count(self, obj):
        if hasattr(obj, "articoli_pubblicati_count"):
            return int(obj.articoli_pubblicati_count or 0)
        return obj.articoli.filter(stato=RUBRICA_ARTICOLO_PUBBLICATO).count()

    def get_can_write(self, obj):
        if self.context.get("is_staff_rubriche"):
            return True
        scrivibili = self.context.get("rubriche_scrivibili") or set()
        return obj.id in scrivibili


class RubricaArticoloCommentSerializer(serializers.ModelSerializer):
    autore_nome = serializers.SerializerMethodField()
    autore_avatar = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = RubricaArticoloComment
        fields = (
            "id",
            "articolo",
            "autore",
            "autore_nome",
            "autore_avatar",
            "testo",
            "created_at",
            "likes_count",
            "liked_by_me",
            "can_delete",
        )
        read_only_fields = (
            "articolo",
            "autore",
            "created_at",
            "likes_count",
            "liked_by_me",
            "can_delete",
        )

    def get_autore_nome(self, obj):
        return social_display_name(obj.autore)

    def get_autore_avatar(self, obj):
        return _personaggio_avatar_url(obj.autore, self.context.get("request"))

    def get_likes_count(self, obj):
        return total_likes_contenuto(obj)

    def get_liked_by_me(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return False
        return RubricaArticoloCommentLike.objects.filter(comment=obj, autore=personaggio).exists()

    def get_can_delete(self, obj):
        if self.context.get("is_staff_rubriche"):
            return True
        personaggio = self.context.get("personaggio")
        return bool(personaggio and obj.autore_id == personaggio.id)


class RubricaArticoloListSerializer(serializers.ModelSerializer):
    rubrica_nome = serializers.CharField(source="rubrica.nome", read_only=True)
    rubrica_slug = serializers.CharField(source="rubrica.slug", read_only=True)
    rubrica_colore = serializers.CharField(source="rubrica.colore_accento", read_only=True)
    firma = serializers.CharField(read_only=True)
    autore_avatar = serializers.SerializerMethodField()
    autore_badge_instafame = serializers.SerializerMethodField()
    autore_firma_testo = serializers.SerializerMethodField()
    autore_firma_banner = serializers.SerializerMethodField()
    hero_url = serializers.SerializerMethodField()
    sommario_effettivo = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = RubricaArticolo
        fields = (
            "id",
            "rubrica",
            "rubrica_nome",
            "rubrica_slug",
            "rubrica_colore",
            "slug",
            "stato",
            "occhiello",
            "titolo",
            "sottotitolo",
            "sommario",
            "sommario_effettivo",
            "hero_url",
            "hero_didascalia",
            "autore_personaggio",
            "firma_libera",
            "firma",
            "autore_avatar",
            "autore_badge_instafame",
            "autore_firma_testo",
            "autore_firma_banner",
            "data_pubblicazione",
            "created_at",
            "tempo_lettura_min",
            "likes_count",
            "comments_count",
            "liked_by_me",
            "can_edit",
            "post_annuncio",
        )
        read_only_fields = fields

    def get_autore_avatar(self, obj):
        if not obj.autore_personaggio_id:
            return None
        return _personaggio_avatar_url(obj.autore_personaggio, self.context.get("request"))

    def get_autore_badge_instafame(self, obj):
        if not obj.autore_personaggio_id:
            return ""
        return get_personaggio_badge_instafame(obj.autore_personaggio)

    def get_autore_firma_testo(self, obj):
        if not obj.autore_personaggio_id:
            return ""
        return social_firma_for_personaggio(obj.autore_personaggio, self.context.get("request")).get("testo") or ""

    def get_autore_firma_banner(self, obj):
        if not obj.autore_personaggio_id:
            return None
        return social_firma_for_personaggio(obj.autore_personaggio, self.context.get("request")).get("banner")

    def get_hero_url(self, obj):
        return _file_url(obj.hero_immagine, self.context.get("request"))

    def get_sommario_effettivo(self, obj):
        return _sommario_effettivo(obj)

    def get_likes_count(self, obj):
        return total_likes_contenuto(obj)

    def get_comments_count(self, obj):
        if hasattr(obj, "commenti_count"):
            return int(obj.commenti_count or 0)
        return obj.comments.count()

    def get_liked_by_me(self, obj):
        personaggio = self.context.get("personaggio")
        if not personaggio:
            return False
        return RubricaArticoloLike.objects.filter(articolo=obj, autore=personaggio).exists()

    def get_can_edit(self, obj):
        if self.context.get("is_staff_rubriche"):
            return True
        personaggio = self.context.get("personaggio")
        if not personaggio or not obj.autore_personaggio_id:
            return False
        if obj.autore_personaggio_id != personaggio.id:
            return False
        scrivibili = self.context.get("rubriche_scrivibili") or set()
        return obj.rubrica_id in scrivibili


class RubricaArticoloDetailSerializer(RubricaArticoloListSerializer):
    immagini = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta(RubricaArticoloListSerializer.Meta):
        fields = RubricaArticoloListSerializer.Meta.fields + (
            "corpo",
            "immagini",
            "video",
            "video_url",
            "ordine",
            "evento",
        )
        read_only_fields = fields

    def get_immagini(self, obj):
        request = self.context.get("request")
        righe = []
        for riga in obj.immagini.all():
            url = _file_url(riga.immagine, request)
            if url:
                righe.append({"id": str(riga.id), "url": url, "didascalia": riga.didascalia or ""})
        return righe

    def get_video_url(self, obj):
        return _file_url(obj.video, self.context.get("request"))


class RubricaArticoloWriteSerializer(serializers.ModelSerializer):
    """Create/update articolo: i media arrivano via multipart e sono gestiti nella view."""

    class Meta:
        model = RubricaArticolo
        fields = (
            "id",
            "rubrica",
            "stato",
            "occhiello",
            "titolo",
            "sottotitolo",
            "sommario",
            "corpo",
            "hero_didascalia",
            "autore_personaggio",
            "firma_libera",
            "ordine",
        )

    def validate(self, attrs):
        autore = attrs.get("autore_personaggio", getattr(self.instance, "autore_personaggio", None))
        firma = attrs.get("firma_libera", getattr(self.instance, "firma_libera", "") or "")
        if not autore and not (firma or "").strip():
            # Scrittura in-game: l'articolo è firmato dal personaggio attivo.
            personaggio = self.context.get("personaggio")
            if not personaggio:
                raise serializers.ValidationError(
                    "Indica un personaggio autore oppure una firma libera."
                )
            attrs["autore_personaggio"] = personaggio
        return attrs


class RubricaPermessoScritturaSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.SerializerMethodField()
    concesso_da_username = serializers.CharField(
        source="concesso_da.username", read_only=True, allow_null=True
    )

    class Meta:
        model = RubricaPermessoScrittura
        fields = (
            "id",
            "rubrica",
            "personaggio",
            "personaggio_nome",
            "concesso_da",
            "concesso_da_username",
            "attivo",
            "note",
            "created_at",
        )
        read_only_fields = ("rubrica", "concesso_da", "created_at")

    def get_personaggio_nome(self, obj):
        return social_display_name(obj.personaggio)


def articolo_preview_data(articolo, request=None):
    """Card anteprima usata dai post InstaFame che linkano un articolo."""
    if not articolo:
        return None
    return {
        "id": str(articolo.id),
        "rubrica_id": str(articolo.rubrica_id),
        "rubrica_nome": articolo.rubrica.nome if articolo.rubrica_id else "",
        "rubrica_colore": articolo.rubrica.colore_accento if articolo.rubrica_id else "",
        "occhiello": articolo.occhiello or "",
        "titolo": articolo.titolo,
        "sottotitolo": articolo.sottotitolo or "",
        "sommario": _sommario_effettivo(articolo),
        "hero_url": _file_url(articolo.hero_immagine, request),
        "firma": articolo.firma,
        "tempo_lettura_min": articolo.tempo_lettura_min,
        "stato": articolo.stato,
        "data_pubblicazione": articolo.data_pubblicazione.isoformat()
        if articolo.data_pubblicazione
        else None,
    }
