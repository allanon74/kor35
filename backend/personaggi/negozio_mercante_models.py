"""
Negozi alternativi (QR) e corporativi (tab Personaggio).
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from kor35.syncing import SyncableModel

NEGOZIO_TIPO_ALTERNATIVO = "ALT"
NEGOZIO_TIPO_CORPORATIVO = "CORP"
NEGOZIO_TIPO_CHOICES = [
    (NEGOZIO_TIPO_ALTERNATIVO, "Alternativo (QR)"),
    (NEGOZIO_TIPO_CORPORATIVO, "Corporativo (tab)"),
]

VOCE_OGGETTO_BASE = "OGB"
VOCE_OGGETTO = "OGG"
VOCE_ABILITA = "ABL"
VOCE_INFUSIONE = "INF"
VOCE_TESSITURA = "TES"
VOCE_CERIMONIALE = "CER"
VOCE_CONSUMABILE = "CON"
VOCE_SERIE = "SER"
VOCE_TIPO_CHOICES = [
    (VOCE_OGGETTO_BASE, "Oggetto base (template)"),
    (VOCE_OGGETTO, "Oggetto (istanza unica)"),
    (VOCE_ABILITA, "Abilità"),
    (VOCE_INFUSIONE, "Infusione"),
    (VOCE_TESSITURA, "Tessitura"),
    (VOCE_CERIMONIALE, "Cerimoniale"),
    (VOCE_CONSUMABILE, "Consumabile (lotto)"),
    (VOCE_SERIE, "Serie (pezzo collezione)"),
]

STOCK_DISPONIBILE = "DISP"
STOCK_VENDUTO = "VEND"
STOCK_STATO_CHOICES = [
    (STOCK_DISPONIBILE, "Disponibile"),
    (STOCK_VENDUTO, "Venduto"),
]

PRESTITO_ATTIVO = "ATT"
PRESTITO_RESTITUITO = "RES"
PRESTITO_STATO_CHOICES = [
    (PRESTITO_ATTIVO, "In prestito"),
    (PRESTITO_RESTITUITO, "Restituito"),
]

DEFAULT_CONFIG_ECONOMIA = {
    "pct_vendita_min": 20,
    "pct_vendita_max": 80,
    "pct_rivendita_min": 120,
    "pct_rivendita_max": 200,
    "cr_per_livello_oggetto": 200,
    "cr_per_livello_consumabile": 20,
}


class NegozioMercante(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="negozi_mercante",
    )
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(
        blank=True,
        default="",
        help_text="Note interne / breve (non mostrata ai PG se è valorizzata la descrizione in-game).",
    )
    descrizione_immersiva = models.TextField(
        blank=True,
        default="",
        help_text="Testo HTML per i giocatori (atmosfera del negozio alla scansione QR).",
    )
    tipo_negozio = models.CharField(
        max_length=4,
        choices=NEGOZIO_TIPO_CHOICES,
        default=NEGOZIO_TIPO_ALTERNATIVO,
        db_index=True,
    )
    attivo = models.BooleanField(default=True, db_index=True)
    qr_code = models.OneToOneField(
        "QrCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="negozio_mercante",
    )
    inventario = models.OneToOneField(
        "Inventario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="negozio_mercante",
    )
    saldo_crediti = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    incassa_acquisti_catalogo = models.BooleanField(
        default=True,
        help_text="Se attivo, i CR spesi in acquisti dal catalogo staff entrano nella cassa del negozio.",
    )
    regole_apertura = models.JSONField(
        default=dict,
        blank=True,
        help_text='Es. {"modalita":"sempre_aperto"} o fasce orarie / requisiti_extra.',
    )
    regole_visibilita = models.JSONField(
        default=dict,
        blank=True,
        help_text='Per negozi corporativi: {"operator":"OR","requisiti":[...]}.',
    )
    config_economia = models.JSONField(default=dict, blank=True)
    negozio_prestiti = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Se attivo, gli oggetti del catalogo si prendono solo in prestito "
            "(restituzione a fine evento). Il prezzo della voce è il costo di noleggio (0 ammesso)."
        ),
    )
    limite_prestiti_per_personaggio = models.PositiveIntegerField(
        default=1,
        help_text=(
            "Quanti oggetti un personaggio può tenere in prestito contemporaneamente "
            "da questo negozio (solo se negozio_prestiti è attivo). Default: 1."
        ),
    )

    class Meta:
        verbose_name = "Negozio mercante"
        verbose_name_plural = "Negozi mercante"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_config_economia(self) -> dict:
        base = dict(DEFAULT_CONFIG_ECONOMIA)
        if isinstance(self.config_economia, dict):
            base.update(self.config_economia)
        return base

    def save(self, *args, **kwargs):
        from .models import Inventario

        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating and not self.inventario_id:
            inv = Inventario.objects.create(nome=f"Magazzino: {self.nome}")
            type(self).objects.filter(pk=self.pk).update(inventario_id=inv.pk)
            self.inventario_id = inv.pk
        if self.nome:
            from personaggi.negozio_mercante_avista import ensure_portale_avista

            ensure_portale_avista(self)


class NegozioMercanteVoce(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    negozio = models.ForeignKey(
        NegozioMercante,
        on_delete=models.CASCADE,
        related_name="voci",
    )
    tipo_voce = models.CharField(max_length=3, choices=VOCE_TIPO_CHOICES, db_index=True)
    prezzo_crediti = models.PositiveIntegerField(
        help_text=(
            "Prezzo in crediti (acquisto) oppure costo di noleggio se il negozio "
            "è in modalità prestiti (0 = prestito gratuito)."
        ),
    )
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)
    quantita_residua = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Null = illimitato. Per consumabili e cap oggetti base.",
    )

    oggetto_base = models.ForeignKey(
        "OggettoBase",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
    )
    oggetto = models.ForeignKey(
        "Oggetto",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
    )
    abilita = models.ForeignKey(
        "Abilita",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
    )
    infusione = models.ForeignKey(
        "Infusione",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
    )
    tessitura = models.ForeignKey(
        "Tessitura",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
    )
    cerimoniale = models.ForeignKey(
        "Cerimoniale",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
    )
    consumabile_tessitura = models.ForeignKey(
        "Tessitura",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voci_consumabile_negozio",
        help_text="Template tessitura per generare il consumabile all'acquisto.",
    )
    serie = models.ForeignKey(
        "SerieCollezione",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="voci_negozio_mercante",
        help_text="Serie collezione: all'acquisto assegna un pezzo via inventario serie (non zaino).",
    )
    consumabile_nome = models.CharField(max_length=200, blank=True, default="")
    consumabile_livello = models.PositiveIntegerField(default=1)
    consegna_istanza = models.BooleanField(
        default=False,
        help_text=(
            "Se attivo su una voce Infusione, all'acquisto crea l'oggetto fisico "
            "(Mod/Materia o Innesto/Mutazione) invece di assegnare la ricetta. "
            "Le infusioni AUM (aumenti corporei) creano sempre un'istanza."
        ),
    )
    non_vendibile = models.BooleanField(
        default=False,
        help_text=(
            "Se attivo, la voce non compare nel listino come articolo singolo: "
            "è acquistabile solo come componente di un bundle."
        ),
    )

    class Meta:
        verbose_name = "Voce negozio mercante"
        verbose_name_plural = "Voci negozio mercante"
        ordering = ["ordine", "created_at"]

    def __str__(self):
        return f"{self.negozio.nome} / {self.get_tipo_voce_display()} ({self.prezzo_crediti} CR)"


class NegozioMercanteBundle(SyncableModel, models.Model):
    """Pacchetto di voci catalogo vendute insieme a un prezzo unico."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    negozio = models.ForeignKey(
        NegozioMercante,
        on_delete=models.CASCADE,
        related_name="bundle",
    )
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True, default="")
    prezzo_crediti = models.PositiveIntegerField(
        help_text="Prezzo del pacchetto (manuale, non somma automatica delle voci).",
    )
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Bundle negozio mercante"
        verbose_name_plural = "Bundle negozi mercante"
        ordering = ["ordine", "created_at"]

    def __str__(self):
        return f"{self.negozio.nome} / bundle «{self.nome}» ({self.prezzo_crediti} CR)"


class NegozioMercanteBundleRiga(SyncableModel, models.Model):
    """Componente di un bundle: riferimento a una voce già in catalogo."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    bundle = models.ForeignKey(
        NegozioMercanteBundle,
        on_delete=models.CASCADE,
        related_name="righe",
    )
    voce = models.ForeignKey(
        NegozioMercanteVoce,
        on_delete=models.PROTECT,
        related_name="righe_bundle",
        help_text="Voce del medesimo negozio inclusa nel pacchetto.",
    )
    quantita = models.PositiveIntegerField(
        default=1,
        help_text="Quante unità di questa voce consegna un acquisto del bundle.",
    )
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Riga bundle negozio"
        verbose_name_plural = "Righe bundle negozio"
        ordering = ["ordine", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["bundle", "voce"],
                name="uniq_negozio_bundle_voce",
            ),
        ]

    def __str__(self):
        return f"{self.bundle.nome} ×{self.quantita} → {self.voce_id}"


class NegozioMercanteStock(SyncableModel, models.Model):
    """Oggetto usato rivenduto dal negozio (magazzino dinamico)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    negozio = models.ForeignKey(
        NegozioMercante,
        on_delete=models.CASCADE,
        related_name="stock",
    )
    oggetto = models.ForeignKey(
        "Oggetto",
        on_delete=models.CASCADE,
        related_name="stock_negozio_mercante",
    )
    stato = models.CharField(
        max_length=4,
        choices=STOCK_STATO_CHOICES,
        default=STOCK_DISPONIBILE,
        db_index=True,
    )
    prezzo_rivendita = models.PositiveIntegerField()
    valore_riferimento = models.PositiveIntegerField()
    venduto_da = models.ForeignKey(
        "Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="oggetti_venduti_a_negozi",
    )

    class Meta:
        verbose_name = "Stock negozio mercante"
        verbose_name_plural = "Stock negozi mercante"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.negozio.nome} ← {self.oggetto.nome} ({self.stato})"


class NegozioMercanteMovimento(SyncableModel, models.Model):
    """Audit movimenti cassa negozio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    negozio = models.ForeignKey(
        NegozioMercante,
        on_delete=models.CASCADE,
        related_name="movimenti",
    )
    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimenti_negozio_mercante",
    )
    tipo = models.CharField(max_length=20)
    importo = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_dopo = models.DecimalField(max_digits=12, decimal_places=2)
    nota = models.CharField(max_length=255, blank=True, default="")
    riferimento_voce = models.ForeignKey(
        NegozioMercanteVoce,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    riferimento_stock = models.ForeignKey(
        NegozioMercanteStock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    riferimento_bundle = models.ForeignKey(
        NegozioMercanteBundle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Movimento cassa negozio"
        verbose_name_plural = "Movimenti cassa negozi"
        ordering = ["-created_at"]


class NegozioMercantePrestito(SyncableModel, models.Model):
    """
    Traccia un oggetto fisico preso in prestito da un negozio di prestiti.
    Un personaggio può avere al più ``negozio.limite_prestiti_per_personaggio``
    prestiti ATTIVI sullo stesso negozio.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    negozio = models.ForeignKey(
        NegozioMercante,
        on_delete=models.CASCADE,
        related_name="prestiti",
    )
    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="prestiti_negozio_mercante",
    )
    oggetto = models.ForeignKey(
        "Oggetto",
        on_delete=models.CASCADE,
        related_name="prestiti_negozio_mercante",
    )
    voce = models.ForeignKey(
        NegozioMercanteVoce,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prestiti",
        help_text="Voce catalogo di origine (se prestito da listino).",
    )
    stock = models.ForeignKey(
        NegozioMercanteStock,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prestiti",
        help_text="Riga stock di origine (se prestito da usato/magazzino).",
    )
    costo_noleggio = models.PositiveIntegerField(
        default=0,
        help_text="Crediti pagati come noleggio al momento del prestito (0 = gratuito).",
    )
    stato = models.CharField(
        max_length=3,
        choices=PRESTITO_STATO_CHOICES,
        default=PRESTITO_ATTIVO,
        db_index=True,
    )
    prestato_at = models.DateTimeField(default=timezone.now)
    restituito_at = models.DateTimeField(null=True, blank=True)
    nota_restituzione = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Prestito negozio mercante"
        verbose_name_plural = "Prestiti negozi mercante"
        ordering = ["-prestato_at"]
        indexes = [
            models.Index(fields=["negozio", "personaggio", "stato"]),
            models.Index(fields=["oggetto", "stato"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["oggetto"],
                condition=models.Q(stato=PRESTITO_ATTIVO),
                name="uniq_oggetto_prestito_attivo",
            ),
        ]

    def __str__(self):
        return f"{self.negozio.nome} → {self.personaggio_id} / {self.oggetto_id} ({self.stato})"
