"""
Rubriche InstaFame: contenuto ibrido on-game (sezione Rubriche) / off-game (Wiki).

Ogni rubrica raccoglie articoli in stile giornalistico. In-game gli articoli hanno
like e commenti; in Wiki vengono pubblicati come pagine di sola lettura.
"""

import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from kor35.syncing import SyncableModel

from .models import (
    MAX_POST_IMAGES,
    MAX_VIDEO_BYTES,
    prepare_image_upload,
)

RUBRICA_ARTICOLO_BOZZA = "BOZZA"
RUBRICA_ARTICOLO_PUBBLICATO = "PUBBLICATO"
RUBRICA_ARTICOLO_ARCHIVIATO = "ARCHIVIATO"
RUBRICA_ARTICOLO_STATO_CHOICES = [
    (RUBRICA_ARTICOLO_BOZZA, "Bozza"),
    (RUBRICA_ARTICOLO_PUBBLICATO, "Pubblicato"),
    (RUBRICA_ARTICOLO_ARCHIVIATO, "Archiviato"),
]

RUBRICA_WIKI_PUBBLICA = "PUBBLICA"
RUBRICA_WIKI_AUTENTICATI = "AUTENTICATI"
RUBRICA_WIKI_VISIBILITA_CHOICES = [
    (RUBRICA_WIKI_PUBBLICA, "Visibile a tutti"),
    (RUBRICA_WIKI_AUTENTICATI, "Solo utenti autenticati"),
]

MAX_ARTICOLO_IMAGES = MAX_POST_IMAGES
PAROLE_PER_MINUTO = 200

_HTML_TAG_REGEX = re.compile(r"<[^>]+>")


def rubrica_logo_upload_to(instance, filename):
    return f"social/rubriche/{instance.pk}/logo/{filename}"


def rubrica_articolo_hero_upload_to(instance, filename):
    return f"social/rubriche/{instance.rubrica_id}/articoli/{instance.pk}/{filename}"


def rubrica_articolo_gallery_upload_to(instance, filename):
    return f"social/rubriche/articoli/{instance.articolo_id}/gallery/{filename}"


def testo_semplice_da_html(html: str) -> str:
    """Testo leggibile da contenuto HTML (conteggio parole, sommari automatici)."""
    if not html:
        return ""
    senza_tag = _HTML_TAG_REGEX.sub(" ", str(html))
    senza_entita = senza_tag.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", senza_entita).strip()


def calcola_tempo_lettura(html: str) -> int:
    parole = len(testo_semplice_da_html(html).split())
    if not parole:
        return 1
    return max(1, round(parole / PAROLE_PER_MINUTO))


def _slug_univoco(model, base: str, *, campo_extra: dict, pk_corrente=None) -> str:
    radice = slugify(base or "")[:60] or uuid.uuid4().hex[:8]
    candidato = radice
    contatore = 2
    while True:
        qs = model.objects.filter(slug=candidato, **campo_extra)
        if pk_corrente:
            qs = qs.exclude(pk=pk_corrente)
        if not qs.exists():
            return candidato
        suffisso = f"-{contatore}"
        candidato = f"{radice[: 60 - len(suffisso)]}{suffisso}"
        contatore += 1


class Rubrica(SyncableModel, models.Model):
    """Testata giornalistica in-game: contenitore di articoli."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=160)
    slug = models.SlugField(max_length=80, unique=True, blank=True)
    sottotitolo = models.CharField(max_length=200, blank=True)
    descrizione = models.TextField(blank=True)
    logo = models.ImageField(upload_to=rubrica_logo_upload_to, null=True, blank=True)
    colore_accento = models.CharField(
        max_length=9,
        default="#b91c1c",
        help_text="Colore esadecimale usato per occhielli e bordi della rubrica.",
    )
    attiva = models.BooleanField(default=True)
    ordine = models.PositiveIntegerField(default=0)
    creata_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rubriche_create",
    )
    created_at = models.DateTimeField(default=timezone.now)

    pubblica_in_wiki = models.BooleanField(default=False)
    wiki_parent = models.ForeignKey(
        "gestione_plot.PaginaRegolamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rubriche_ospitate",
        help_text="Pagina wiki sotto cui pubblicare la rubrica.",
    )
    wiki_titolo = models.CharField(max_length=200, blank=True)
    wiki_ordine = models.PositiveIntegerField(default=0)
    wiki_visibilita = models.CharField(
        max_length=16,
        choices=RUBRICA_WIKI_VISIBILITA_CHOICES,
        default=RUBRICA_WIKI_AUTENTICATI,
    )
    wiki_pagina = models.ForeignKey(
        "gestione_plot.PaginaRegolamento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rubrica_generata",
        editable=False,
    )

    class Meta:
        verbose_name = "Rubrica"
        verbose_name_plural = "Rubriche"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return self.nome

    @property
    def titolo_wiki_effettivo(self) -> str:
        return (self.wiki_titolo or "").strip() or self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _slug_univoco(Rubrica, self.nome, campo_extra={}, pk_corrente=self.pk)
        if self.logo:
            self.logo = prepare_image_upload(self.logo, f"social/rubriche/{self.pk}/logo")
        super().save(*args, **kwargs)


class RubricaArticolo(SyncableModel, models.Model):
    """Articolo di una rubrica, con struttura editoriale (occhiello, sommario, hero)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rubrica = models.ForeignKey(Rubrica, on_delete=models.CASCADE, related_name="articoli")
    slug = models.SlugField(max_length=80, blank=True)
    stato = models.CharField(
        max_length=12,
        choices=RUBRICA_ARTICOLO_STATO_CHOICES,
        default=RUBRICA_ARTICOLO_BOZZA,
    )

    occhiello = models.CharField(max_length=120, blank=True)
    titolo = models.CharField(max_length=200)
    sottotitolo = models.CharField(max_length=300, blank=True)
    sommario = models.TextField(blank=True)
    corpo = models.TextField(blank=True, help_text="HTML dell'articolo (editor wiki).")

    hero_immagine = models.ImageField(upload_to=rubrica_articolo_hero_upload_to, null=True, blank=True)
    hero_didascalia = models.CharField(max_length=300, blank=True)
    video = models.FileField(upload_to=rubrica_articolo_hero_upload_to, null=True, blank=True)

    autore_personaggio = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articoli_rubrica",
    )
    firma_libera = models.CharField(
        max_length=160,
        blank=True,
        help_text="Nome di penna usato quando l'articolo non è firmato da un personaggio.",
    )
    creato_da_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articoli_rubrica_creati",
    )

    evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articoli_rubrica",
    )
    post_annuncio = models.ForeignKey(
        "social.SocialPost",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articolo_annunciato",
    )

    data_pubblicazione = models.DateTimeField(null=True, blank=True)
    ordine = models.PositiveIntegerField(default=0)
    tempo_lettura_min = models.PositiveSmallIntegerField(default=1)
    likes_base = models.PositiveIntegerField(
        default=1,
        help_text="Like iniziali simulati (statici) alla pubblicazione.",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Articolo rubrica"
        verbose_name_plural = "Articoli rubrica"
        ordering = ["-data_pubblicazione", "-created_at", "-id"]
        unique_together = ("rubrica", "slug")

    def __str__(self):
        return f"{self.rubrica.nome} - {self.titolo}"

    @property
    def is_pubblicato(self) -> bool:
        return self.stato == RUBRICA_ARTICOLO_PUBBLICATO

    @property
    def firma(self) -> str:
        if self.autore_personaggio_id:
            from .display_names import social_display_name

            return social_display_name(self.autore_personaggio)
        return self.firma_libera or "Redazione"

    def clean(self):
        if not (self.titolo or "").strip():
            raise ValidationError("Il titolo dell'articolo è obbligatorio.")
        if not self.autore_personaggio_id and not (self.firma_libera or "").strip():
            raise ValidationError("Serve un personaggio autore oppure una firma libera.")
        if self.video and self.pk and self.immagini.exists():
            raise ValidationError("Un articolo non può avere contemporaneamente video e galleria.")
        if self.video:
            # In replica il file può arrivare dopo il record (rsync): non bloccare il sync.
            try:
                if getattr(self.video, "size", 0) > MAX_VIDEO_BYTES:
                    raise ValidationError(
                        f"Video troppo grande (max {MAX_VIDEO_BYTES // (1024 * 1024)}MB)."
                    )
            except FileNotFoundError:
                pass

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _slug_univoco(
                RubricaArticolo,
                self.titolo,
                campo_extra={"rubrica_id": self.rubrica_id},
                pk_corrente=self.pk,
            )
        if self.stato == RUBRICA_ARTICOLO_PUBBLICATO and not self.data_pubblicazione:
            self.data_pubblicazione = timezone.now()
        self.tempo_lettura_min = calcola_tempo_lettura(self.corpo)
        if self.hero_immagine:
            self.hero_immagine = prepare_image_upload(
                self.hero_immagine,
                f"social/rubriche/{self.rubrica_id}/articoli/{self.pk}",
            )
        self.clean()
        super().save(*args, **kwargs)


class RubricaArticoloImmagine(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    articolo = models.ForeignKey(RubricaArticolo, on_delete=models.CASCADE, related_name="immagini")
    immagine = models.ImageField(upload_to=rubrica_articolo_gallery_upload_to)
    didascalia = models.CharField(max_length=300, blank=True)
    ordine = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Immagine articolo rubrica"
        verbose_name_plural = "Immagini articoli rubrica"
        ordering = ["ordine", "id"]
        unique_together = ("articolo", "ordine")

    def save(self, *args, **kwargs):
        if self.immagine:
            self.immagine = prepare_image_upload(
                self.immagine, f"social/rubriche/articoli/{self.articolo_id}/gallery"
            )
        super().save(*args, **kwargs)


class RubricaPermessoScrittura(SyncableModel, models.Model):
    """Autorizzazione a scrivere in una rubrica dalla sezione in-game di InstaFame."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rubrica = models.ForeignKey(Rubrica, on_delete=models.CASCADE, related_name="permessi_scrittura")
    personaggio = models.ForeignKey(
        "personaggi.Personaggio", on_delete=models.CASCADE, related_name="permessi_rubriche"
    )
    concesso_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="permessi_rubriche_concessi",
    )
    attivo = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Permesso scrittura rubrica"
        verbose_name_plural = "Permessi scrittura rubriche"
        unique_together = ("rubrica", "personaggio")
        ordering = ["rubrica__nome", "personaggio__nome"]

    def __str__(self):
        return f"{self.personaggio.nome} -> {self.rubrica.nome}"


class RubricaArticoloLike(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    articolo = models.ForeignKey(RubricaArticolo, on_delete=models.CASCADE, related_name="likes")
    autore = models.ForeignKey(
        "personaggi.Personaggio", on_delete=models.CASCADE, related_name="rubrica_articolo_likes"
    )
    peso_like = models.PositiveIntegerField(
        default=1,
        help_text="Peso statico del like (simulazione popolazione).",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Like articolo rubrica"
        verbose_name_plural = "Like articoli rubrica"
        unique_together = ("articolo", "autore")
        ordering = ["-created_at", "-id"]


class RubricaArticoloComment(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    articolo = models.ForeignKey(RubricaArticolo, on_delete=models.CASCADE, related_name="comments")
    autore = models.ForeignKey(
        "personaggi.Personaggio", on_delete=models.CASCADE, related_name="rubrica_articolo_comments"
    )
    testo = models.TextField()
    evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rubrica_articolo_comments",
    )
    likes_base = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Commento articolo rubrica"
        verbose_name_plural = "Commenti articoli rubrica"
        ordering = ["created_at", "id"]


class RubricaArticoloCommentLike(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(
        RubricaArticoloComment, on_delete=models.CASCADE, related_name="likes"
    )
    autore = models.ForeignKey(
        "personaggi.Personaggio", on_delete=models.CASCADE, related_name="rubrica_commento_likes"
    )
    peso_like = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Like commento articolo rubrica"
        verbose_name_plural = "Like commenti articoli rubrica"
        unique_together = ("comment", "autore")
        ordering = ["-created_at", "-id"]
