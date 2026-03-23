from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from .models import SocialComment, SocialLike, SocialPost, SocialProfile


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


@admin.register(SocialPost)
class SocialPostAdmin(SummernoteModelAdmin):
    list_display = ("titolo", "autore", "visibilita", "korp_visibilita", "evento", "created_at")
    list_filter = ("visibilita", "korp_visibilita", "evento")
    search_fields = ("titolo", "testo", "autore__nome")
    autocomplete_fields = ("autore", "korp_visibilita", "evento")
    inlines = [SocialCommentInline, SocialLikeInline]
    summernote_fields = ("testo",)


@admin.register(SocialComment)
class SocialCommentAdmin(SummernoteModelAdmin):
    list_display = ("post", "autore", "evento", "created_at")
    list_filter = ("evento",)
    search_fields = ("testo", "autore__nome", "post__titolo")
    autocomplete_fields = ("post", "autore", "evento")
    summernote_fields = ("testo",)


@admin.register(SocialLike)
class SocialLikeAdmin(admin.ModelAdmin):
    list_display = ("post", "autore", "created_at")
    search_fields = ("post__titolo", "autore__nome")
    autocomplete_fields = ("post", "autore")
