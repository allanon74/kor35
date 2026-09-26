"""
Contratti tra personaggi.

Il catalogo è composto da parametri, effetti e voci (clausole/compensi).
Le sei ricette di gioco sono preset, non tipi fissi sul modello.
"""
from __future__ import annotations

import uuid

from django.db import models

from kor35.syncing import SyncableModel

DURATA_GIORNI = "GIORNI"
DURATA_FINE_EVENTO = "FINE_EVENTO"
DURATA_MODI = [
    (DURATA_GIORNI, "Giorni reali"),
    (DURATA_FINE_EVENTO, "Fine evento"),
]

PARAM_INTERO = "INTERO"
PARAM_DECIMALE = "DECIMALE"
PARAM_PERCENTUALE = "PERCENTUALE"
PARAM_TESTO = "TESTO"
PARAM_SCELTA = "SCELTA"
PARAM_PERSONAGGIO = "PERSONAGGIO"
PARAM_TIPI = [
    (PARAM_INTERO, "Intero"),
    (PARAM_DECIMALE, "Decimale"),
    (PARAM_PERCENTUALE, "Percentuale"),
    (PARAM_TESTO, "Testo"),
    (PARAM_SCELTA, "Scelta"),
    (PARAM_PERSONAGGIO, "Personaggio"),
]

CHI_STAFF = "STAFF"
CHI_PROPONENTE = "PROPONENTE"
CHI_COMPILA = [
    (CHI_STAFF, "Staff"),
    (CHI_PROPONENTE, "Proponente"),
]

VOCE_CLAUSOLA = "CLAUSOLA"
VOCE_COMPENSO = "COMPENSO"
VOCE_TIPI = [
    (VOCE_CLAUSOLA, "Clausola"),
    (VOCE_COMPENSO, "Compenso"),
]

STATO_IN_ATTESA = "IN_ATTESA"
STATO_STIPULATO = "STIPULATO"
STATO_SCADUTO = "SCADUTO"
STATO_RIFIUTATO = "RIFIUTATO"
STATO_RISOLTO = "RISOLTO"
STATO_ANNULLATO = "ANNULLATO"
STATI_CONTRATTO = [
    (STATO_IN_ATTESA, "In attesa di firma"),
    (STATO_STIPULATO, "Stipulato"),
    (STATO_SCADUTO, "Scaduto"),
    (STATO_RIFIUTATO, "Rifiutato"),
    (STATO_RISOLTO, "Risolto"),
    (STATO_ANNULLATO, "Annullato"),
]
STATI_OCCUPANO_SLOT = (STATO_IN_ATTESA, STATO_STIPULATO)

ADEMP_APPLICATO = "APPLICATO"
ADEMP_IN_ATTESA = "IN_ATTESA"
ADEMP_DEBITO = "DEBITO"
ADEMP_ANNULLATO = "ANNULLATO"
ADEMP_STATI = [
    (ADEMP_APPLICATO, "Applicato"),
    (ADEMP_IN_ATTESA, "In attesa di conferma"),
    (ADEMP_DEBITO, "Debito"),
    (ADEMP_ANNULLATO, "Annullato"),
]


class ModelloContratto(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    campagna = models.ForeignKey(
        "personaggi.Campagna",
        on_delete=models.CASCADE,
        related_name="modelli_contratto",
    )
    korp = models.ForeignKey(
        "personaggi.Carriera",
        on_delete=models.PROTECT,
        related_name="modelli_contratto",
    )
    nome = models.CharField(max_length=160)
    attivo = models.BooleanField(default=True)
    chiave_esclusivita = models.CharField(max_length=64, blank=True, default="")
    durata_modo = models.CharField(max_length=16, choices=DURATA_MODI, default=DURATA_GIORNI)
    durata_giorni = models.PositiveIntegerField(default=90)
    testo = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["nome"]
        verbose_name = "Modello contratto"
        verbose_name_plural = "Modelli contratto"

    def __str__(self):
        return self.nome


class ParametroModello(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modello = models.ForeignKey(ModelloContratto, on_delete=models.CASCADE, related_name="parametri")
    chiave = models.SlugField(max_length=64)
    etichetta = models.CharField(max_length=160)
    tipo = models.CharField(max_length=16, choices=PARAM_TIPI, default=PARAM_DECIMALE)
    chi_compila = models.CharField(max_length=16, choices=CHI_COMPILA, default=CHI_STAFF)
    valore = models.JSONField(null=True, blank=True)
    vincoli = models.JSONField(default=dict, blank=True)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordine", "chiave"]
        unique_together = [("modello", "chiave")]
        verbose_name = "Parametro modello contratto"
        verbose_name_plural = "Parametri modello contratto"

    def __str__(self):
        return f"{self.modello.nome}: {self.chiave}"


class VoceModello(SyncableModel, models.Model):
    """Clausola accessoria o compenso accessorio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modello = models.ForeignKey(ModelloContratto, on_delete=models.CASCADE, related_name="voci")
    tipo = models.CharField(max_length=16, choices=VOCE_TIPI, default=VOCE_CLAUSOLA)
    nome = models.CharField(max_length=160)
    testo = models.TextField(blank=True, default="")
    obbligatoria = models.BooleanField(default=False)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordine", "nome"]
        verbose_name = "Voce modello contratto"
        verbose_name_plural = "Voci modello contratto"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.nome}"


class EffettoModello(SyncableModel, models.Model):
    """Effetto del modello (sempre attivo) oppure di una voce (se scelta)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modello = models.ForeignKey(
        ModelloContratto,
        on_delete=models.CASCADE,
        related_name="effetti",
        null=True,
        blank=True,
    )
    voce = models.ForeignKey(
        VoceModello,
        on_delete=models.CASCADE,
        related_name="effetti",
        null=True,
        blank=True,
    )
    codice = models.CharField(max_length=40)
    config = models.JSONField(default=dict, blank=True)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordine", "codice"]
        verbose_name = "Effetto modello contratto"
        verbose_name_plural = "Effetti modello contratto"

    def __str__(self):
        return self.codice


class Contratto(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modello = models.ForeignKey(
        ModelloContratto,
        on_delete=models.PROTECT,
        related_name="contratti",
    )
    campagna = models.ForeignKey(
        "personaggi.Campagna",
        on_delete=models.CASCADE,
        related_name="contratti",
    )
    proponente = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.PROTECT,
        related_name="contratti_proposti",
    )
    cliente = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.PROTECT,
        related_name="contratti_sottoscritti",
        null=True,
        blank=True,
    )
    stato = models.CharField(max_length=16, choices=STATI_CONTRATTO, default=STATO_IN_ATTESA, db_index=True)
    scadenza = models.DateTimeField()
    stipulata_at = models.DateTimeField(null=True, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    qr_code = models.OneToOneField(
        "personaggi.QrCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contratto",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contratto"
        verbose_name_plural = "Contratti"

    def __str__(self):
        return f"{self.snapshot.get('nome') or self.modello_id} ({self.stato})"


class ContrattoAdempimento(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    contratto = models.ForeignKey(Contratto, on_delete=models.CASCADE, related_name="adempimenti")
    codice_effetto = models.CharField(max_length=40)
    fonte = models.CharField(max_length=180)
    evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adempimenti_contratto",
    )
    stato = models.CharField(max_length=16, choices=ADEMP_STATI, default=ADEMP_APPLICATO)
    dovuto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    versato = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    importo_cliente = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    importo_proponente = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=240, blank=True, default="")
    dettaglio = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("contratto", "fonte")]
        ordering = ["-created_at"]
        verbose_name = "Adempimento contratto"
        verbose_name_plural = "Adempimenti contratto"

    def __str__(self):
        return f"{self.codice_effetto} {self.fonte}"


class ContrattoPost(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    contratto = models.ForeignKey(Contratto, on_delete=models.CASCADE, related_name="post_associati")
    post = models.OneToOneField(
        "social.SocialPost",
        on_delete=models.CASCADE,
        related_name="contratto_associato",
    )
    evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.CASCADE,
        related_name="contratti_post",
    )

    class Meta:
        verbose_name = "Post associato a contratto"
        verbose_name_plural = "Post associati a contratto"


class ContrattoServizio(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    contratto = models.ForeignKey(Contratto, on_delete=models.CASCADE, related_name="servizi")
    evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servizi_contratto",
    )
    unita = models.CharField(max_length=8)
    quantita = models.DecimalField(max_digits=8, decimal_places=2)
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Servizio contratto"
        verbose_name_plural = "Servizi contratto"
