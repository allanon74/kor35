import os
import re
import uuid
from io import BytesIO

from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

from gestione_plot.models import Evento
from kor35.syncing import SyncableModel
from personaggi.models import Korp, Personaggio


SOCIAL_VISIBILITY_PUBLIC = "PUB"
SOCIAL_VISIBILITY_KORP = "KORP"
SOCIAL_VISIBILITY_CHOICES = [
    (SOCIAL_VISIBILITY_PUBLIC, "Pubblico"),
    (SOCIAL_VISIBILITY_KORP, "Solo KORP"),
]

MAX_IMAGE_SIZE = (1600, 1600)
MAX_VIDEO_BYTES = 30 * 1024 * 1024
MAX_POST_IMAGES = 8
STORY_TTL_HOURS = 24

SOCIAL_GROUP_ROLE_MEMBER = "MEMBER"
SOCIAL_GROUP_ROLE_ADMIN = "ADMIN"
SOCIAL_GROUP_ROLE_CHOICES = [
    (SOCIAL_GROUP_ROLE_MEMBER, "Membro"),
    (SOCIAL_GROUP_ROLE_ADMIN, "Admin"),
]

SOCIAL_GROUP_STATUS_INVITED = "INVITED"
SOCIAL_GROUP_STATUS_REQUESTED = "REQUESTED"
SOCIAL_GROUP_STATUS_ACTIVE = "ACTIVE"
SOCIAL_GROUP_STATUS_REJECTED = "REJECTED"
SOCIAL_GROUP_STATUS_CHOICES = [
    (SOCIAL_GROUP_STATUS_INVITED, "Invitato"),
    (SOCIAL_GROUP_STATUS_REQUESTED, "Richiesta inviata"),
    (SOCIAL_GROUP_STATUS_ACTIVE, "Attivo"),
    (SOCIAL_GROUP_STATUS_REJECTED, "Rifiutato"),
]


def social_post_media_upload_to(instance, filename):
    return f"social/posts/{instance.autore_id}/{filename}"


def social_post_image_upload_to(instance, filename):
    return f"social/posts/{instance.post_id}/gallery/{filename}"


def social_profile_image_upload_to(instance, filename):
    return f"social/profiles/{instance.personaggio_id}/{filename}"


def social_story_media_upload_to(instance, filename):
    return f"social/stories/{instance.autore_id}/{filename}"


class SocialProfile(SyncableModel, models.Model):
    personaggio = models.OneToOneField(Personaggio, on_delete=models.CASCADE, related_name="social_profile")
    nickname = models.CharField(max_length=120, null=True, blank=True)
    foto_principale = models.ImageField(upload_to=social_profile_image_upload_to, null=True, blank=True)
    regione = models.CharField(max_length=120, null=True, blank=True)
    prefettura = models.CharField(max_length=120, null=True, blank=True)
    descrizione = models.TextField(null=True, blank=True)
    professioni = models.TextField(null=True, blank=True)
    era_provenienza = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Profilo Social"
        verbose_name_plural = "Profili Social"

    def __str__(self):
        return f"Profilo social {self.personaggio.nome}"

    def clean(self):
        from .nickname_validation import clean_nickname_value_model

        self.nickname = clean_nickname_value_model(self.nickname)

    def save(self, *args, **kwargs):
        if self.foto_principale:
            self.foto_principale = prepare_image_upload(
                self.foto_principale, f"social/profiles/{self.personaggio_id}"
            )
        super().save(*args, **kwargs)


class SocialPost(SyncableModel, models.Model):
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_posts")
    titolo = models.CharField(max_length=180)
    testo = models.TextField(null=True, blank=True)
    immagine = models.ImageField(upload_to=social_post_media_upload_to, null=True, blank=True)
    video = models.FileField(upload_to=social_post_media_upload_to, null=True, blank=True)
    visibilita = models.CharField(max_length=4, choices=SOCIAL_VISIBILITY_CHOICES, default=SOCIAL_VISIBILITY_PUBLIC)
    korp_visibilita = models.ForeignKey(Korp, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_posts_riservati")
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_posts")
    created_at = models.DateTimeField(default=timezone.now)
    public_slug = models.SlugField(max_length=64, unique=True, blank=True)
    likes_base = models.PositiveIntegerField(
        default=1,
        help_text="Like iniziali simulati (statici) alla creazione del post.",
    )

    class Meta:
        verbose_name = "Post Social"
        verbose_name_plural = "Post Social"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.autore.nome} - {self.titolo}"

    def clean(self):
        has_gallery = bool(self.pk and self.post_images.exists())
        has_media = bool(self.testo or self.immagine or self.video or has_gallery)
        if not has_media:
            raise ValidationError("Un post deve avere testo, immagine o video.")
        if self.immagine and self.video:
            raise ValidationError("Un post non puo avere contemporaneamente immagine e video.")
        if self.pk and self.video and self.post_images.exists():
            raise ValidationError("Un post non puo avere contemporaneamente video e piu immagini.")
        if self.pk:
            n_images = self.post_images.count()
            if self.immagine and n_images == 0:
                n_images = 1
            if n_images > MAX_POST_IMAGES:
                raise ValidationError(f"Massimo {MAX_POST_IMAGES} immagini per post.")
        if self.visibilita == SOCIAL_VISIBILITY_KORP and not self.korp_visibilita_id:
            raise ValidationError("Per la visibilita KORP devi selezionare una KORP.")
        if self.visibilita != SOCIAL_VISIBILITY_KORP and self.korp_visibilita_id:
            raise ValidationError("La KORP visibilita e ammessa solo per post visibili alla KORP.")
        # Nota sync/offline:
        # In modalità replica i file fisici vengono sincronizzati via rsync, non via JSON.
        # Durante una sync DB può arrivare prima del file → size() può sollevare FileNotFoundError.
        if self.video:
            try:
                if getattr(self.video, "size", 0) > MAX_VIDEO_BYTES:
                    raise ValidationError(
                        f"Video troppo grande (max {MAX_VIDEO_BYTES // (1024 * 1024)}MB)."
                    )
            except FileNotFoundError:
                pass

    def save(self, *args, **kwargs):
        if not self.public_slug:
            self.public_slug = uuid.uuid4().hex[:16]
        if self.immagine:
            self.immagine = prepare_image_upload(
                self.immagine, f"social/posts/{self.autore_id}"
            )
        self.clean()
        super().save(*args, **kwargs)


class SocialPostImage(SyncableModel, models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="post_images")
    immagine = models.ImageField(upload_to=social_post_image_upload_to)
    ordine = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Immagine post social"
        verbose_name_plural = "Immagini post social"
        ordering = ["ordine", "id"]
        unique_together = ("post", "ordine")

    def __str__(self):
        return f"Immagine {self.ordine} post {self.post_id}"

    def save(self, *args, **kwargs):
        if self.immagine:
            self.immagine = prepare_image_upload(
                self.immagine, f"social/posts/{self.post_id}/gallery"
            )
        super().save(*args, **kwargs)
        from .post_media import sync_post_cover_image

        sync_post_cover_image(self.post)


class SocialComment(SyncableModel, models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="comments")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_comments")
    testo = models.TextField()
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_comments")
    created_at = models.DateTimeField(default=timezone.now)
    likes_base = models.PositiveIntegerField(
        default=1,
        help_text="Like iniziali simulati (statici) alla creazione del commento.",
    )

    class Meta:
        verbose_name = "Commento Social"
        verbose_name_plural = "Commenti Social"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.autore.nome}: {self.testo[:40]}"


class SocialLike(SyncableModel, models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="likes")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_likes")
    peso_like = models.PositiveIntegerField(
        default=1,
        help_text="Peso statico del like (simulazione popolazione).",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Like Social"
        verbose_name_plural = "Like Social"
        unique_together = ("post", "autore")
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.autore.nome} -> {self.post_id}"


class SocialCommentLike(SyncableModel, models.Model):
    comment = models.ForeignKey(SocialComment, on_delete=models.CASCADE, related_name="likes")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_comment_likes")
    peso_like = models.PositiveIntegerField(
        default=1,
        help_text="Peso statico del like al commento.",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Like Commento Social"
        verbose_name_plural = "Like Commenti Social"
        unique_together = ("comment", "autore")
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.autore.nome} -> comment {self.comment_id}"


class SocialPostTag(SyncableModel, models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="tags")
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="tagged_in_social_posts")

    class Meta:
        verbose_name = "Tag Post Social"
        verbose_name_plural = "Tag Post Social"
        unique_together = ("post", "personaggio")


class SocialCommentTag(SyncableModel, models.Model):
    comment = models.ForeignKey(SocialComment, on_delete=models.CASCADE, related_name="tags")
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="tagged_in_social_comments")

    class Meta:
        verbose_name = "Tag Commento Social"
        verbose_name_plural = "Tag Commento Social"
        unique_together = ("comment", "personaggio")


class SocialGroup(SyncableModel, models.Model):
    nome = models.CharField(max_length=160)
    slug = models.SlugField(max_length=64, unique=True, blank=True)
    descrizione = models.TextField(null=True, blank=True)
    creatore = models.ForeignKey(
        Personaggio, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_groups_created"
    )
    is_hidden = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Gruppo Social"
        verbose_name_plural = "Gruppi Social"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid4().hex[:16]
        super().save(*args, **kwargs)


class SocialGroupMembership(SyncableModel, models.Model):
    group = models.ForeignKey(SocialGroup, on_delete=models.CASCADE, related_name="memberships")
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_group_memberships")
    ruolo = models.CharField(max_length=10, choices=SOCIAL_GROUP_ROLE_CHOICES, default=SOCIAL_GROUP_ROLE_MEMBER)
    status = models.CharField(max_length=10, choices=SOCIAL_GROUP_STATUS_CHOICES, default=SOCIAL_GROUP_STATUS_REQUESTED)
    invited_by = models.ForeignKey(
        Personaggio, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_group_invites_sent"
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Membro Gruppo Social"
        verbose_name_plural = "Membri Gruppi Social"
        unique_together = ("group", "personaggio")
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.group.nome} - {self.personaggio.nome} ({self.status})"

    def save(self, *args, **kwargs):
        if self.status == SOCIAL_GROUP_STATUS_ACTIVE and not self.joined_at:
            self.joined_at = timezone.now()
        super().save(*args, **kwargs)


class SocialGroupPost(SyncableModel, models.Model):
    group = models.ForeignKey(SocialGroup, on_delete=models.CASCADE, related_name="posts")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_group_posts")
    titolo = models.CharField(max_length=180)
    testo = models.TextField(null=True, blank=True)
    immagine = models.ImageField(upload_to=social_post_media_upload_to, null=True, blank=True)
    video = models.FileField(upload_to=social_post_media_upload_to, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Post Gruppo Social"
        verbose_name_plural = "Post Gruppi Social"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.group.nome} - {self.titolo}"

    def clean(self):
        if not self.testo and not self.immagine and not self.video:
            raise ValidationError("Un post di gruppo deve avere testo, immagine o video.")
        if self.immagine and self.video:
            raise ValidationError("Un post di gruppo non puo avere contemporaneamente immagine e video.")
        if self.video:
            try:
                if getattr(self.video, "size", 0) > MAX_VIDEO_BYTES:
                    raise ValidationError(
                        f"Video troppo grande (max {MAX_VIDEO_BYTES // (1024 * 1024)}MB)."
                    )
            except FileNotFoundError:
                pass

    def save(self, *args, **kwargs):
        if self.immagine:
            self.immagine = prepare_image_upload(
                self.immagine, f"social/posts/{self.autore_id}"
            )
        self.clean()
        super().save(*args, **kwargs)


class SocialGroupMessage(SyncableModel, models.Model):
    group = models.ForeignKey(SocialGroup, on_delete=models.CASCADE, related_name="messages")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_group_messages")
    testo = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Messaggio Gruppo Social"
        verbose_name_plural = "Messaggi Gruppi Social"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.group.nome} - {self.autore.nome}: {self.testo[:30]}"


class SocialStory(SyncableModel, models.Model):
    AUTO_PUBLISH_OFF = "OFF"
    AUTO_PUBLISH_NOW = "NOW"
    AUTO_PUBLISH_ON_EXPIRE = "EXPIRE"
    AUTO_PUBLISH_CHOICES = [
        (AUTO_PUBLISH_OFF, "Non pubblicare come post"),
        (AUTO_PUBLISH_NOW, "Pubblica subito anche come post"),
        (AUTO_PUBLISH_ON_EXPIRE, "Pubblica come post alla scadenza"),
    ]

    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_stories")
    testo = models.TextField(null=True, blank=True)
    media = models.FileField(upload_to=social_story_media_upload_to, null=True, blank=True)
    text_size = models.PositiveSmallIntegerField(default=22)
    visibilita = models.CharField(max_length=4, choices=SOCIAL_VISIBILITY_CHOICES, default=SOCIAL_VISIBILITY_PUBLIC)
    korp_visibilita = models.ForeignKey(
        Korp, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_stories_riservate"
    )
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_stories")
    auto_publish_mode = models.CharField(
        max_length=10, choices=AUTO_PUBLISH_CHOICES, default=AUTO_PUBLISH_OFF
    )
    converted_post = models.ForeignKey(
        "SocialPost", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_stories"
    )
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Story Social"
        verbose_name_plural = "Stories Social"
        ordering = ["-created_at", "-id"]

    def clean(self):
        if not self.testo and not self.media:
            raise ValidationError("Una story deve avere testo o media.")
        if int(self.text_size or 22) < 12 or int(self.text_size or 22) > 56:
            raise ValidationError("Dimensione testo story non valida (12-56).")
        if self.visibilita == SOCIAL_VISIBILITY_KORP and not self.korp_visibilita_id:
            raise ValidationError("Per la visibilita KORP devi selezionare una KORP.")
        if self.visibilita != SOCIAL_VISIBILITY_KORP and self.korp_visibilita_id:
            raise ValidationError("La KORP visibilita e ammessa solo per story visibili alla KORP.")
        if self.media:
            try:
                if getattr(self.media, "size", 0) > MAX_VIDEO_BYTES:
                    # Limite anche per immagini grandi, coerente con video.
                    raise ValidationError(
                        f"Media troppo grande (max {MAX_VIDEO_BYTES // (1024 * 1024)}MB)."
                    )
            except FileNotFoundError:
                pass

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = (self.created_at or timezone.now()) + timezone.timedelta(hours=STORY_TTL_HOURS)
        # Se è un'immagine, comprimila (come per i post).
        if self.media and hasattr(self.media, "name"):
            name = str(self.media.name or "").lower()
            if name.endswith((".jpg", ".jpeg", ".png", ".webp")):
                self.media = prepare_image_upload(
                    self.media, f"social/stories/{self.autore_id}"
                )
        self.clean()
        super().save(*args, **kwargs)


def social_story_active_q(now=None):
    """Story ancora visibili nel feed (24h da created_at se expires_at mancante)."""
    from django.db.models import Q

    now = now or timezone.now()
    cutoff = now - timezone.timedelta(hours=STORY_TTL_HOURS)
    return Q(expires_at__gt=now) | Q(expires_at__isnull=True, created_at__gt=cutoff)


def social_story_expired_q(now=None):
    from django.db.models import Q

    now = now or timezone.now()
    cutoff = now - timezone.timedelta(hours=STORY_TTL_HOURS)
    return Q(expires_at__lte=now) | Q(expires_at__isnull=True, created_at__lte=cutoff)


class SocialStoryTag(SyncableModel, models.Model):
    story = models.ForeignKey(SocialStory, on_delete=models.CASCADE, related_name="tags")
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="tagged_in_social_stories")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Tag Story Social"
        verbose_name_plural = "Tag Stories Social"
        unique_together = ("story", "personaggio")


class SocialStoryView(SyncableModel, models.Model):
    story = models.ForeignKey(SocialStory, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_story_views")
    created_at = models.DateTimeField(default=timezone.now)
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Visualizzazione Story"
        verbose_name_plural = "Visualizzazioni Stories"
        unique_together = ("story", "viewer")
        ordering = ["-viewed_at", "-id"]


class SocialStoryReaction(SyncableModel, models.Model):
    story = models.ForeignKey(SocialStory, on_delete=models.CASCADE, related_name="reactions")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_story_reactions")
    emoji = models.CharField(max_length=16, default="❤️")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Reazione Story"
        verbose_name_plural = "Reazioni Stories"
        unique_together = ("story", "autore")
        ordering = ["-created_at", "-id"]


class SocialStoryReply(SyncableModel, models.Model):
    story = models.ForeignKey(SocialStory, on_delete=models.CASCADE, related_name="replies")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_story_replies")
    testo = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Risposta Story"
        verbose_name_plural = "Risposte Stories"
        ordering = ["-created_at", "-id"]


class SocialStoryHighlight(SyncableModel, models.Model):
    owner = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_story_highlights")
    titolo = models.CharField(max_length=80)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Highlight Stories"
        verbose_name_plural = "Highlights Stories"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.owner.nome} - {self.titolo}"


class SocialStoryHighlightItem(SyncableModel, models.Model):
    highlight = models.ForeignKey(SocialStoryHighlight, on_delete=models.CASCADE, related_name="items")
    story = models.ForeignKey(SocialStory, on_delete=models.CASCADE, related_name="in_highlights")
    created_at = models.DateTimeField(default=timezone.now)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Item Highlight"
        verbose_name_plural = "Items Highlights"
        unique_together = ("highlight", "story")
        ordering = ["-added_at", "-id"]


MENTION_TOKEN_REGEX = re.compile(r"@([A-Za-z0-9_]+)")
HASHTAG_TOKEN_REGEX = re.compile(r"(?<!\w)#([A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*)")
HASHTAG_MIN_LEN = 2
HASHTAG_MAX_LEN = 40


def extract_mentioned_personaggi_ids(text):
    if not text:
        return []
    tokens = set(MENTION_TOKEN_REGEX.findall(text))
    if not tokens:
        return []

    from .mention_notifications import personaggi_ids_for_mention_tokens

    return personaggi_ids_for_mention_tokens(tokens)


def extract_hashtags(text):
    if not text:
        return []
    tags = set()
    for raw in HASHTAG_TOKEN_REGEX.findall(text or ""):
        tag = raw.lower()
        if HASHTAG_MIN_LEN <= len(tag) <= HASHTAG_MAX_LEN:
            tags.add(tag)
    return sorted(tags)


def is_new_file_upload(field_file) -> bool:
    return bool(field_file) and getattr(field_file, "_committed", True) is False


def normalize_media_field_path(field_file, upload_prefix: str) -> None:
    """
    Ripara path annidati (upload_to riapplicato a ogni save) e sposta il file se serve.
    """
    if not field_file or not field_file.name:
        return
    prefix = upload_prefix.rstrip("/")
    basename = os.path.basename(field_file.name.replace("\\", "/"))
    if not basename:
        return
    normalized = f"{prefix}/{basename}"
    if field_file.name == normalized:
        return
    storage = field_file.storage
    old_name = field_file.name
    if storage.exists(old_name):
        if not storage.exists(normalized):
            with storage.open(old_name, "rb") as src:
                storage.save(normalized, src)
        storage.delete(old_name)
    field_file.name = normalized


def prepare_image_upload(field_file, upload_prefix: str):
    if not field_file:
        return field_file
    normalize_media_field_path(field_file, upload_prefix)
    if is_new_file_upload(field_file):
        return optimize_uploaded_image(field_file)
    return field_file


def optimize_uploaded_image(uploaded_file):
    """
    Resize/compressione semplice per ridurre spazio media.
    """
    try:
        image = Image.open(uploaded_file)
        image = image.convert("RGB")
        image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

        output = BytesIO()
        image.save(output, format="JPEG", quality=80, optimize=True)
        output.seek(0)

        base_name = os.path.splitext(os.path.basename(uploaded_file.name.replace("\\", "/")))[0]
        new_name = f"{base_name}.jpg"
        return ContentFile(output.read(), name=new_name)
    except Exception:
        return uploaded_file
