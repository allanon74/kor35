"""
Modelli console pilotaggio (LARP).

Tutti i modelli sono sync-safe (UUID PK + created_at/updated_at) per
funzionare nell'architettura Edge-Master con risoluzione conflitti LWW.

Convenzioni dei codici a 3 caratteri:
- carattere 1 = sottosistema della nave (alfanumerico, 1 char)
- carattere 2 = comando del sottosistema (alfanumerico, 1 char)
- carattere 3 = intensita' (cifra 0-9)
"""
from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from kor35.syncing import SyncableModel


# ---------------------------------------------------------------------------
# Catalogo configurabile da staff
# ---------------------------------------------------------------------------


def _default_curve_zero() -> dict:
    return {str(i): 0.0 for i in range(10)}


def _default_curve_guasto() -> dict:
    data = _default_curve_zero()
    data["7"] = 1.0
    data["8"] = 10.0
    data["9"] = 25.0
    return data


def _default_colori_livello() -> dict:
    # 0 bianco spento, 1..9 scala iride da violetto a rosso.
    return {
        "0": "#ffffff",
        "1": "#8a2be2",
        "2": "#4b5fd1",
        "3": "#2f8cff",
        "4": "#00b894",
        "5": "#9ccc65",
        "6": "#ffd54f",
        "7": "#ffb74d",
        "8": "#ff7043",
        "9": "#ff3b30",
    }


def _default_effetti_guasto() -> dict:
    return {
        "tipo": "none",  # none|guasto_altro_percent|guasto_random_percent|riduci_carburante_percent|riduci_batterie_percent|allunga_distanza_percent|naufragio
        "valore": 0.0,
        "target_codice": "",
    }


def _default_effetti_inversione() -> dict:
    return {
        "tipo": "none",
        "probabilita_percent": 0.0,
        "valore": 0.0,
        "target_codice": "",
    }


def _default_effetti_espulsione() -> dict:
    return {
        "tipo": "none",
        "probabilita_percent": 0.0,
        "valore": 0.0,
        "target_codice": "",
    }


class SottosistemaNave(SyncableModel, models.Model):
    """
    Sottosistema della nave (primo carattere del codice comando).

    Collegato opzionalmente a un A_vista per generare un QR scansionabile dai
    P(N)G con statistiche 0SA/0RI per provocare guasto/ripristino runtime.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    codice = models.CharField(
        max_length=1,
        unique=True,
        help_text="Singolo carattere alfanumerico maiuscolo (primo char del codice comando).",
    )
    nome = models.CharField(max_length=80)
    descrizione = models.TextField(blank=True, default="")
    a_vista = models.OneToOneField(
        "personaggi.A_vista",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sottosistema_nave",
        help_text="A_vista collegata: il QrCode su questa A_vista permette guasto/ripristino.",
    )
    durata_ripristino_secondi = models.PositiveIntegerField(
        default=60,
        help_text="Tempo di attesa dopo scansione 0RI prima che il sottosistema torni online.",
    )
    attivo = models.BooleanField(default=True)
    gruppo = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="Nome del sistema di appartenenza (es. Difesa, Alimentazione).",
    )
    ordine_gruppo = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Ordine della colonna 'sistema' nella console pilota. "
            "Usa lo stesso valore per tutti i sottosistemi appartenenti allo stesso gruppo."
        ),
    )
    ordine = models.PositiveIntegerField(
        default=0,
        help_text="Ordine dei riquadri sottosistema all'interno del gruppo nella console pilota.",
    )
    tipo = models.CharField(
        max_length=16,
        choices=[
            ("standard", "Standard"),
            ("generatore", "Generatore"),
            ("batteria", "Batteria"),
            ("serbatoio", "Serbatoio carburante"),
            ("motore", "Motore principale"),
            ("portale", "Portale transdimensionale"),
            ("manovra", "Propulsori di manovra"),
            ("compattatore", "Compattatore"),
        ],
        default="standard",
    )
    richiede_componenti_riparazione = models.BooleanField(
        default=False,
        help_text="Se attivo (e riparazione componenti abilitata in runtime), la riparazione QR consuma componenti da stiva.",
    )
    requisiti_riparazione_json = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista vincoli: specifico (mattone_id+quantita) o scelta (mattone_ids+quantita).",
    )
    richiede_componenti_ricarica = models.BooleanField(
        default=False,
        help_text="Se attivo (e toggle componenti ON), QR su batteria/serbatoio operativo consuma componenti e ricarica storage/carburante.",
    )
    requisiti_ricarica_json = models.JSONField(
        default=list,
        blank=True,
        help_text="Vincoli ricarica: come riparazione + campo ricarica (energia storage o carburante).",
    )
    coeff_produzione = models.FloatField(
        default=0.0,
        help_text="Energia prodotta per tick = livello * coeff_produzione.",
    )
    coeff_consumo_energia = models.FloatField(
        default=1.0,
        help_text="Energia assorbita per tick = livello * coeff_consumo_energia.",
    )
    coeff_consumo_carburante = models.FloatField(
        default=0.0,
        help_text="Carburante usato per tick = livello * coeff_consumo_carburante.",
    )
    coeff_effetto_speciale = models.FloatField(
        default=1.0,
        help_text="Coefficiente speciale (es. portale: moltiplicatore per livello).",
    )
    rampa_livelli_per_tick = models.PositiveSmallIntegerField(
        default=1,
        help_text="Variazione massima del livello attuale per tick verso il target (solo sistemi con inerzia).",
    )
    capacita_storage = models.FloatField(
        default=0.0,
        help_text="Capacita energetica (solo batterie).",
    )
    coeff_ricarica_storage = models.FloatField(
        default=0.5,
        help_text="Conversione energia->storage in riposo (es. 0.5 significa 2:1).",
    )
    capacita_carburante = models.FloatField(
        default=0.0,
        help_text="Capacita serbatoio carburante (solo tipo serbatoio).",
    )
    effetti_guasto_json = models.JSONField(
        default=_default_effetti_guasto,
        blank=True,
        help_text=(
            "Effetto applicato quando il sottosistema va guasto. "
            "Chiavi: tipo, valore, target_codice."
        ),
    )
    effetti_inversione_json = models.JSONField(
        default=_default_effetti_inversione,
        blank=True,
        help_text="Effetti percentuali quando si attiva 'inverti'.",
    )
    effetti_espulsione_json = models.JSONField(
        default=_default_effetti_espulsione,
        blank=True,
        help_text="Effetti percentuali quando si attiva 'espelli'.",
    )
    probabilita_guasto_7 = models.FloatField(default=0.01)
    probabilita_guasto_8 = models.FloatField(default=0.10)
    probabilita_guasto_9 = models.FloatField(default=0.25)
    guasto_percent_per_livello = models.JSONField(
        default=_default_curve_guasto,
        blank=True,
        help_text="Probabilita' guasto in percentuale per livello 0..9 (chiavi stringa).",
    )
    ripristino_percent_per_livello = models.JSONField(
        default=_default_curve_zero,
        blank=True,
        help_text="Probabilita' ripristino automatico in percentuale per tick per livello 0..9.",
    )
    colori_per_livello = models.JSONField(
        default=_default_colori_livello,
        blank=True,
        help_text="Colore HEX per ogni livello 0..9 (es. {'0':'#ffffff',...}).",
    )
    supporta_inversione = models.BooleanField(default=True)
    supporta_espulsione = models.BooleanField(default=True)
    supporta_direzioni = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Sottosistema nave"
        verbose_name_plural = "Sottosistemi nave"
        ordering = ["codice"]

    def save(self, *args, **kwargs):
        if self.codice:
            self.codice = self.codice.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codice} - {self.nome}"


class ComandoNave(SyncableModel, models.Model):
    """
    Comando della nave (secondo carattere del codice).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    codice = models.CharField(
        max_length=1,
        unique=True,
        help_text="Singolo carattere alfanumerico maiuscolo (secondo char del codice).",
    )
    nome = models.CharField(max_length=80)
    descrizione = models.TextField(blank=True, default="")
    attivo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Comando nave"
        verbose_name_plural = "Comandi nave"
        ordering = ["codice"]

    def save(self, *args, **kwargs):
        if self.codice:
            self.codice = self.codice.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codice} - {self.nome}"


class IntensitaComando(SyncableModel, models.Model):
    """
    Configurazione del terzo carattere del codice comando (0-9).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    valore = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Intensita' numerica usata come terzo carattere (0..9).",
    )
    nome = models.CharField(max_length=80, blank=True, default="")
    descrizione = models.TextField(blank=True, default="")
    attivo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Intensita comando"
        verbose_name_plural = "Intensita comandi"
        ordering = ["valore"]

    def save(self, *args, **kwargs):
        if self.valore < 0:
            self.valore = 0
        if self.valore > 9:
            self.valore = 9
        super().save(*args, **kwargs)

    def __str__(self):
        label = self.nome or f"Intensita {self.valore}"
        return f"{self.valore} - {label}"


class EventoNave(SyncableModel, models.Model):
    """
    Definizione di un evento randomico che puo' apparire sulla console.

    Logica di risoluzione:
    - codice_soluzione_esatta -> evento risolto, defcon -1
    - pattern in codici_soluzione_parziale (lista regex/jolly) -> defcon invariato
    - pattern in codici_precipizio -> precipitazione immediata (stesso formato dei parziali)
    - tutto il resto + timeout -> fallimento, defcon +1

    I pattern parziali usano `_` come jolly (singolo carattere) e maiuscole.
    Esempio: "A_5" oppure intervallo sulla terza cifra: "ML(4-9)" per ML4..ML9.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(
        help_text="Testo mostrato al pilota quando l'evento appare.",
    )
    codice_soluzione_esatta = models.CharField(
        max_length=3,
        help_text="Codice 3 char che risolve l'evento (es. 'A23').",
    )
    codici_soluzione_parziale = models.JSONField(
        default=list,
        blank=True,
        help_text='Pattern parziali: jolly "_" (es. ["A_3","_B5"]) o intervallo terza cifra (es. ["ML(4-9)"]).',
    )
    codici_precipizio = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Pattern che causano precipitazione immediata (DEFCON oltre il massimo). "
            'Stessa sintassi dei parziali. Es. ["XX9","ZZ(8-9)"]. Valutati dopo la soluzione esatta.'
        ),
    )
    regole_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Regole avanzate evento in formato JSON (opzionale, editable da staff).",
    )
    durata_base_secondi = models.PositiveIntegerField(
        default=20,
        help_text="Deprecato: la durata runtime deriva da StatoAllerta.tempo_risoluzione_secondi.",
    )
    durata_tick = models.CharField(
        max_length=16,
        default="4",
        help_text='Durata evento in tick: "N" fisso oppure "A-B" (random inclusivo tra A e B).',
    )
    peso_random = models.PositiveIntegerField(
        default=10,
        help_text="Peso relativo per la scelta random (maggiore = piu' frequente).",
    )
    sottosistema = models.ForeignKey(
        SottosistemaNave,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventi",
        help_text="Se collegato, il guasto del sottosistema impatta su questo evento.",
    )
    attivo = models.BooleanField(default=True)
    scadenza_critica = models.BooleanField(
        default=False,
        help_text=(
            "Se attivo: allo scadere dei tick dell'evento applica ca_effetto. "
            "Altrimenti l'evento termina senza fallimento critico."
        ),
    )

    class Meta:
        verbose_name = "Evento nave"
        verbose_name_plural = "Eventi nave"
        ordering = ["nome"]

    def save(self, *args, **kwargs):
        if self.codice_soluzione_esatta:
            self.codice_soluzione_esatta = self.codice_soluzione_esatta.upper()
        if isinstance(self.codici_soluzione_parziale, list):
            self.codici_soluzione_parziale = [
                str(p).upper() for p in self.codici_soluzione_parziale if p
            ]
        if isinstance(self.codici_precipizio, list):
            self.codici_precipizio = [
                str(p).upper() for p in self.codici_precipizio if p
            ]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} [{self.codice_soluzione_esatta}]"


SEQUENZA_DECOLLO = "decollo"
SEQUENZA_ATTERRAGGIO = "atterraggio"
SEQUENZA_TIPO_CHOICES = [
    (SEQUENZA_DECOLLO, "Decollo"),
    (SEQUENZA_ATTERRAGGIO, "Atterraggio"),
]


class SequenzaVolo(SyncableModel, models.Model):
    """
    Sequenza obbligatoria di codici per decollo/atterraggio.

    `codici` e' una lista ordinata di stringhe 3-char.
    Esiste una sola sequenza attiva per tipo (singleton logico).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=16, choices=SEQUENZA_TIPO_CHOICES, db_index=True)
    nome = models.CharField(max_length=80, blank=True, default="")
    codici = models.JSONField(
        default=list,
        help_text="Lista ordinata di codici 3-char. Es. ['A12','B34','C56'].",
    )
    attiva = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Sequenza di volo"
        verbose_name_plural = "Sequenze di volo"
        ordering = ["tipo", "-created_at"]

    def save(self, *args, **kwargs):
        if isinstance(self.codici, list):
            self.codici = [str(c).upper() for c in self.codici if c]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_tipo_display()} ({len(self.codici or [])} step)"


class StatoAllertaPilot(SyncableModel, models.Model):
    """
    Livello DEFCON 0..6: nome, colore UI, frequenza spawn eventi e tempo risoluzione.
    Esattamente un livello deve avere `equivale_nave_abbattuta` (tipicamente 6).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    livello = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(0), MaxValueValidator(6)],
        help_text="Allineato al DEFCON runtime (0..5 in volo; 6 = oltre soglia / precipizio).",
    )
    nome = models.CharField(max_length=80)
    colore = models.CharField(
        max_length=7,
        default="#888888",
        help_text="Colore CSS (#RRGGBB) per la console.",
    )
    frequenza_evento_min_sec = models.PositiveIntegerField(
        default=60,
        help_text=(
            "Solo se probabilita_evento_per_tick=0: estremo inferiore (secondi) "
            "dell'intervallo casuale prima del prossimo evento."
        ),
    )
    frequenza_evento_max_sec = models.PositiveIntegerField(
        default=90,
        help_text=(
            "Solo se probabilita_evento_per_tick=0: estremo superiore (secondi) "
            "dell'intervallo casuale prima del prossimo evento."
        ),
    )
    tempo_risoluzione_secondi = models.PositiveIntegerField(
        default=20,
        help_text=(
            "Durata in secondi di ogni tick motore mentre c'e' un evento attivo "
            "(in viaggio regolare si usa tick_interval_secondi in Runtime Console). "
            "Durata totale evento in secondi = tick evento × questo valore."
        ),
    )
    probabilita_evento_per_tick = models.FloatField(
        default=0.15,
        help_text="Probabilita' 0..1 che a ogni tick venga generato un evento (se non ce n'e' uno attivo).",
    )
    equivale_nave_abbattuta = models.BooleanField(
        default=False,
        help_text="Se vero: questo livello descrive la nave precipitata (crash). Solo uno tra 0..6.",
    )

    class Meta:
        verbose_name = "Stato allerta console"
        verbose_name_plural = "Stati allerta console"
        ordering = ["livello"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.equivale_nave_abbattuta:
            StatoAllertaPilot.objects.exclude(pk=self.pk).update(
                equivale_nave_abbattuta=False
            )

    def __str__(self):
        return f"{self.livello} — {self.nome}"


class ComandoCriticoGlobale(SyncableModel, models.Model):
    """
    Pattern di codice 3-char che provocano precipitazione immediata se inseriti,
    indipendentemente dall'evento attivo. Stessa sintassi degli altri pattern
    (jolly _, XY(N-M), ecc.).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    pattern = models.CharField(
        max_length=48,
        help_text='Es. "XX9", "ML(4-9)", "_Z3"',
    )
    nome = models.CharField(max_length=120, blank=True, default="")
    attivo = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Comando critico globale"
        verbose_name_plural = "Comandi critici globali"
        ordering = ["nome", "pattern"]

    def save(self, *args, **kwargs):
        if self.pattern:
            self.pattern = str(self.pattern).strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome or self.pattern


# ---------------------------------------------------------------------------
# Sessione di volo + runtime
# ---------------------------------------------------------------------------


SESSIONE_STATO_IDLE = "idle"
SESSIONE_STATO_DECOLLO = "decollo"
SESSIONE_STATO_VOLO = "volo"
SESSIONE_STATO_ATTERRAGGIO = "atterraggio"
SESSIONE_STATO_ARRIVATA = "arrivata"
SESSIONE_STATO_CRASHED = "crashed"
SESSIONE_STATO_CHOICES = [
    (SESSIONE_STATO_IDLE, "A terra"),
    (SESSIONE_STATO_DECOLLO, "Decollo in corso"),
    (SESSIONE_STATO_VOLO, "In volo"),
    (SESSIONE_STATO_ATTERRAGGIO, "Atterraggio in corso"),
    (SESSIONE_STATO_ARRIVATA, "Arrivata"),
    (SESSIONE_STATO_CRASHED, "Precipitata"),
]

DEFCON_MAX = 5


class SessioneVolo(SyncableModel, models.Model):
    """
    Sessione di volo del pilota.

    Stato runtime principale:
    - DEFCON: gravita' situazione (0..DEFCON_MAX). >DEFCON_MAX => crash.
    - durata_pianificata_secondi: durata viaggio calcolata a partenza.
    - decollo_idx/atterraggio_idx: avanzamento sequenze obbligatorie.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    pilota = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.PROTECT,
        related_name="sessioni_volo",
    )
    prefettura_partenza = models.ForeignKey(
        "personaggi.Prefettura",
        on_delete=models.PROTECT,
        related_name="voli_in_partenza",
        null=True,
        blank=True,
    )
    prefettura_arrivo = models.ForeignKey(
        "personaggi.Prefettura",
        on_delete=models.PROTECT,
        related_name="voli_in_arrivo",
        null=True,
        blank=True,
    )
    stato = models.CharField(
        max_length=16,
        choices=SESSIONE_STATO_CHOICES,
        default=SESSIONE_STATO_IDLE,
        db_index=True,
    )
    defcon = models.PositiveIntegerField(default=0)
    durata_pianificata_secondi = models.PositiveIntegerField(default=600)
    started_at = models.DateTimeField(null=True, blank=True)
    decollo_completato_at = models.DateTimeField(null=True, blank=True)
    atterraggio_iniziato_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    decollo_idx = models.PositiveIntegerField(default=0)
    atterraggio_idx = models.PositiveIntegerField(default=0)
    next_event_at = models.DateTimeField(null=True, blank=True)
    tick_secondi = models.PositiveIntegerField(default=5)
    carburante_massimo = models.FloatField(default=1000.0)
    carburante_attuale = models.FloatField(default=1000.0)
    storage_energia_massimo = models.FloatField(default=0.0)
    storage_energia_attuale = models.FloatField(default=0.0)
    coeff_rigenerazione_carburante_riposo = models.FloatField(default=1.0)
    produzione_ultimo_tick = models.FloatField(default=0.0)
    consumo_ultimo_tick = models.FloatField(default=0.0)
    distanza_target = models.FloatField(default=1000.0)
    distanza_percorsa = models.FloatField(default=0.0)
    crash_reason = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Motivo tecnico della precipitazione (es. defcon_overflow, end_of_energy, manual_abort).",
    )
    ultimo_tick_motore_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp dell'ultimo tick motore applicato (throttle poll API / worker).",
    )

    class Meta:
        verbose_name = "Sessione di volo"
        verbose_name_plural = "Sessioni di volo"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pilota", "stato"]),
            models.Index(fields=["stato", "next_event_at"]),
        ]

    def __str__(self):
        return f"Volo {self.id} [{self.stato} D{self.defcon}]"

    @property
    def is_attiva(self) -> bool:
        return self.stato == SESSIONE_STATO_VOLO

    @property
    def is_terminata(self) -> bool:
        return self.stato in (SESSIONE_STATO_ARRIVATA, SESSIONE_STATO_CRASHED)


EVENTO_ESITO_PENDING = "pending"
EVENTO_ESITO_RISOLTO = "risolto"
EVENTO_ESITO_PARZIALE = "parziale"
EVENTO_ESITO_FALLITO = "fallito"
EVENTO_ESITO_TIMEOUT = "timeout"
EVENTO_ESITO_PRECIPITAZIO = "precipizio"
EVENTO_ESITO_GUASTO_CA = "guasto_ca"
EVENTO_ESITO_CHOICES = [
    (EVENTO_ESITO_PENDING, "In attesa"),
    (EVENTO_ESITO_RISOLTO, "Risolto"),
    (EVENTO_ESITO_PARZIALE, "Parziale"),
    (EVENTO_ESITO_FALLITO, "Fallito"),
    (EVENTO_ESITO_TIMEOUT, "Timeout"),
    (EVENTO_ESITO_PRECIPITAZIO, "Precipizio"),
    (EVENTO_ESITO_GUASTO_CA, "CA: guasto sottosistema"),
]


class EventoAttivoSessione(SyncableModel, models.Model):
    """
    Istanza runtime di un evento generato durante una sessione.

    Solo un evento puo' essere `pending` per sessione alla volta.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sessione = models.ForeignKey(
        SessioneVolo, on_delete=models.CASCADE, related_name="eventi_attivi"
    )
    evento = models.ForeignKey(
        EventoNave, on_delete=models.PROTECT, related_name="istanze"
    )
    deadline_at = models.DateTimeField()
    ticks_rimanenti = models.IntegerField(
        null=True,
        blank=True,
        help_text="Tick rimanenti dell'evento; null = durata infinita.",
    )
    persiste_fino_st = models.BooleanField(default=False)
    precipita_a_scadenza = models.BooleanField(default=False)
    esito = models.CharField(
        max_length=16,
        choices=EVENTO_ESITO_CHOICES,
        default=EVENTO_ESITO_PENDING,
        db_index=True,
    )
    risolto_at = models.DateTimeField(null=True, blank=True)
    codice_inserito = models.CharField(max_length=8, blank=True, default="")
    direzione_evento = models.CharField(
        max_length=16,
        blank=True,
        default="",
        choices=[
            ("", "Nessuna"),
            ("avanti", "Avanti"),
            ("indietro", "Indietro"),
            ("su", "Su"),
            ("giu", "Giu"),
            ("destra", "Destra"),
            ("sinistra", "Sinistra"),
        ],
    )
    prossima_valutazione_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Prossimo check CA/ST/SP programmato (dopo il primo intervallo di reazione, "
            "usa intervallo DEFCON corrente)."
        ),
    )
    reazione_fino_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Fine del tempo di reazione pilota: congelato alla comparsa dell'evento "
            "(DEFCON al momento dello spawn). Nessuna valutazione CA/ST/SP prima di questo istante."
        ),
    )
    intervallo_reazione_secondi = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Secondi di reazione fissati alla comparsa (tempo_risoluzione DEFCON allo spawn).",
    )
    valutazioni_eseguite = models.PositiveSmallIntegerField(
        default=0,
        help_text=(
            "Numero di tick evento gia' valutati. La CA e la scadenza critica precipizio "
            "non si applicano al primo check (tempo di reazione pilota)."
        ),
    )

    class Meta:
        verbose_name = "Evento attivo"
        verbose_name_plural = "Eventi attivi"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sessione", "esito"]),
            models.Index(fields=["esito", "deadline_at"]),
        ]


class TentativoCodice(SyncableModel, models.Model):
    """
    Storico ogni input a 3 caratteri durante una sessione.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sessione = models.ForeignKey(
        SessioneVolo, on_delete=models.CASCADE, related_name="tentativi"
    )
    evento_attivo = models.ForeignKey(
        EventoAttivoSessione,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tentativi",
    )
    codice = models.CharField(max_length=8)
    esito = models.CharField(max_length=24)
    defcon_pre = models.IntegerField(default=0)
    defcon_post = models.IntegerField(default=0)
    note = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Tentativo codice"
        verbose_name_plural = "Tentativi codice"
        ordering = ["-created_at"]


class VoceDiarioVolo(SyncableModel, models.Model):
    """
    Cronologia leggibile di una sessione di volo (eventi, DEFCON, precipizi).
    Append-only: per analisi post-partita da parte del pilota.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sessione = models.ForeignKey(
        SessioneVolo, on_delete=models.CASCADE, related_name="diario_voci"
    )
    categoria = models.CharField(max_length=32, db_index=True)
    messaggio = models.TextField()
    defcon_pre = models.SmallIntegerField(null=True, blank=True)
    defcon_post = models.SmallIntegerField(null=True, blank=True)
    evento_attivo = models.ForeignKey(
        EventoAttivoSessione,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voci_diario",
    )
    dati_json = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Voce diario volo"
        verbose_name_plural = "Voci diario volo"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["sessione", "created_at"]),
            models.Index(fields=["sessione", "categoria"]),
        ]

    def __str__(self):
        return f"{self.categoria}: {self.messaggio[:60]}"


class StatoSottosistemaSessione(SyncableModel, models.Model):
    """
    Stato runtime di un sottosistema in una specifica sessione.

    online=False  : sottosistema guasto (i codici col primo carattere relativo
                    falliscono sempre).
    recovery_at != None: ripristino in corso, online torna True dopo recovery_at.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sessione = models.ForeignKey(
        SessioneVolo, on_delete=models.CASCADE, related_name="stati_sottosistemi"
    )
    sottosistema = models.ForeignKey(
        SottosistemaNave, on_delete=models.PROTECT, related_name="stati_runtime"
    )
    online = models.BooleanField(default=True)
    guasto_at = models.DateTimeField(null=True, blank=True)
    recovery_at = models.DateTimeField(null=True, blank=True)
    livello_target = models.PositiveSmallIntegerField(default=0)
    livello_attuale = models.PositiveSmallIntegerField(default=0)
    invertito = models.BooleanField(default=False)
    espulso = models.BooleanField(default=False)
    direzione = models.CharField(
        max_length=16,
        default="avanti",
        choices=[
            ("avanti", "Avanti"),
            ("indietro", "Indietro"),
            ("su", "Su"),
            ("giu", "Giu"),
            ("destra", "Destra"),
            ("sinistra", "Sinistra"),
        ],
    )

    class Meta:
        verbose_name = "Stato sottosistema in sessione"
        verbose_name_plural = "Stati sottosistemi in sessione"
        unique_together = [("sessione", "sottosistema")]
        indexes = [
            models.Index(fields=["sessione", "online"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from pilotaggio.stato_nave import sync_stato_sessione_a_nave

        sync_stato_sessione_a_nave(self)


class StatoSottosistemaNave(SyncableModel, models.Model):
    """
    Stato persistente del sottosistema sulla nave (sopravvive a fine volo / nuova sessione idle).

    Fonte di verità per guasti, espulsioni e livelli tra una sessione e l'altra.
    La sessione runtime (idle o volo) viene allineata a questo record.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sottosistema = models.OneToOneField(
        SottosistemaNave,
        on_delete=models.PROTECT,
        related_name="stato_nave",
    )
    online = models.BooleanField(default=True)
    guasto_at = models.DateTimeField(null=True, blank=True)
    recovery_at = models.DateTimeField(null=True, blank=True)
    livello_target = models.PositiveSmallIntegerField(default=0)
    livello_attuale = models.PositiveSmallIntegerField(default=0)
    invertito = models.BooleanField(default=False)
    espulso = models.BooleanField(default=False)
    direzione = models.CharField(
        max_length=16,
        default="avanti",
        choices=[
            ("avanti", "Avanti"),
            ("indietro", "Indietro"),
            ("su", "Su"),
            ("giu", "Giu"),
            ("destra", "Destra"),
            ("sinistra", "Sinistra"),
        ],
    )

    class Meta:
        verbose_name = "Stato sottosistema nave (persistente)"
        verbose_name_plural = "Stati sottosistemi nave (persistenti)"
        indexes = [
            models.Index(fields=["online"]),
            models.Index(fields=["espulso"]),
        ]

    def __str__(self):
        return f"Nave {self.sottosistema_id} online={self.online}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from pilotaggio.stato_nave import sync_nave_a_sessione_corrente

        sync_nave_a_sessione_corrente(self)


# ---------------------------------------------------------------------------
# Token sessione console (login QR pilota)
# ---------------------------------------------------------------------------


class PilotConsoleToken(SyncableModel, models.Model):
    """
    Token rilasciato alla console pilota dopo login QR (separato dal token DRF).

    Permette al frontend pilota di autenticarsi senza esporre lo stesso token
    dell'app principale del giocatore. Il token viene revocato al termine della
    sessione di volo o esplicitamente.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    pilota = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.CASCADE,
        related_name="console_tokens",
    )
    revocato_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Token console pilota"
        verbose_name_plural = "Token console pilota"
        ordering = ["-created_at"]

    @classmethod
    def genera_token(cls) -> str:
        import secrets

        return secrets.token_urlsafe(32)

    @property
    def attivo(self) -> bool:
        return self.revocato_at is None


class PilotConsoleLoginTicket(SyncableModel, models.Model):
    """
    Ticket temporaneo per login inverso:
    - la console crea il ticket e mostra il QR con URL di claim;
    - il giocatore loggato nella web app apre il link e conferma il claim;
    - la console polla lo stato e riceve il PilotConsoleToken finale.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    codice = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    pilota = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="console_login_tickets",
    )
    token_console = models.CharField(max_length=64, blank=True, default="")
    token_issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ticket login console"
        verbose_name_plural = "Ticket login console"
        ordering = ["-created_at"]

    @classmethod
    def genera_codice(cls) -> str:
        import secrets

        return secrets.token_urlsafe(24)

    @property
    def scaduto(self) -> bool:
        return timezone.now() >= self.expires_at


class CoppiaColoriComponente(SyncableModel, models.Model):
    """Coppia di colori (caratteristiche) opposti nella stiva componenti nave."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    colore_a = models.ForeignKey(
        "personaggi.Punteggio",
        on_delete=models.PROTECT,
        related_name="coppie_componenti_a",
        limit_choices_to={"tipo": "CA"},
    )
    colore_b = models.ForeignKey(
        "personaggi.Punteggio",
        on_delete=models.PROTECT,
        related_name="coppie_componenti_b",
        limit_choices_to={"tipo": "CA"},
    )
    ordine = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Coppia colori componente"
        verbose_name_plural = "Coppie colori componente"
        ordering = ["ordine", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["colore_a", "colore_b"],
                name="uniq_coppia_colori_componente",
            ),
        ]

    def __str__(self):
        return f"{self.colore_a} ↔ {self.colore_b}"


class StivaComponenteNave(SyncableModel, models.Model):
    """Inventario globale componenti nave (per mattone-componente aura dedicata)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    mattone = models.OneToOneField(
        "personaggi.Mattone",
        on_delete=models.CASCADE,
        related_name="stiva_nave",
    )
    quantita = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Stiva componente nave"
        verbose_name_plural = "Stiva componenti nave"
        ordering = ["mattone__indice_componente", "mattone__ordine"]

    def __str__(self):
        return f"{self.mattone} × {self.quantita}"


class StivaCoppiaOppositiStato(SyncableModel, models.Model):
    """Contatore tick di coesistenza per coppia opposta in stiva."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    coppia = models.OneToOneField(
        CoppiaColoriComponente,
        on_delete=models.CASCADE,
        related_name="stato_coesistenza",
    )
    tick_coesistenza = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Stato coesistenza opposti"
        verbose_name_plural = "Stati coesistenza opposti"

    def __str__(self):
        return f"{self.coppia} tick={self.tick_coesistenza}"


class PilotRuntimeConfig(models.Model):
    """
    Config runtime singleton per worker tick.
    """

    singleton_id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    tick_enabled = models.BooleanField(default=False)
    tick_interval_secondi = models.FloatField(default=5.0)
    tick_last_heartbeat = models.DateTimeField(null=True, blank=True)
    stiva_ultimo_tick_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultimo tick annichilamento opposti stiva (idempotenza tra sessioni).",
    )
    login_required_console = models.BooleanField(
        default=False,
        help_text="Se attivo, la console richiede login ticket/QR. Default disattivo (utile in dev).",
    )
    alarm_audio_enabled = models.BooleanField(
        default=False,
        help_text="Abilita beep allarme lato console quando ci sono sottosistemi critici con tick attivo.",
    )
    riparazione_componenti_abilitata = models.BooleanField(
        default=False,
        help_text="Abilita consumo componenti da stiva nelle riparazioni QR (se richiesto dal sottosistema).",
    )
    annichilamento_opposti_abilitato = models.BooleanField(
        default=True,
        help_text="Annichilamento colori opposti in stiva dopo 5 tick di coesistenza.",
    )
    compattatore_console_abilitata = models.BooleanField(
        default=False,
        help_text="Abilita console /pilot/?screen=compattatore.",
    )
    compattatore_login_richiesto = models.BooleanField(
        default=True,
        help_text="Richiede login alla console compattatore.",
    )
    compattatore_stat_accesso_sigla = models.CharField(
        max_length=3,
        default="0IN",
        help_text="Sigla statistica per accesso console compattatore (es. 0IN>0).",
    )
    compattatore_quantico_abilitato = models.BooleanField(
        default=False,
        help_text="Abilita operazione Compattatore Quantico in console (default disattivo fino a evento).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Runtime pilotaggio"
        verbose_name_plural = "Runtime pilotaggio"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(singleton_id=1)
        return obj


class CompattatoreStatoNave(SyncableModel, models.Model):
    """Energia accumulata compattatore (singleton nave)."""

    singleton_id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    energia_accumulata = models.FloatField(
        default=0.0,
        help_text="Energia accumulata; un'operazione consuma 9 unità.",
    )

    class Meta:
        verbose_name = "Stato compattatore nave"
        verbose_name_plural = "Stato compattatore nave"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(singleton_id=1)
        return obj
