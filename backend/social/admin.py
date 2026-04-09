from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from .models import (
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
)


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


class SocialGroupMembershipInline(admin.TabularInline):
    model = SocialGroupMembership
    extra = 0
    autocomplete_fields = ("personaggio", "invited_by")
    readonly_fields = ("joined_at", "created_at")


class SocialGroupPostInline(admin.TabularInline):
    model = SocialGroupPost
    extra = 0
    autocomplete_fields = ("autore",)
    readonly_fields = ("created_at",)


class SocialGroupMessageInline(admin.TabularInline):
    model = SocialGroupMessage
    extra = 0
    autocomplete_fields = ("autore",)
    readonly_fields = ("created_at",)


@admin.register(SocialGroup)
class SocialGroupAdmin(SummernoteModelAdmin):
    list_display = ("nome", "creatore", "is_hidden", "requires_approval", "created_at")
    list_filter = ("is_hidden", "requires_approval")
    search_fields = ("nome", "descrizione", "creatore__nome")
    autocomplete_fields = ("creatore",)
    summernote_fields = ("descrizione",)
    inlines = [SocialGroupMembershipInline, SocialGroupPostInline, SocialGroupMessageInline]


@admin.register(SocialGroupMembership)
class SocialGroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("group", "personaggio", "ruolo", "status", "invited_by", "joined_at", "created_at")
    list_filter = ("ruolo", "status")
    search_fields = ("group__nome", "personaggio__nome", "invited_by__nome")
    autocomplete_fields = ("group", "personaggio", "invited_by")


@admin.register(SocialGroupPost)
class SocialGroupPostAdmin(SummernoteModelAdmin):
    list_display = ("group", "titolo", "autore", "created_at")
    list_filter = ("group",)
    search_fields = ("titolo", "testo", "group__nome", "autore__nome")
    autocomplete_fields = ("group", "autore")
    summernote_fields = ("testo",)


@admin.register(SocialGroupMessage)
class SocialGroupMessageAdmin(SummernoteModelAdmin):
    list_display = ("group", "autore", "created_at")
    list_filter = ("group",)
    search_fields = ("testo", "group__nome", "autore__nome")
    autocomplete_fields = ("group", "autore")
    summernote_fields = ("testo",)


class SocialStoryTagInline(admin.TabularInline):
    model = SocialStoryTag
    extra = 0
    autocomplete_fields = ("personaggio",)


class SocialStoryViewInline(admin.TabularInline):
    model = SocialStoryView
    extra = 0
    autocomplete_fields = ("viewer",)
    readonly_fields = ("viewed_at",)


class SocialStoryReactionInline(admin.TabularInline):
    model = SocialStoryReaction
    extra = 0
    autocomplete_fields = ("autore",)
    readonly_fields = ("created_at",)


class SocialStoryReplyInline(admin.TabularInline):
    model = SocialStoryReply
    extra = 0
    autocomplete_fields = ("autore",)
    readonly_fields = ("created_at",)


@admin.register(SocialStory)
class SocialStoryAdmin(SummernoteModelAdmin):
    list_display = ("autore", "visibilita", "korp_visibilita", "auto_publish_mode", "converted_post", "evento", "created_at", "expires_at")
    list_filter = ("visibilita", "korp_visibilita", "auto_publish_mode", "evento")
    search_fields = ("testo", "autore__nome")
    autocomplete_fields = ("autore", "korp_visibilita", "evento", "converted_post")
    summernote_fields = ("testo",)
    readonly_fields = ("created_at", "expires_at")
    inlines = [SocialStoryTagInline, SocialStoryViewInline, SocialStoryReactionInline, SocialStoryReplyInline]


class SocialStoryHighlightItemInline(admin.TabularInline):
    model = SocialStoryHighlightItem
    extra = 0
    autocomplete_fields = ("story",)
    readonly_fields = ("added_at",)


@admin.register(SocialStoryHighlight)
class SocialStoryHighlightAdmin(admin.ModelAdmin):
    list_display = ("owner", "titolo", "created_at")
    search_fields = ("owner__nome", "titolo")
    autocomplete_fields = ("owner",)
    readonly_fields = ("created_at",)
    inlines = [SocialStoryHighlightItemInline]


@admin.register(SocialStoryHighlightItem)
class SocialStoryHighlightItemAdmin(admin.ModelAdmin):
    list_display = ("highlight", "story", "added_at")
    autocomplete_fields = ("highlight", "story")
    readonly_fields = ("added_at",)


@admin.register(SocialStoryView)
class SocialStoryViewAdmin(admin.ModelAdmin):
    list_display = ("story", "viewer", "viewed_at")
    autocomplete_fields = ("story", "viewer")
    readonly_fields = ("viewed_at",)


@admin.register(SocialStoryReaction)
class SocialStoryReactionAdmin(admin.ModelAdmin):
    list_display = ("story", "autore", "emoji", "created_at")
    autocomplete_fields = ("story", "autore")
    readonly_fields = ("created_at",)


@admin.register(SocialStoryReply)
class SocialStoryReplyAdmin(SummernoteModelAdmin):
    list_display = ("story", "autore", "created_at")
    autocomplete_fields = ("story", "autore")
    readonly_fields = ("created_at",)
    summernote_fields = ("testo",)
