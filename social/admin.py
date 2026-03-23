from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from .models import SocialComment, SocialCommentTag, SocialLike, SocialPost, SocialPostTag, SocialProfile


@admin.register(SocialProfile)
class SocialProfileAdmin(SummernoteModelAdmin):
    list_display = ("personaggio", "regione", "prefettura", "created_at")
    search_fields = ("personaggio__nome", "regione", "prefettura")
    autocomplete_fields = ("personaggio",)
    summernote_fields = ("descrizione",)


class SocialCommentInline(admin.TabularInline):
    model = SocialComment
    extra = 0
    autocomplete_fields = ("autore",)
    readonly_fields = ("created_at",)


class SocialLikeInline(admin.TabularInline):
    model = SocialLike
    extra = 0
    autocomplete_fields = ("autore",)
    readonly_fields = ("created_at",)


class SocialPostTagInline(admin.TabularInline):
    model = SocialPostTag
    extra = 0
    autocomplete_fields = ("personaggio",)


class SocialCommentTagInline(admin.TabularInline):
    model = SocialCommentTag
    extra = 0
    autocomplete_fields = ("personaggio",)


@admin.register(SocialPost)
class SocialPostAdmin(SummernoteModelAdmin):
    list_display = ("titolo", "autore", "visibilita", "korp_visibilita", "evento", "public_slug", "created_at")
    list_filter = ("visibilita", "korp_visibilita", "evento")
    search_fields = ("titolo", "testo", "autore__nome")
    autocomplete_fields = ("autore", "korp_visibilita", "evento")
    inlines = [SocialPostTagInline, SocialCommentInline, SocialLikeInline]
    summernote_fields = ("testo",)


@admin.register(SocialComment)
class SocialCommentAdmin(SummernoteModelAdmin):
    list_display = ("post", "autore", "evento", "created_at")
    list_filter = ("evento",)
    search_fields = ("testo", "autore__nome", "post__titolo")
    autocomplete_fields = ("post", "autore", "evento")
    summernote_fields = ("testo",)
    inlines = [SocialCommentTagInline]


@admin.register(SocialLike)
class SocialLikeAdmin(admin.ModelAdmin):
    list_display = ("post", "autore", "created_at")
    search_fields = ("post__titolo", "autore__nome")
    autocomplete_fields = ("post", "autore")


@admin.register(SocialPostTag)
class SocialPostTagAdmin(admin.ModelAdmin):
    list_display = ("post", "personaggio")
    search_fields = ("post__titolo", "personaggio__nome")
    autocomplete_fields = ("post", "personaggio")


@admin.register(SocialCommentTag)
class SocialCommentTagAdmin(admin.ModelAdmin):
    list_display = ("comment", "personaggio")
    search_fields = ("comment__testo", "personaggio__nome")
    autocomplete_fields = ("comment", "personaggio")
