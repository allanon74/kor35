"""
Carte collezionabili «Cronache delle Sette Elegie» — catalogo, collezione, reliquiario, bustine.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from kor35.syncing import SyncableModel

# --- Energie Kor (7) ---
CARTA_ENERGIA_MARZIALE = "MAR"
CARTA_ENERGIA_TECNOLOGICA = "TEC"
CARTA_ENERGIA_INNATA = "INN"
CARTA_ENERGIA_MAGICA = "MAG"
CARTA_ENERGIA_SACRA = "SAC"
CARTA_ENERGIA_PSIONICA = "PSI"
CARTA_ENERGIA_ARCANA = "ARC"
CARTA_ENERGIA_CHOICES = [
    (CARTA_ENERGIA_MARZIALE, "Marziale (Addestramento)"),
    (CARTA_ENERGIA_TECNOLOGICA, "Tecnologica (Apprendimento)"),
    (CARTA_ENERGIA_INNATA, "Innata (Genetica)"),
    (CARTA_ENERGIA_MAGICA, "Magica (Elementali)"),
    (CARTA_ENERGIA_SACRA, "Sacra (Divine)"),
    (CARTA_ENERGIA_PSIONICA, "Psionica (Mentali)"),
    (CARTA_ENERGIA_ARCANA, "Arcana (Artistiche)"),
]
CARTA_ENERGIE_NATURALI = frozenset({
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_ENERGIA_INNATA,
})
CARTA_ENERGIE_SOPRANNATURALI = frozenset({
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_ARCANA,
})

# --- Tipi carta ---
CARTA_TIPO_PERSONAGGIO = "PG"
CARTA_TIPO_OGGETTO = "OGG"
CARTA_TIPO_LUOGO = "LUO"
CARTA_TIPO_EVENTO = "EVT"
CARTA_TIPO_CHOICES = [
    (CARTA_TIPO_PERSONAGGIO, "Personaggio"),
    (CARTA_TIPO_OGGETTO, "Oggetto"),
    (CARTA_TIPO_LUOGO, "Luogo"),
    (CARTA_TIPO_EVENTO, "Evento"),
]

# --- Rarità ---
CARTA_RARITA_COMUNE = "COM"
CARTA_RARITA_NON_COMUNE = "NC"
CARTA_RARITA_RARA = "RAR"
CARTA_RARITA_EPICA = "EPI"
CARTA_RARITA_LEGGENDARIA = "LEG"
CARTA_RARITA_UNICA = "UNI"
CARTA_RARITA_CHOICES = [
    (CARTA_RARITA_COMUNE, "Comune"),
    (CARTA_RARITA_NON_COMUNE, "Non comune"),
    (CARTA_RARITA_RARA, "Rara"),
    (CARTA_RARITA_EPICA, "Epica"),
    (CARTA_RARITA_LEGGENDARIA, "Leggendaria"),
    (CARTA_RARITA_UNICA, "Unica"),
]

DEFAULT_PROBABILITA_BUSTINA = {
    CARTA_RARITA_COMUNE: 0.55,
    CARTA_RARITA_NON_COMUNE: 0.28,
    CARTA_RARITA_RARA: 0.12,
    CARTA_RARITA_EPICA: 0.04,
    CARTA_RARITA_LEGGENDARIA: 0.0095,
    CARTA_RARITA_UNICA: 0.0005,
}

CARTE_ACCESSO_OFF = "OFF"
CARTE_ACCESSO_TEST = "TEST"
CARTE_ACCESSO_OPEN = "OPEN"
CARTE_ACCESSO_CHOICES = [
    (CARTE_ACCESSO_OFF, "Disattivo (tutti)"),
    (CARTE_ACCESSO_TEST, "Testing (solo PnG staff)"),
    (CARTE_ACCESSO_OPEN, "Aperto (tutti)"),
]

CARTA_FONTE_BUSTINA = "BUST"
CARTA_FONTE_SCAMBIO = "SCAM"
CARTA_FONTE_MERCATO = "MERC"
CARTA_FONTE_STAFF = "STAF"
CARTA_FONTE_CHOICES = [
    (CARTA_FONTE_BUSTINA, "Bustina"),
    (CARTA_FONTE_SCAMBIO, "Scambio"),
    (CARTA_FONTE_MERCATO, "Mercato"),
    (CARTA_FONTE_STAFF, "Staff"),
]

RELIQUIARIO_SLOTS = 5
MAZZO_DUELLO_SIZE = 15

# Mappatura energia carta → sigla aura Punteggio (tipo AU) per colori/icona da DB
CARTA_ENERGIA_AURA_SIGLA = {
    CARTA_ENERGIA_MARZIALE: "AMZ",
    CARTA_ENERGIA_TECNOLOGICA: "ATE",
    CARTA_ENERGIA_INNATA: "AIN",
    CARTA_ENERGIA_MAGICA: "AMA",
    CARTA_ENERGIA_SACRA: "ASA",
    CARTA_ENERGIA_PSIONICA: "APS",
    CARTA_ENERGIA_ARCANA: "AAR",
}


class KeywordCarta(SyncableModel, models.Model):
    """Parola chiave di regolamento per testo carte."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="keyword_carte",
    )
    codice = models.CharField(
        max_length=40,
        db_index=True,
        help_text="Identificatore univoco per campagna, es. MUTAZIONE o EVOCAZIONE",
    )
    nome = models.CharField(
        max_length=80,
        help_text=(
            "Testo da cercare nel testo carta. Usa [X], [Y], … per parametri "
            '(es. "Mutazione [X]" corrisponde a "Mutazione 0").'
        ),
    )
    testo_regola = models.TextField(
        help_text="Testo completo al tap/click; stessi placeholder del nome (es. …costo [X].).",
    )
    reminder_breve = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Promemoria inline; placeholder [X] sostituiti come nel testo regola.",
    )
    priorita = models.PositiveSmallIntegerField(
        default=0,
        help_text="Priorità match (più alto = preferito su overlap).",
    )
    attiva = models.BooleanField(default=True, db_index=True)
    effect_script = models.JSONField(
        blank=True,
        default=dict,
        help_text="EffectScript v1 (JSON) per automazione duello; opzionale.",
    )

    class Meta:
        verbose_name = "Keyword carta"
        verbose_name_plural = "Keyword carte"
        ordering = ["-priorita", "nome"]
        unique_together = [("campagna", "codice")]

    def __str__(self):
        return self.nome or self.codice

    def termini_match(self) -> list[str]:
        terms = []
        for t in (self.nome, self.codice):
            t = (t or "").strip()
            if t and t not in terms:
                terms.append(t)
        return terms

    def is_parametrizzata(self) -> bool:
        from personaggi.carte_keyword_utils import keyword_ha_parametri

        return keyword_ha_parametri(self.nome) or keyword_ha_parametri(self.codice)


class EspansioneCarte(SyncableModel, models.Model):
    """Collezione / espansione che raggruppa carte e bustine autonome."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="espansioni_carte",
    )
    nome = models.CharField(max_length=120)
    slug = models.CharField(
        max_length=80,
        db_index=True,
        help_text="Identificatore univoco per campagna, es. caduta-del-consiglio",
    )
    descrizione = models.TextField(blank=True, default="")
    immagine = models.ImageField(upload_to="carte_collezionabili/espansioni/", blank=True, null=True)
    ordine = models.PositiveSmallIntegerField(default=0)
    attiva = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Espansione carte"
        verbose_name_plural = "Espansioni carte"
        ordering = ["ordine", "nome"]
        unique_together = [("campagna", "slug")]
        indexes = [
            models.Index(fields=["campagna", "attiva"]),
        ]

    def __str__(self):
        return self.nome


class CartaCollezionabile(SyncableModel, models.Model):
    """Definizione catalogo carta (template)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="carte_collezionabili",
    )
    codice = models.CharField(max_length=40, db_index=True, help_text="Codice univoco per campagna, es. ST-KAEL-001")
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=3, choices=CARTA_TIPO_CHOICES, db_index=True)
    energia = models.CharField(max_length=3, choices=CARTA_ENERGIA_CHOICES, db_index=True)
    rarita = models.CharField(max_length=3, choices=CARTA_RARITA_CHOICES, db_index=True)

    costo_gioco = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(3)],
        help_text="Costo energia in partita (0–3).",
    )
    attacco = models.PositiveSmallIntegerField(null=True, blank=True)
    salute = models.PositiveSmallIntegerField(null=True, blank=True)
    iniziativa = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(5)],
    )

    testo_gioco = models.TextField(blank=True, default="")
    testo_lore = models.TextField(blank=True, default="")
    set_collezione = models.CharField(
        max_length=80,
        blank=True,
        default="",
        db_index=True,
        help_text="Deprecato: usare espansione. Slug set narrativo legacy.",
    )
    espansione = models.ForeignKey(
        EspansioneCarte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carte",
        help_text="Espansione di appartenenza.",
    )
    campagna_origine = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Slug campagna lore (ST, SP, CA, …).",
    )
    legame_id = models.CharField(
        max_length=80,
        blank=True,
        default="",
        db_index=True,
        help_text="Identificatore combo reliquiario.",
    )
    tag_tematici = models.JSONField(default=list, blank=True)
    bonus_equip = models.JSONField(
        default=dict,
        blank=True,
        help_text='Bonus passivo reliquiario, es. {"stat_sigla":"FOR","valore":1}',
    )
    duplicabile = models.BooleanField(
        default=False,
        help_text="Se true, fino a 2 copie nel mazzo da duello.",
    )
    immagine = models.ImageField(upload_to="carte_collezionabili/", blank=True, null=True)
    attiva = models.BooleanField(default=True, db_index=True)
    ordine_set = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Carta collezionabile"
        verbose_name_plural = "Carte collezionabili"
        ordering = ["espansione__ordine", "espansione__nome", "ordine_set", "nome"]
        unique_together = [("campagna", "codice")]
        indexes = [
            models.Index(fields=["campagna", "rarita", "attiva"]),
            models.Index(fields=["campagna", "set_collezione"]),
            models.Index(fields=["campagna", "espansione"]),
        ]

    def __str__(self):
        return f"{self.nome} ({self.codice})"

    @property
    def is_naturale(self):
        return self.energia in CARTA_ENERGIE_NATURALI

    @property
    def is_soprannaturale(self):
        return self.energia in CARTA_ENERGIE_SOPRANNATURALI


class ConfigurazioneCarteCollezionabili(SyncableModel, models.Model):
    """Configurazione economia carte per campagna."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.OneToOneField(
        "Campagna",
        on_delete=models.CASCADE,
        related_name="config_carte_collezionabili",
    )
    abilitata = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Deprecato: usare accesso_modo.",
    )
    accesso_modo = models.CharField(
        max_length=4,
        choices=CARTE_ACCESSO_CHOICES,
        default=CARTE_ACCESSO_OFF,
        db_index=True,
        help_text="OFF=nessuno, TEST=solo PnG (tipologia non giocante), OPEN=tutti i PG.",
    )
    pity_soglia = models.PositiveSmallIntegerField(
        default=20,
        help_text="Bustine senza Rara+ prima del pity.",
    )
    max_bustine_giorno = models.PositiveSmallIntegerField(
        default=10,
        help_text="Limite aperture bustina per PG al giorno.",
    )
    mercato_commissione_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("8.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        verbose_name = "Configurazione carte collezionabili"
        verbose_name_plural = "Configurazioni carte collezionabili"

    def __str__(self):
        return f"Config carte — {self.campagna.nome}"


class BustinaCarte(SyncableModel, models.Model):
    """Tipo di bustina acquistabile in-game."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="bustine_carte",
    )
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(blank=True, default="")
    costo_crediti = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    carte_per_bustina = models.PositiveSmallIntegerField(default=5)
    espansione = models.ForeignKey(
        EspansioneCarte,
        on_delete=models.PROTECT,
        related_name="bustine",
        null=True,
        blank=True,
        help_text="Espansione di appartenenza (bustine raggruppate per collezione).",
    )
    set_collezione = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Deprecato: usare espansione. Se valorizzato, limita il pool legacy.",
    )
    probabilita_rarita = models.JSONField(default=dict, blank=True)
    garantisce_min_rarita = models.CharField(
        max_length=3,
        choices=CARTA_RARITA_CHOICES,
        blank=True,
        default="",
        help_text="Rarità minima garantita (es. NC = almeno una Non comune).",
    )
    attiva = models.BooleanField(default=True, db_index=True)
    ordine = models.PositiveSmallIntegerField(default=0)
    qr_code = models.OneToOneField(
        "QrCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bustina_carte",
    )

    class Meta:
        verbose_name = "Bustina carte"
        verbose_name_plural = "Bustine carte"
        ordering = ["espansione__ordine", "ordine", "nome"]

    def __str__(self):
        return self.nome

    def probabilita_effettive(self):
        base = dict(DEFAULT_PROBABILITA_BUSTINA)
        if isinstance(self.probabilita_rarita, dict):
            for k, v in self.probabilita_rarita.items():
                if k in base:
                    base[k] = float(v)
        tot = sum(base.values())
        if tot <= 0:
            return dict(DEFAULT_PROBABILITA_BUSTINA)
        return {k: v / tot for k, v in base.items()}


class CartaPosseduta(SyncableModel, models.Model):
    """Istanza carta in collezione di un personaggio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="carte_possedute",
    )
    carta = models.ForeignKey(
        CartaCollezionabile,
        on_delete=models.PROTECT,
        related_name="possessioni",
    )
    fonte = models.CharField(max_length=4, choices=CARTA_FONTE_CHOICES, default=CARTA_FONTE_BUSTINA)
    serial_globale = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="Numero seriale per carte Uniche (1 esemplare globale).",
    )

    class Meta:
        verbose_name = "Carta posseduta"
        verbose_name_plural = "Carte possedute"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["personaggio", "carta"]),
        ]

    def __str__(self):
        return f"{self.carta.nome} → {self.personaggio.nome}"


class ReliquiarioSlot(SyncableModel, models.Model):
    """Slot reliquiario (5 carte equipaggiate per bonus passivi)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="reliquiario_slots",
    )
    slot_index = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(RELIQUIARIO_SLOTS - 1)],
    )
    carta_posseduta = models.ForeignKey(
        CartaPosseduta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="slot_reliquiario",
    )

    class Meta:
        verbose_name = "Slot reliquiario"
        verbose_name_plural = "Slot reliquiario"
        unique_together = [("personaggio", "slot_index")]
        ordering = ["personaggio", "slot_index"]

    def __str__(self):
        return f"Reliquiario {self.personaggio.nome} slot {self.slot_index}"


class MazzoDuello(SyncableModel, models.Model):
    """Mazzo da 15 carte per duelli (fase 2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="mazzi_duello",
    )
    nome = models.CharField(max_length=80, default="Mazzo principale")
    carte_possedute_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista UUID CartaPosseduta (max 15).",
    )
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Mazzo duello"
        verbose_name_plural = "Mazzi duello"
        ordering = ["-is_default", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.personaggio.nome})"


class AperturaBustinaCarte(SyncableModel, models.Model):
    """Log apertura bustina."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="aperture_bustine_carte",
    )
    bustina = models.ForeignKey(
        BustinaCarte,
        on_delete=models.PROTECT,
        related_name="aperture",
    )
    costo_pagato = models.DecimalField(max_digits=10, decimal_places=2)
    carte_ottenute_ids = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "Apertura bustina carte"
        verbose_name_plural = "Aperture bustine carte"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.bustina.nome} — {self.personaggio.nome}"


DUELLO_STATO_LOBBY = "LOB"
DUELLO_STATO_PREMATCH = "PRE"
DUELLO_STATO_ATTESA = "ATT"
DUELLO_STATO_IN_CORSO = "COR"
DUELLO_STATO_FINITO = "FIN"
DUELLO_STATO_ANNULLATO = "ANN"
DUELLO_STATO_CHOICES = [
    (DUELLO_STATO_LOBBY, "Lobby aperta"),
    (DUELLO_STATO_PREMATCH, "Pre-partita"),
    (DUELLO_STATO_ATTESA, "In attesa"),
    (DUELLO_STATO_IN_CORSO, "In corso"),
    (DUELLO_STATO_FINITO, "Terminato"),
    (DUELLO_STATO_ANNULLATO, "Annullato"),
]

DUELLO_AVVIO_TEST = "TST"
DUELLO_AVVIO_LOBBY = "LOB"
DUELLO_AVVIO_CHOICES = [
    (DUELLO_AVVIO_TEST, "Lista (testing)"),
    (DUELLO_AVVIO_LOBBY, "Lobby QR (open)"),
]

DUELLO_MODALITA_LIVE = "LIV"
DUELLO_MODALITA_MANUALE = "MAN"
DUELLO_MODALITA_CHOICES = [
    (DUELLO_MODALITA_LIVE, "Turni live"),
    (DUELLO_MODALITA_MANUALE, "Manuale"),
]

POSTA_FONTE_RISERVA = "riserva"
POSTA_FONTE_CREDITI = "crediti"

INFLUENZA_INIZIALE = 20


class DuelloCarte(SyncableModel, models.Model):
    """Partita duello live tra due personaggi."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="duelli_carte",
    )
    sfidante = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="duelli_carte_sfidante",
    )
    sfidato = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="duelli_carte_sfidato",
        null=True,
        blank=True,
    )
    mazzo_sfidante_ids = models.JSONField(default=list, blank=True)
    mazzo_sfidato_ids = models.JSONField(default=list, blank=True)
    stato = models.CharField(
        max_length=3,
        choices=DUELLO_STATO_CHOICES,
        default=DUELLO_STATO_ATTESA,
        db_index=True,
    )
    turno_personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duelli_carte_turno",
    )
    influenza_sfidante = models.PositiveSmallIntegerField(default=INFLUENZA_INIZIALE)
    influenza_sfidato = models.PositiveSmallIntegerField(default=INFLUENZA_INIZIALE)
    stato_gioco = models.JSONField(default=dict, blank=True)
    vincitore = models.ForeignKey(
        "Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duelli_carte_vinti",
    )
    codice_invito = models.CharField(max_length=8, blank=True, default="", db_index=True)
    avvio_tipo = models.CharField(
        max_length=3,
        choices=DUELLO_AVVIO_CHOICES,
        blank=True,
        default="",
        db_index=True,
    )
    modalita_partita = models.CharField(
        max_length=3,
        choices=DUELLO_MODALITA_CHOICES,
        default=DUELLO_MODALITA_LIVE,
        db_index=True,
    )
    stato_prematch = models.JSONField(default=dict, blank=True)
    posta_cr = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    qr_code = models.OneToOneField(
        "QrCode",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duello_lobby",
    )

    class Meta:
        verbose_name = "Duello carte"
        verbose_name_plural = "Duelli carte"
        ordering = ["-updated_at"]

    def __str__(self):
        nome_b = self.sfidato.nome if self.sfidato_id else "?"
        return f"{self.sfidante.nome} vs {nome_b} ({self.stato})"
