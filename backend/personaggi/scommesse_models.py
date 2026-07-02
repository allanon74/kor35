"""
Modelli per il sistema scommesse in-game.
"""
import uuid
from datetime import time
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from kor35.syncing import SyncableModel

from personaggi.scommesse_config import DEFAULT_SCOMMESSE_CONFIG, get_config_scommesse
from personaggi.scommesse_risultati import TIPO_CALCIO, TIPO_RISULTATO_CHOICES, pareggio_consentito
from personaggi.scommesse_logic import (
    ALLIBRATORE_SIGLA,
    ESITI_VALIDI,
    STRATEGIA_ACCOPPIAMENTO_CHOICES,
    STRATEGIA_ACCOPPIAMENTO_RANDOM,
    STRATEGIA_ACCOPPIAMENTO_ROUND_ROBIN,
    accoppia_squadre_random,
    accoppia_squadre_round_robin,
    calcola_quote,
    genera_codice_scommessa,
    genera_esito_incontro,
    risultati_pubblicati,
)


def get_default_campagna_id():
    from personaggi.models import get_default_campagna_id as _fn
    return _fn()


class SportScommesse(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(blank=True, default="")
    campagna = models.ForeignKey(
        "Campagna",
        on_delete=models.PROTECT,
        related_name="sport_scommesse",
        default=get_default_campagna_id,
        db_index=True,
    )
    attivo = models.BooleanField(default=True)
    tipo_risultato = models.CharField(
        max_length=20,
        choices=TIPO_RISULTATO_CHOICES,
        default=TIPO_CALCIO,
        help_text="Formato punteggio e regole pareggio per questo sport.",
    )

    class Meta:
        verbose_name = "Sport scommesse"
        verbose_name_plural = "Sport scommesse"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class SquadraScommesse(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sport = models.ForeignKey(
        SportScommesse,
        on_delete=models.CASCADE,
        related_name="squadre",
    )
    nome = models.CharField(max_length=120)
    potenza = models.PositiveIntegerField(default=50, help_text="Potenza numerica della squadra (1-999)")
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Squadra scommesse"
        verbose_name_plural = "Squadre scommesse"
        ordering = ["sport__nome", "nome"]
        unique_together = [("sport", "nome")]

    def __str__(self):
        return f"{self.nome} ({self.sport.nome})"


class ProgrammazioneTorneoScommesse(SyncableModel, models.Model):
    """
    Configurazione cadenzata (es. ogni 14 giorni) per giornate torneo tra un evento LARP e il successivo.
    Le giornate legate a un evento in loco si creano manualmente dallo staff.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sport = models.OneToOneField(
        SportScommesse,
        on_delete=models.CASCADE,
        related_name="programmazione",
    )
    attiva = models.BooleanField(
        default=False,
        help_text="Se attiva, la sincronizzazione può creare nuove giornate.",
    )
    auto_genera = models.BooleanField(
        default=True,
        help_text="Crea automaticamente calendari sulla cadenza temporale (cron/sync).",
    )
    intervallo_giorni = models.PositiveSmallIntegerField(
        default=14,
        help_text="Giorni tra una giornata automatica e la successiva (default 14).",
    )
    sfasamento_giorni = models.PositiveSmallIntegerField(
        default=0,
        help_text="Ritardo in giorni rispetto all'ancora per sfalsare gli sport tra loro.",
    )
    giorni_apertura = models.PositiveSmallIntegerField(
        default=12,
        help_text="Giorni di apertura scommesse prima della pubblicazione risultati.",
    )
    ora_risoluzione = models.TimeField(
        default=time(18, 0),
        help_text="Ora locale di pubblicazione risultati per le giornate a cadenza.",
    )
    data_ancora_cadenza = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Prima data di riferimento del ciclo (opzionale; default creazione programmazione).",
    )
    strategia_accoppiamento = models.CharField(
        max_length=16,
        choices=STRATEGIA_ACCOPPIAMENTO_CHOICES,
        default=STRATEGIA_ACCOPPIAMENTO_ROUND_ROBIN,
    )
    ore_apertura_prima_evento = models.PositiveIntegerField(
        default=336,
        help_text="Ore prima dell'inizio evento in cui aprono le scommesse (default 14 giorni).",
    )
    ore_chiusura_prima_evento = models.PositiveIntegerField(
        default=2,
        help_text="Ore prima dell'inizio evento in cui si pubblicano i risultati (default 2h).",
    )
    giornata_corrente = models.PositiveSmallIntegerField(
        default=0,
        help_text="Contatore giornate già generate (usato per il girone).",
    )
    ultimo_evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programmazioni_scommesse_ultimo",
    )

    class Meta:
        verbose_name = "Programmazione torneo scommesse"
        verbose_name_plural = "Programmazioni torneo scommesse"

    def __str__(self):
        stato = "attiva" if self.attiva else "spenta"
        return f"Programmazione {self.sport.nome} ({stato})"


class CalendarioScommesse(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sport = models.ForeignKey(
        SportScommesse,
        on_delete=models.CASCADE,
        related_name="calendari",
    )
    titolo = models.CharField(max_length=160, blank=True, default="")
    data_apertura = models.DateTimeField(default=timezone.now)
    data_risoluzione = models.DateTimeField(
        help_text="Data/ora in cui i risultati diventano visibili ai giocatori.",
    )
    importo_max_senza_codice = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=DEFAULT_SCOMMESSE_CONFIG.importo_max_senza_codice_default,
    )
    attivo = models.BooleanField(default=True)
    liquidato = models.BooleanField(default=False)
    evento = models.ForeignKey(
        "gestione_plot.Evento",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendari_scommesse",
        help_text="Evento LARP a cui è collegata questa giornata (se generata da programmazione).",
    )
    giornata_numero = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Numero giornata nel torneo (1, 2, 3…).",
    )
    programmazione = models.ForeignKey(
        ProgrammazioneTorneoScommesse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendari_generati",
    )

    class Meta:
        verbose_name = "Calendario scommesse"
        verbose_name_plural = "Calendari scommesse"
        ordering = ["-data_risoluzione"]
        constraints = [
            models.UniqueConstraint(
                fields=["sport", "evento"],
                condition=models.Q(evento__isnull=False),
                name="uniq_calendario_sport_evento",
            ),
        ]

    def __str__(self):
        label = self.titolo or f"Calendario {self.sport.nome}"
        return label

    @property
    def risultati_visibili(self):
        return risultati_pubblicati(self.data_risoluzione)

    def genera_incontri(self, strategia=None, giornata_index=None):
        """Genera accoppiamenti e calcola quote/risultati (nascosti fino a data_risoluzione)."""
        squadre = list(
            self.sport.squadre.filter(attiva=True).order_by("nome")
        )
        if len(squadre) < 2:
            raise ValidationError("Servono almeno 2 squadre attive per generare un calendario.")

        if strategia is None and self.programmazione_id:
            strategia = self.programmazione.strategia_accoppiamento
        if strategia is None:
            strategia = STRATEGIA_ACCOPPIAMENTO_RANDOM
        if giornata_index is None and self.giornata_numero is not None:
            giornata_index = max(0, int(self.giornata_numero) - 1)
        elif giornata_index is None:
            giornata_index = 0

        seed_base = str(self.sync_id)
        if strategia == STRATEGIA_ACCOPPIAMENTO_ROUND_ROBIN:
            coppie = accoppia_squadre_round_robin(squadre, giornata_index, seed_base)
        else:
            coppie = accoppia_squadre_random(squadre, seed_base)
        self.incontri.all().delete()
        cfg = get_config_scommesse(self.sport.campagna_id)
        allow_draw = pareggio_consentito(self.sport.tipo_risultato)

        for idx, (casa, trasferta) in enumerate(coppie):
            seed_incontro = f"{seed_base}:{idx}:{casa.sync_id}:{trasferta.sync_id}"
            quote = calcola_quote(
                casa.potenza,
                trasferta.potenza,
                seed_incontro,
                margine=cfg.margine_book_default,
                variabilita_pct=cfg.variabilita_potenza_pct,
                allow_draw=allow_draw,
            )
            risultato = genera_esito_incontro(
                quote["potenza_casa_effettiva"],
                quote["potenza_trasferta_effettiva"],
                seed_incontro,
                tipo_risultato=self.sport.tipo_risultato,
            )
            IncontroScommesse.objects.create(
                calendario=self,
                squadra_casa=casa,
                squadra_trasferta=trasferta,
                ordine=idx,
                potenza_casa_effettiva=quote["potenza_casa_effettiva"],
                potenza_trasferta_effettiva=quote["potenza_trasferta_effettiva"],
                quota_casa=quote["quota_casa"],
                quota_pareggio=quote["quota_pareggio"],
                quota_trasferta=quote["quota_trasferta"],
                esito=risultato["esito"],
                gol_casa=risultato["gol_casa"],
                gol_trasferta=risultato["gol_trasferta"],
            )


class IncontroScommesse(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    calendario = models.ForeignKey(
        CalendarioScommesse,
        on_delete=models.CASCADE,
        related_name="incontri",
    )
    squadra_casa = models.ForeignKey(
        SquadraScommesse,
        on_delete=models.PROTECT,
        related_name="incontri_casa",
    )
    squadra_trasferta = models.ForeignKey(
        SquadraScommesse,
        on_delete=models.PROTECT,
        related_name="incontri_trasferta",
    )
    ordine = models.PositiveSmallIntegerField(default=0)
    potenza_casa_effettiva = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    potenza_trasferta_effettiva = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    quota_casa = models.DecimalField(max_digits=8, decimal_places=2)
    quota_pareggio = models.DecimalField(max_digits=8, decimal_places=2)
    quota_trasferta = models.DecimalField(max_digits=8, decimal_places=2)
    esito = models.CharField(max_length=1, choices=[(e, e) for e in sorted(ESITI_VALIDI)])
    gol_casa = models.PositiveSmallIntegerField(default=0)
    gol_trasferta = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Incontro scommesse"
        verbose_name_plural = "Incontri scommesse"
        ordering = ["calendario", "ordine"]

    def __str__(self):
        return f"{self.squadra_casa.nome} vs {self.squadra_trasferta.nome}"

    def quota_per_esito(self, esito: str) -> Decimal:
        if esito == "1":
            return self.quota_casa
        if esito == "X":
            return self.quota_pareggio
        return self.quota_trasferta


class CodiceScommessa(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    codice = models.CharField(max_length=5, unique=True, db_index=True)
    allibratore = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="codici_scommessa_generati",
    )
    usato = models.BooleanField(default=False)
    usato_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Codice scommessa"
        verbose_name_plural = "Codici scommessa"
        ordering = ["-created_at"]

    def __str__(self):
        stato = "usato" if self.usato else "disponibile"
        return f"{self.codice} ({stato})"

    @classmethod
    def crea_per_allibratore(cls, personaggio):
        valore_all = personaggio.get_valore_statistica(ALLIBRATORE_SIGLA)
        if valore_all <= 0:
            raise ValidationError("Il personaggio non ha la statistica Allibratore (ALL > 0).")
        for _ in range(20):
            codice = genera_codice_scommessa()
            if not cls.objects.filter(codice=codice).exists():
                return cls.objects.create(allibratore=personaggio, codice=codice)
        raise ValidationError("Impossibile generare un codice univoco, riprova.")


class PuntataScommessa(SyncableModel, models.Model):
    STATO_PENDING = "PENDING"
    STATO_WON = "WON"
    STATO_LOST = "LOST"
    STATO_CHOICES = [
        (STATO_PENDING, "In attesa"),
        (STATO_WON, "Vinta"),
        (STATO_LOST, "Persa"),
    ]
    TIPO_SINGOLA = "SINGOLA"
    TIPO_COMBINATA = "COMBINATA"
    TIPO_CHOICES = [
        (TIPO_SINGOLA, "Singola"),
        (TIPO_COMBINATA, "Combinata"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.CASCADE,
        related_name="puntate_scommesse",
    )
    calendario = models.ForeignKey(
        CalendarioScommesse,
        on_delete=models.PROTECT,
        related_name="puntate",
    )
    codice = models.ForeignKey(
        CodiceScommessa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntate",
    )
    importo = models.DecimalField(max_digits=12, decimal_places=2)
    importo_riserva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Quota puntata pagata dalla riserva scommesse.",
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default=TIPO_SINGOLA)
    quota_totale = models.DecimalField(max_digits=12, decimal_places=2)
    stato = models.CharField(max_length=10, choices=STATO_CHOICES, default=STATO_PENDING)
    vincita = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    liquidata_at = models.DateTimeField(null=True, blank=True)
    vincita_riscossa = models.BooleanField(
        default=False,
        help_text="True se il giocatore ha già incassato la vincita (riscossione manuale).",
    )
    riscossa_at = models.DateTimeField(null=True, blank=True)
    vincita_ritirata = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="CR prelevati dalla riserva e accreditati in contanti (solo in evento attivo).",
    )
    vincita_versata_riserva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="CR versati in riserva alla riscossione della vincita.",
    )

    class Meta:
        verbose_name = "Puntata scommessa"
        verbose_name_plural = "Puntate scommesse"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.personaggio.nome} — {self.importo} CR ({self.stato})"


class SelezionePuntata(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    puntata = models.ForeignKey(
        PuntataScommessa,
        on_delete=models.CASCADE,
        related_name="selezioni",
    )
    incontro = models.ForeignKey(
        IncontroScommesse,
        on_delete=models.PROTECT,
        related_name="selezioni_puntate",
    )
    esito_scelto = models.CharField(max_length=1, choices=[(e, e) for e in sorted(ESITI_VALIDI)])

    class Meta:
        verbose_name = "Selezione puntata"
        verbose_name_plural = "Selezioni puntata"
        unique_together = [("puntata", "incontro")]

    def __str__(self):
        return f"{self.incontro} → {self.esito_scelto}"


class ConfigurazioneScommesse(SyncableModel, models.Model):
    """
    Parametri globali del sistema scommesse per campagna (modificabili dallo staff).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    campagna = models.OneToOneField(
        "Campagna",
        on_delete=models.CASCADE,
        related_name="configurazione_scommesse",
        default=get_default_campagna_id,
    )
    importo_max_senza_codice_default = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=DEFAULT_SCOMMESSE_CONFIG.importo_max_senza_codice_default,
        help_text="Importo massimo (CR) per scommessa senza codice allibratore (default nuovi calendari).",
    )
    scadenza_calendario_ore = models.PositiveSmallIntegerField(
        default=DEFAULT_SCOMMESSE_CONFIG.scadenza_calendario_ore,
        help_text="Ore di visibilità del calendario dopo la pubblicazione risultati.",
    )
    commissione_allibratore_pct = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=DEFAULT_SCOMMESSE_CONFIG.commissione_allibratore_pct,
        help_text="Frazione della vincita (es. 0.08 = 8%) accreditata all'allibratore se la puntata vince.",
    )
    bonus_quota_allibratore_pct = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=DEFAULT_SCOMMESSE_CONFIG.bonus_quota_allibratore_pct,
        help_text="Bonus quota con codice allibratore (es. 0.10 = +10% sulla quota).",
    )
    margine_book_default = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=DEFAULT_SCOMMESSE_CONFIG.margine_book_default,
        help_text="Margine del bookmaker sulle quote standard (>1 = house edge).",
    )
    margine_book_min = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=DEFAULT_SCOMMESSE_CONFIG.margine_book_min,
        help_text="Margine minimo con codice allibratore (ALL alto).",
    )
    riduzione_margine_per_punto_all = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=DEFAULT_SCOMMESSE_CONFIG.riduzione_margine_per_punto_all,
        help_text="Riduzione margine per ogni punto della statistica ALL.",
    )
    variabilita_potenza_pct = models.PositiveSmallIntegerField(
        default=DEFAULT_SCOMMESSE_CONFIG.variabilita_potenza_pct,
        help_text="Variabilità ±% applicata alla potenza squadre nel calcolo quote.",
    )
    max_selezioni_combinata = models.PositiveSmallIntegerField(
        default=DEFAULT_SCOMMESSE_CONFIG.max_selezioni_combinata,
        help_text="Massimo eventi in una scommessa combinata.",
    )
    potenza_delta_vittoria = models.PositiveSmallIntegerField(
        default=DEFAULT_SCOMMESSE_CONFIG.potenza_delta_vittoria,
        help_text="Incremento potenza squadra vincente dopo ogni incontro risolto.",
    )
    potenza_delta_sconfitta = models.PositiveSmallIntegerField(
        default=DEFAULT_SCOMMESSE_CONFIG.potenza_delta_sconfitta,
        help_text="Decremento potenza squadra perdente dopo ogni incontro risolto.",
    )
    soglia_vincita_rilevante = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=DEFAULT_SCOMMESSE_CONFIG.soglia_vincita_rilevante,
        help_text="Oltre questa soglia, per puntata si ritira al massimo questo importo in contanti (resto resta in riserva).",
    )
    max_ritiro_vincita_calendario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=DEFAULT_SCOMMESSE_CONFIG.max_ritiro_vincita_calendario,
        help_text="Massimo CR ritirabili in contanti per calendario/evento.",
    )
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configurazione scommesse"
        verbose_name_plural = "Configurazioni scommesse"

    def __str__(self):
        return f"Config scommesse — {self.campagna_id}"

