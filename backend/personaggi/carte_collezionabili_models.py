"""
Carte collezionabili «Cronache delle Sette Elegie» — catalogo, collezione, reliquiario, bustine.
"""
from __future__ import annotations

from io import BytesIO
import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone

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

CARTA_LAYOUT_STANDARD = "STD"
CARTA_LAYOUT_FULL = "FULL"
CARTA_LAYOUT_CHOICES = [
    (CARTA_LAYOUT_STANDARD, "Standard"),
    (CARTA_LAYOUT_FULL, "Full-size borderless"),
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
MAZZO_MIN_PERSONAGGI = 8
MAZZO_MAX_TERRE = 2
MAZZO_MAX_AURE = 3
MAZZI_DUELLO_MAX_PER_PG = 5

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


def _compress_image_field(instance, field_name: str, *, max_side: int = 1600, quality: int = 82) -> None:
    """Riduce immagini troppo pesanti lato server (upload carte/espansioni)."""
    image_field = getattr(instance, field_name, None)
    if not image_field:
        return
    try:
        from PIL import Image
    except Exception:
        return
    try:
        image_field.file.seek(0)
        img = Image.open(image_field.file)
    except Exception:
        return
    img = img.convert("RGB")
    width, height = img.size
    if max(width, height) > max_side:
        scale = max_side / float(max(width, height))
        img = img.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, format="JPEG", quality=quality, optimize=True)
    out.seek(0)
    name = (image_field.name or "upload.jpg").rsplit(".", 1)[0] + ".jpg"
    image_field.save(name, ContentFile(out.read()), save=False)


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
    mse_match_pattern = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Pattern match MSE per export keyword (opzionale).",
    )
    mse_reminder_template = models.TextField(
        blank=True,
        default="",
        help_text="Template reminder MSE; placeholder come nel nome.",
    )
    mse_export_mode = models.CharField(
        max_length=12,
        choices=[
            ("kor35", "Solo KOR35"),
            ("mse_compat", "Compatibile MSE"),
            ("both", "KOR35 + MSE"),
        ],
        default="kor35",
        help_text="Modalità export verso Card Studio / MSE.",
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


class TagCarta(SyncableModel, models.Model):
    """
    Etichetta meccanica assegnata esplicitamente alle carte (non parsata dal testo).
    Le keyword possono riferirsi ai tag negli EffectScript (buff, distruzione, filtri).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="tag_carte",
    )
    codice = models.CharField(
        max_length=40,
        db_index=True,
        help_text="Identificatore univoco per campagna, es. CAVALIERE",
    )
    nome = models.CharField(max_length=80, help_text="Nome mostrato, es. Cavaliere")
    descrizione = models.TextField(
        blank=True,
        default="",
        help_text="Spiegazione per staff / glossario.",
    )
    colore = models.CharField(
        max_length=7,
        blank=True,
        default="",
        help_text="Colore UI opzionale (#RRGGBB).",
    )
    attiva = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Tag carta"
        verbose_name_plural = "Tag carte"
        ordering = ["nome"]
        unique_together = [("campagna", "codice")]

    def __str__(self):
        return self.nome or self.codice


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
    in_vendita = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Se false, le bustine dell'espansione non sono acquistabili.",
    )
    vendita_dal = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Inizio finestra vendita bustine (opzionale).",
    )
    vendita_al = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fine finestra vendita bustine (opzionale).",
    )
    legale_duello = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Se false, carte dell'espansione non legali nei mazzi duello.",
    )
    disclaimer_disattiva = models.TextField(
        blank=True,
        default="",
        help_text="Nota staff mostrata quando si disattiva l'espansione.",
    )
    gioco_definizione = models.ForeignKey(
        "personaggi.CarteGiocoDefinizione",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="espansioni",
        help_text="Definizione gioco piattaforma (Card Studio / Arena).",
    )
    studio_set_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadati set Card Studio / MSE (studio_set_spec_v1).",
    )
    mse_set_riferimento = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Identificatore o path package .mse-set collegato.",
    )
    default_studio_template = models.ForeignKey(
        "personaggi.CarteStudioTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="espansioni_default",
        help_text="Template predefinito per nuove carte in questa espansione.",
    )

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

    def save(self, *args, **kwargs):
        _compress_image_field(self, "immagine", max_side=1920, quality=84)
        return super().save(*args, **kwargs)


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
    testo_reliquiario = models.TextField(
        blank=True,
        default="",
        help_text="Testo mostrato sullo slot reliquiario quando equipaggiata (sostituisce il testo gioco).",
    )
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
    tags = models.ManyToManyField(
        TagCarta,
        blank=True,
        related_name="carte",
        help_text="Tag meccanici (Cavaliere, Orda, …) usati da keyword ed effetti.",
    )
    bonus_equip = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Bonus equip: reliquiario {"stat_sigla":"FOR","valore":1}; '
            'duello {"forza":1,"robustezza_se_leader":2} o '
            '{"duello":[{"stat":"forza","valore":2},{"stat":"robustezza","valore":2,"se_leader":true}]}'
        ),
    )
    effect_scripts = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "EffectScript v1 sulla carta (senza keyword nel testo). "
            "Ogni elemento: {codice?, nome?, script: {version, trigger, steps, params?}}."
        ),
    )
    legale_duello = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Se false, carta non legale nei mazzi duello.",
    )
    bandita = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Se true, carta bandita dai mazzi duello.",
    )
    ban_reason = models.TextField(
        blank=True,
        default="",
        help_text="Motivazione ban mostrata in staff/UI.",
    )
    layout_versione = models.CharField(
        max_length=4,
        choices=CARTA_LAYOUT_CHOICES,
        default=CARTA_LAYOUT_STANDARD,
        help_text="Layout visuale carta (standard/full-size).",
    )
    studio_template = models.ForeignKey(
        "personaggi.CarteStudioTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carte",
        help_text="Template Card Studio per rendering stampa.",
    )
    studio_carta_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="Campi layout/stampa extra (studio_card_spec_v1).",
    )
    arena_playable_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot normalizzato per Card Arena (playable_card_spec_v1).",
    )
    mse_campi = models.JSONField(
        default=dict,
        blank=True,
        help_text="Mappa campi raw MSE importati (round-trip export).",
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

    def errata_attiva(self, *, when=None):
        when = when or timezone.now()
        return (
            self.errata.filter(attiva=True, effective_from__lte=when)
            .order_by("-effective_from", "-updated_at")
            .first()
        )

    def save(self, *args, **kwargs):
        _compress_image_field(self, "immagine", max_side=1600, quality=82)
        return super().save(*args, **kwargs)


class CartaErrata(SyncableModel, models.Model):
    """Override schedulati gameplay carta attivi da una data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="carte_errata",
    )
    carta = models.ForeignKey(
        CartaCollezionabile,
        on_delete=models.CASCADE,
        related_name="errata",
    )
    effective_from = models.DateTimeField(db_index=True)
    attiva = models.BooleanField(default=True, db_index=True)
    versione = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Codice versione errata (es. 2026.07-A).",
    )
    pubblicata = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Se true, mostrata ai giocatori nel riepilogo storico errata.",
    )
    pubblicata_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp pubblicazione errata verso i giocatori.",
    )
    pubblicata_nota = models.TextField(
        blank=True,
        default="",
        help_text="Nota di rilascio mostrata nell'interfaccia personaggi.",
    )
    titolo = models.CharField(max_length=120, blank=True, default="")
    descrizione = models.TextField(blank=True, default="")
    testo_gioco_override = models.TextField(blank=True, default="")
    costo_gioco_override = models.PositiveSmallIntegerField(null=True, blank=True)
    attacco_override = models.PositiveSmallIntegerField(null=True, blank=True)
    salute_override = models.PositiveSmallIntegerField(null=True, blank=True)
    iniziativa_override = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(5)],
    )
    effect_scripts_override = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "Errata carta"
        verbose_name_plural = "Errata carte"
        ordering = ["-effective_from", "-updated_at"]
        indexes = [models.Index(fields=["campagna", "effective_from", "attiva"])]

    def __str__(self):
        return f"Errata {self.carta.nome} @ {self.effective_from:%Y-%m-%d %H:%M}"


COMBO_TRIGGER_LEGAME = "LEGAME"
COMBO_TRIGGER_SET = "SET"
COMBO_TRIGGER_CARTE = "CARTE"
COMBO_TRIGGER_ENERGIE_NAT = "ENERGIE_NAT"
COMBO_TRIGGER_ENERGIE_SOP = "ENERGIE_SOP"
COMBO_TRIGGER_CHOICES = [
    (COMBO_TRIGGER_LEGAME, "Stesso legame_id"),
    (COMBO_TRIGGER_SET, "Stesso set_collezione"),
    (COMBO_TRIGGER_CARTE, "Carte specifiche (codici)"),
    (COMBO_TRIGGER_ENERGIE_NAT, "Energie naturali distinte"),
    (COMBO_TRIGGER_ENERGIE_SOP, "Energie soprannaturali distinte"),
]


class ComboReliquiario(SyncableModel, models.Model):
    """Combo reliquiario definita da staff (non compare sulla carta)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.CASCADE,
        related_name="combo_reliquiario",
    )
    codice = models.CharField(max_length=60, db_index=True)
    nome = models.CharField(max_length=120)
    testo = models.TextField(
        blank=True,
        default="",
        help_text="Testo mostrato nella sezione combo attive sotto il reliquiario.",
    )
    colore = models.CharField(
        max_length=7,
        default="#10b981",
        help_text="Colore bordo/testo combo (es. #10b981).",
    )
    tipo_trigger = models.CharField(max_length=12, choices=COMBO_TRIGGER_CHOICES, db_index=True)
    param_legame_id = models.CharField(max_length=80, blank=True, default="")
    param_set_collezione = models.CharField(max_length=80, blank=True, default="")
    param_carte_codici = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista codici carta richiesti, es. ["ST-KAEL-001","ST-KAEL-002"].',
    )
    param_min_count = models.PositiveSmallIntegerField(
        default=2,
        help_text="Soglia minima (conteggio legame/set/energie). Ignorata per trigger CARTE.",
    )
    ordine = models.PositiveSmallIntegerField(default=0)
    attiva = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Combo reliquiario"
        verbose_name_plural = "Combo reliquiario"
        ordering = ["ordine", "nome"]
        unique_together = [("campagna", "codice")]

    def __str__(self):
        return self.nome


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
    leader_carta_posseduta_id = models.CharField(
        max_length=36,
        blank=True,
        default="",
        help_text="UUID CartaPosseduta Leader (Personaggio comandante, fuori dal mazzo).",
    )
    is_default = models.BooleanField(default=False)
    formato_codice = models.CharField(
        max_length=40,
        default="standard_15",
        db_index=True,
        help_text="Codice formato Arena (es. standard_15, sealed).",
    )
    arena_deck_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadati mazzo per Card Arena (arena_deck_spec_v1).",
    )

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
    leader_sfidante_id = models.CharField(max_length=36, blank=True, default="")
    leader_sfidato_id = models.CharField(max_length=36, blank=True, default="")
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


# --- Mercato / scambio carte tra personaggi ---
SCAMBIO_STATO_APERTA = "APR"
SCAMBIO_STATO_ACCETTATA = "ACC"
SCAMBIO_STATO_ANNULLATA = "ANN"
SCAMBIO_STATO_SCADUTA = "SCD"
SCAMBIO_STATO_CHOICES = [
    (SCAMBIO_STATO_APERTA, "Aperta"),
    (SCAMBIO_STATO_ACCETTATA, "Accettata"),
    (SCAMBIO_STATO_ANNULLATA, "Annullata"),
    (SCAMBIO_STATO_SCADUTA, "Scaduta"),
]


class OffertaScambioCarte(SyncableModel, models.Model):
    """
    Offerta di scambio carte tra personaggi della stessa campagna.
    MVP: persistenza + admin; API/UI mercato in sviluppo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="offerte_scambio_carte",
    )
    offerente = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="offerte_scambio_carte_inviate",
    )
    carta_offerta = models.ForeignKey(
        "CartaPosseduta",
        on_delete=models.CASCADE,
        related_name="offerte_scambio",
    )
    richiesta_carta = models.ForeignKey(
        "CartaCollezionabile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offerte_scambio_richieste",
        help_text="Carta catalogo desiderata (qualsiasi copia posseduta dall'accettante).",
    )
    richiesta_crediti = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Crediti richiesti in aggiunta o al posto di una carta.",
    )
    messaggio = models.TextField(blank=True, default="")
    stato = models.CharField(
        max_length=3,
        choices=SCAMBIO_STATO_CHOICES,
        default=SCAMBIO_STATO_APERTA,
        db_index=True,
    )
    accettante = models.ForeignKey(
        "Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offerte_scambio_accettate",
    )
    accettata_at = models.DateTimeField(null=True, blank=True)
    carta_contropartita = models.ForeignKey(
        "CartaPosseduta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offerte_scambio_contropartita",
        help_text="Copia ceduta dall'accettante al completamento (se richiesta carta).",
    )
    commissione_crediti = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    crediti_trasferiti = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Crediti netti ricevuti dall'offerente dopo commissione.",
    )

    class Meta:
        verbose_name = "Offerta scambio carte"
        verbose_name_plural = "Offerte scambio carte"
        ordering = ["-updated_at"]

    def __str__(self):
        richiesta = self.richiesta_carta.nome if self.richiesta_carta_id else "crediti"
        return f"{self.offerente.nome} offre carta → {richiesta} ({self.stato})"
