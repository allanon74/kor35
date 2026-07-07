"""
Modelli di piattaforma Card Studio / Card Arena — predisposizione schema futuro.

Estendono il dominio carte collezionabili senza duplicare catalogo o collezione.
Vedi docs/card-platform/02-database-alignment.md
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from kor35.syncing import SyncableModel

PLATFORM_VERSION_DEFAULT = "1.0.0"

MSE_EXPORT_MODE_KOR35 = "kor35"
MSE_EXPORT_MODE_COMPAT = "mse_compat"
MSE_EXPORT_MODE_BOTH = "both"
MSE_EXPORT_MODE_CHOICES = [
    (MSE_EXPORT_MODE_KOR35, "Solo KOR35 (nessun export MSE)"),
    (MSE_EXPORT_MODE_COMPAT, "Compatibile MSE (export subset)"),
    (MSE_EXPORT_MODE_BOTH, "KOR35 + MSE (doppia sorgente)"),
]

EXCHANGE_JOB_IMPORT_MSE_SET = "import_mse_set"
EXCHANGE_JOB_EXPORT_MSE_SET = "export_mse_set"
EXCHANGE_JOB_IMPORT_MSE_STYLE = "import_mse_style"
EXCHANGE_JOB_EXPORT_MSE_STYLE = "export_mse_style"
EXCHANGE_JOB_EXPORT_PLAYABLE = "export_playable_spec"
EXCHANGE_JOB_TIPO_CHOICES = [
    (EXCHANGE_JOB_IMPORT_MSE_SET, "Import set MSE"),
    (EXCHANGE_JOB_EXPORT_MSE_SET, "Export set MSE"),
    (EXCHANGE_JOB_IMPORT_MSE_STYLE, "Import style MSE"),
    (EXCHANGE_JOB_EXPORT_MSE_STYLE, "Export style MSE"),
    (EXCHANGE_JOB_EXPORT_PLAYABLE, "Export playable spec Arena"),
]

EXCHANGE_JOB_PENDING = "pending"
EXCHANGE_JOB_RUNNING = "running"
EXCHANGE_JOB_DONE = "done"
EXCHANGE_JOB_FAILED = "failed"
EXCHANGE_JOB_STATO_CHOICES = [
    (EXCHANGE_JOB_PENDING, "In attesa"),
    (EXCHANGE_JOB_RUNNING, "In esecuzione"),
    (EXCHANGE_JOB_DONE, "Completato"),
    (EXCHANGE_JOB_FAILED, "Fallito"),
]


class CarteGiocoDefinizione(SyncableModel, models.Model):
    """
    Radice «Game» per campagna: contenitore Studio (MSE-like) + Arena (GCCG-like).
    Una campagna con carte collezionabili può avere al massimo una definizione.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.OneToOneField(
        "Campagna",
        on_delete=models.CASCADE,
        related_name="carte_gioco_definizione",
    )
    slug = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Identificatore stabile per URL/API future (es. sette-elegie).",
    )
    nome = models.CharField(max_length=120, help_text="Nome mostrato del gioco di carte.")
    descrizione = models.TextField(blank=True, default="")
    platform_version = models.CharField(
        max_length=16,
        default=PLATFORM_VERSION_DEFAULT,
        help_text="Versione contratti JSON (playable_spec, duel_state, …).",
    )
    studio_abilitato = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Card Studio attivo per questa campagna.",
    )
    arena_abilitata = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Card Arena attivo per questa campagna.",
    )
    mse_game_name = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Nome package MSE game per export (opzionale).",
    )
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadati estensibili (licenze, autori, note bridge).",
    )

    class Meta:
        verbose_name = "Definizione gioco carte"
        verbose_name_plural = "Definizioni gioco carte"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.campagna.nome})"


class CarteStudioTemplate(SyncableModel, models.Model):
    """
    Template / stylesheet Card Studio (equivalente MSE style package).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    gioco_definizione = models.ForeignKey(
        CarteGiocoDefinizione,
        on_delete=models.CASCADE,
        related_name="studio_templates",
    )
    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="carte_studio_templates",
    )
    slug = models.CharField(max_length=80, db_index=True)
    nome = models.CharField(max_length=120)
    mse_style_riferimento = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Path o identificatore package .mse-style importato.",
    )
    layout_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dimensioni carta, DPI, layer, font (studio_layout_spec_v1).",
    )
    campi_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mappatura campi MSE ↔ campi CartaCollezionabile (studio_field_map_v1).",
    )
    attivo = models.BooleanField(default=True, db_index=True)
    ordine = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Template Card Studio"
        verbose_name_plural = "Template Card Studio"
        ordering = ["ordine", "nome"]
        unique_together = [("gioco_definizione", "slug")]

    def __str__(self):
        return self.nome


class CarteArenaRuleset(SyncableModel, models.Model):
    """
    Regole partita Card Arena per una definizione gioco (zone, formati, vittoria).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    gioco_definizione = models.OneToOneField(
        CarteGiocoDefinizione,
        on_delete=models.CASCADE,
        related_name="arena_ruleset",
    )
    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="carte_arena_ruleset",
    )
    ruleset_version = models.CharField(
        max_length=16,
        default="1.0.0",
        help_text="Versione schema arena_ruleset_spec_v1.",
    )
    zones_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="Zone tavolo (mano, campo, reliquiario, …).",
    )
    win_conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Condizioni vittoria/sconfitta/pareggio.",
    )
    formato_mazzo = models.JSONField(
        default=dict,
        blank=True,
        help_text="Limiti mazzo (es. max 15, duplicati, leader).",
    )
    effect_engine_version = models.CharField(
        max_length=8,
        default="v1",
        help_text="Versione EffectScript usata in Arena.",
    )

    class Meta:
        verbose_name = "Ruleset Card Arena"
        verbose_name_plural = "Ruleset Card Arena"

    def __str__(self):
        return f"Arena rules — {self.gioco_definizione.nome}"


class CartePlatformGiocatore(SyncableModel, models.Model):
    """
    Identità giocatore per Card Arena: bridge User ↔ Personaggio (KOR35) o standalone futuro.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.CASCADE,
        related_name="carte_platform_giocatori",
    )
    gioco_definizione = models.ForeignKey(
        CarteGiocoDefinizione,
        on_delete=models.CASCADE,
        related_name="giocatori",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carte_platform_giocatori",
    )
    personaggio = models.OneToOneField(
        "Personaggio",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carte_platform_giocatore",
        help_text="Profilo KOR35: una riga per personaggio PG.",
    )
    display_name = models.CharField(max_length=80, blank=True, default="")
    external_player_ref = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID stabile per client Arena standalone (futuro).",
    )
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Giocatore piattaforma carte"
        verbose_name_plural = "Giocatori piattaforma carte"
        constraints = [
            models.UniqueConstraint(
                fields=["campagna", "user"],
                condition=Q(user__isnull=False),
                name="personaggi_cpg_campagna_user_uniq",
            ),
            models.UniqueConstraint(
                fields=["personaggio"],
                condition=Q(personaggio__isnull=False),
                name="personaggi_cpg_personaggio_uniq",
            ),
        ]

    def __str__(self):
        if self.personaggio_id:
            return f"{self.display_name or self.personaggio} @ {self.campagna.nome}"
        return f"{self.display_name or self.user} @ {self.campagna.nome}"


class CartePlatformExchangeJob(SyncableModel, models.Model):
    """Audit job import/export MSE o export contratti Arena."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.CASCADE,
        related_name="carte_platform_exchange_jobs",
    )
    gioco_definizione = models.ForeignKey(
        CarteGiocoDefinizione,
        on_delete=models.CASCADE,
        related_name="exchange_jobs",
    )
    tipo = models.CharField(max_length=24, choices=EXCHANGE_JOB_TIPO_CHOICES, db_index=True)
    stato = models.CharField(
        max_length=12,
        choices=EXCHANGE_JOB_STATO_CHOICES,
        default=EXCHANGE_JOB_PENDING,
        db_index=True,
    )
    richiesto_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carte_platform_exchange_jobs",
    )
    payload = models.JSONField(default=dict, blank=True)
    risultato = models.JSONField(default=dict, blank=True)
    errore = models.TextField(blank=True, default="")
    completato_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Job scambio piattaforma carte"
        verbose_name_plural = "Job scambio piattaforma carte"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo} ({self.stato})"
