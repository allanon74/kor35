import os
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


def social_post_media_upload_to(instance, filename):
    return f"social/posts/{instance.autore_id}/{filename}"


def social_profile_image_upload_to(instance, filename):
    return f"social/profiles/{instance.personaggio_id}/{filename}"


class SocialProfile(SyncableModel, models.Model):
    personaggio = models.OneToOneField(Personaggio, on_delete=models.CASCADE, related_name="social_profile")
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

    def save(self, *args, **kwargs):
        if self.foto_principale:
            self.foto_principale = optimize_uploaded_image(self.foto_principale)
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

    class Meta:
        verbose_name = "Post Social"
        verbose_name_plural = "Post Social"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.autore.nome} - {self.titolo}"

    def clean(self):
        if not self.testo and not self.immagine and not self.video:
            raise ValidationError("Un post deve avere testo, immagine o video.")
        if self.immagine and self.video:
            raise ValidationError("Un post non puo avere contemporaneamente immagine e video.")
        if self.visibilita == SOCIAL_VISIBILITY_KORP and not self.korp_visibilita_id:
            raise ValidationError("Per la visibilita KORP devi selezionare una KORP.")
        if self.visibilita != SOCIAL_VISIBILITY_KORP and self.korp_visibilita_id:
            raise ValidationError("La KORP visibilita e ammessa solo per post visibili alla KORP.")
        if self.video and getattr(self.video, "size", 0) > MAX_VIDEO_BYTES:
            raise ValidationError(f"Video troppo grande (max {MAX_VIDEO_BYTES // (1024 * 1024)}MB).")

    def save(self, *args, **kwargs):
        if self.immagine:
            self.immagine = optimize_uploaded_image(self.immagine)
        self.clean()
        super().save(*args, **kwargs)


class SocialComment(SyncableModel, models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="comments")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_comments")
    testo = models.TextField()
    evento = models.ForeignKey(Evento, on_delete=models.SET_NULL, null=True, blank=True, related_name="social_comments")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Commento Social"
        verbose_name_plural = "Commenti Social"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.autore.nome}: {self.testo[:40]}"


class SocialLike(SyncableModel, models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="likes")
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="social_likes")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Like Social"
        verbose_name_plural = "Like Social"
        unique_together = ("post", "autore")
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.autore.nome} -> {self.post_id}"


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

        base_name = os.path.splitext(uploaded_file.name)[0]
        new_name = f"{base_name}.jpg"
        return ContentFile(output.read(), name=new_name)
    except Exception:
        return uploaded_file
