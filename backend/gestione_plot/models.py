import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from personaggi.models import Personaggio, Manifesto, Inventario, QrCode, Tier, Punteggio
from kor35.syncing import SyncableModel

# --- 1. SEZIONE TEMPLATE (L'ANAGRAFICA GENERALE) ---

class MostroTemplate(SyncableModel, models.Model):
    """
    Il record "Master". Definisce le statistiche base di una tipologia di creatura.
    Es: "Zombie", "Vampiro Antico", "Sgherro della Corporazione".
    """
    nome = models.CharField(max_length=100, unique=True)
    punti_vita_base = models.IntegerField(default=1)
    armatura_base = models.IntegerField(default=0)
    guscio_base = models.IntegerField(default=0)
    note_generali = models.TextField(blank=True, help_text="Descrizione fisica o comportamento standard")
    costume = models.TextField(blank=True, help_text="Tratti distintivi, maschere o indumenti necessari")

    class Meta:
        verbose_name = "Template Mostro"
        verbose_name_plural = "A. Template Mostri"

    def __str__(self):
        return self.nome

class AttaccoTemplate(SyncableModel, models.Model):
    """
    Gli attacchi associati a un Template.
    """
    template = models.ForeignKey(MostroTemplate, on_delete=models.CASCADE, related_name='attacchi')
    nome_attacco = models.CharField(max_length=100)
    descrizione_danno = models.CharField(max_length=200, help_text="Es: 3 Fisici, Atterramento...")
    ordine = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Attacco Template"
        verbose_name_plural = "B. Attacchi Template"
        ordering = ['ordine']


# --- 2. SEZIONE EVENTI E QUEST ---

class Evento(SyncableModel, models.Model):
    titolo = models.CharField(max_length=200)
    pc_guadagnati = models.PositiveIntegerField(
        default=1,
        verbose_name="PC guadagnati",
        help_text="PC assegnati una sola volta a ogni PG iscritto al primo accesso durante i giorni d'evento.",
    )
    crediti_guadagnati = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1000.00"),
        validators=[MinValueValidator(0)],
        verbose_name="Crediti guadagnati",
        help_text="Crediti assegnati una sola volta a ogni PG iscritto al primo accesso durante i giorni d'evento.",
    )
    crediti_base_inizio_evento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        verbose_name="Crediti base inizio evento",
        help_text="Quota fissa crediti assegnata a ogni PG partecipante all'avvio ufficiale evento.",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Evento iniziato il",
        help_text="Timestamp di avvio ufficiale evento (pulsante staff «Inizia evento»).",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Evento terminato il",
        help_text="Timestamp di chiusura ufficiale evento (pulsante staff «Termina evento»).",
    )
    data_inizio = models.DateTimeField()
    data_fine = models.DateTimeField()
    sinossi = models.TextField(blank=True)
    luogo = models.CharField(max_length=255, blank=True)
    
    partecipanti = models.ManyToManyField(
        Personaggio, 
        related_name='eventi_partecipati',
        blank=True,
        limit_choices_to={'tipologia__giocante': True}
    )
    staff_assegnato = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='eventi_gestiti',
        blank=True,
    )

    # Iscrizione giocatori (PayPal): entrambe le date valorizzate = finestra attiva
    iscrizione_apertura = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Iscrizione: apertura",
        help_text="Inizio finestra iscrizione (incluso). Lasciare vuoto per disattivare l'iscrizione online.",
    )
    iscrizione_chiusura = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Iscrizione: chiusura",
        help_text="Fine finestra iscrizione (incluso).",
    )
    iscrizione_costo_euro = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Costo iscrizione (EUR)",
        help_text="Importo addebitato via PayPal (es. 45.00). Deve essere > 0 per abilitare il pagamento.",
    )
    iscrizione_test_attiva = models.BooleanField(
        default=False,
        verbose_name="Test iscrizione (solo Master campagna principale)",
        help_text="Se attivo, l'evento compare solo a Master/Head Master della campagna principale (slug kor35) per provare PayPal in sandbox.",
    )

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "1. Eventi"

    def __str__(self):
        return self.titolo


class EventoIscrizioneOpzione(SyncableModel, models.Model):
    """
    Costo accessorio per l'iscrizione a un evento (pasto, pernottamento, ecc.).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="iscrizione_opzioni",
    )
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(blank=True)
    costo_euro = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Costo (EUR)",
    )
    ordine = models.PositiveIntegerField(default=0)
    scelta_giocatore = models.BooleanField(
        default=True,
        verbose_name="Scelta del giocatore",
        help_text="Se disattivo, l'opzione è inclusa automaticamente in ogni iscrizione.",
    )
    obbligatoria = models.BooleanField(
        default=False,
        verbose_name="Obbligatoria (se a scelta)",
        help_text="Con «scelta del giocatore» attivo: il giocatore deve selezionarla per iscriversi.",
    )
    posti_limite = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Posti disponibili",
        help_text="Vuoto = posti illimitati. I posti occupati includono ordini in attesa di pagamento.",
    )
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Opzione iscrizione evento"
        verbose_name_plural = "Opzioni iscrizione evento"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return f"{self.evento_id} — {self.nome}"


class EventoPremioPersonaggio(SyncableModel, models.Model):
    """
    Segna che PC e crediti d'evento sono stati accreditati una volta al PG iscritto
    (al primo accesso in sessione durante un giorno d'evento).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="premi_presenza")
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="premi_evento_presenza")

    class Meta:
        verbose_name = "Premio presenza evento (PG)"
        verbose_name_plural = "Premi presenza evento"
        constraints = [
            models.UniqueConstraint(
                fields=("evento", "personaggio"),
                name="uq_evento_premio_presenza_pg",
            ),
        ]

    def __str__(self):
        return f"{self.evento_id} → PG {self.personaggio_id}"


class GiornoEvento(SyncableModel, models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='giorni')
    titolo = models.CharField(max_length=200, blank=True, help_text="Titolo identificativo del giorno")
    descrizione_completa = models.TextField(blank=True, help_text="Dettagli completi del plot per questo giorno")
    data_ora_inizio = models.DateTimeField()
    data_ora_fine = models.DateTimeField()
    sinossi_breve = models.TextField()

    class Meta:
        verbose_name = "Giorno Evento"
        verbose_name_plural = "2. Giorni Evento"
        ordering = ['data_ora_inizio']
        
    def __str__(self):
        # Migliorato per mostrare il titolo se presente
        return self.titolo if self.titolo else f"Giorno del {self.data_ora_inizio.strftime('%d/%m/%Y')}"

class Quest(SyncableModel, models.Model):
    giorno = models.ForeignKey(GiornoEvento, on_delete=models.CASCADE, related_name='quests')
    titolo = models.CharField(max_length=200)
    orario_indicativo = models.TimeField()
    descrizione_ampia = models.TextField()
    props = models.TextField("Oggetti di scena / Props", blank=True, null=True)

    class Meta:
        verbose_name = "Quest"
        verbose_name_plural = "3. Quests"

    def __str__(self):
        return f"{self.orario_indicativo.strftime('%H:%M')} - {self.titolo}"


# --- 3. SEZIONE ISTANZE (I MOSTRI SUL CAMPO) ---

class QuestMostro(SyncableModel, models.Model):
    """
    L'istanza specifica di un mostro in una Quest. 
    Ereditato dal Template ma assegnabile a uno Staffer specifico.
    """
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='mostri_presenti')
    template = models.ForeignKey(MostroTemplate, on_delete=models.PROTECT, verbose_name="Tipo di Mostro")
    
    # Lo staffer che interpreta QUESTA istanza (es: Carlo fa lo zombi 1, Marco lo zombi 2)
    staffer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Interpretato da"
    )
    
    # Statistiche "copiate" o personalizzate per questa specifica istanza
    punti_vita = models.IntegerField(help_text="Copiati dal template, ma modificabili per questa istanza")
    armatura = models.IntegerField(default=0)
    guscio = models.IntegerField(default=0)
    
    note_per_staffer = models.TextField(blank=True, help_text="Note specifiche per chi interpreta il mostro")

    class Meta:
        verbose_name = "Mostro in Quest"
        verbose_name_plural = "4. Mostri in Quest"

    def __str__(self):
        return f"{self.template.nome} (Quest: {self.quest.titolo} - Staff: {self.staffer})"

    def save(self, *args, **kwargs):
        # Se è un nuovo inserimento, pre-popola le statistiche dal template
        if not self.pk and self.template:
            self.punti_vita = self.template.punti_vita_base
            self.armatura = self.template.armatura_base
            self.guscio = self.template.guscio_base
        super().save(*args, **kwargs)

class PngAssegnato(SyncableModel, models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='png_richiesti')
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, limit_choices_to={'tipologia__giocante': False})
    staffer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ordine_uscita = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "PnG Assegnato"
        verbose_name_plural = "5. PnG Assegnati"
        ordering = ['staffer', 'ordine_uscita']

class QuestVista(SyncableModel, models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='viste_previste')
    tipo = models.CharField(max_length=3, choices=[
        ('PG', 'Personaggio'),
        ('PNG', 'Personaggio Non Giocante'),
        ('INV', 'Inventario'),
        ('OGG', 'Oggetto'),
        ('TES', 'Tessitura'),
        ('INF', 'Infusione'),
        ('CER', 'Cerimoniale'),
        ('MAN', 'Manifesto')
    ])
    
    # Riferimenti a tutti i possibili tipi di a_vista (con related_name univoci)
    manifesto = models.ForeignKey(Manifesto, on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_manifesto')
    inventario = models.ForeignKey(Inventario, on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_inventario')
    personaggio = models.ForeignKey(Personaggio, on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_personaggio')
    oggetto = models.ForeignKey('personaggi.Oggetto', on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_oggetto')
    tessitura = models.ForeignKey('personaggi.Tessitura', on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_tessitura')
    infusione = models.ForeignKey('personaggi.Infusione', on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_infusione')
    cerimoniale = models.ForeignKey('personaggi.Cerimoniale', on_delete=models.SET_NULL, null=True, blank=True, related_name='questvista_cerimoniale')
    
    qr_code = models.OneToOneField(QrCode, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Oggetto Vista Quest"
        verbose_name_plural = "6. Oggetti Vista"
        
class StaffOffGame(SyncableModel, models.Model):
    """
    Staffer assegnati a compiti di arbitraggio o gestione Off-Game per una specifica Quest.
    """
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='staff_offgame')
    staffer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    compito = models.TextField(help_text="Es: Arbitro, Gestione Audio, Allestimento Zone...")

    class Meta:
        verbose_name = "Staff Off-Game"
        verbose_name_plural = "7. Staff Off-Game"
        unique_together = ('quest', 'staffer') # Evita duplicati dello stesso staffer nella stessa quest

    def __str__(self):
        return f"{self.staffer.username} - {self.compito} ({self.quest.titolo})"
    
class QuestFase(SyncableModel, models.Model):
    """
    Rappresenta un momento specifico della Quest (es. Fase 1: Infiltrazione, Fase 2: Scontro).
    """
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='fasi')
    ordine = models.PositiveIntegerField(default=1)
    titolo = models.CharField(max_length=100, help_text="Es: Scena del crimine, Assalto...")
    descrizione = models.TextField(blank=True, help_text="Cosa succede in questa fase")

    class Meta:
        ordering = ['ordine']
        verbose_name = "Fase Quest"
        verbose_name_plural = "3b. Fasi Quest"

    def __str__(self):
        return f"Fase {self.ordine}: {self.titolo} ({self.quest.titolo})"

class QuestTask(SyncableModel, models.Model):
    """
    Un compito specifico assegnato a un membro dello staff durante una fase.
    """
    RUOLO_CHOICES = [
        ('PNG', 'PnG'),
        ('MOSTRO', 'Mostro'),
        ('OFF', 'Staff Off-Game'),
    ]

    COMPITO_OFF_CHOICES = [
        ('REG', 'Regole'),
        ('AIU', 'Aiuto'),
        ('ALL', 'Allestimento'),
    ]

    fase = models.ForeignKey(QuestFase, on_delete=models.CASCADE, related_name='tasks')
    staffer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks_assegnati')
    
    ruolo = models.CharField(max_length=10, choices=RUOLO_CHOICES)
    
    # Campi condizionali
    personaggio = models.ForeignKey(Personaggio, on_delete=models.SET_NULL, null=True, blank=True, help_text="Se PnG")
    mostro_template = models.ForeignKey(MostroTemplate, on_delete=models.SET_NULL, null=True, blank=True, help_text="Se Mostro")
    compito_offgame = models.CharField(max_length=10, choices=COMPITO_OFF_CHOICES, null=True, blank=True, help_text="Se Staff Off-Game")
    
    # Statistiche runtime (solo se Mostro)
    punti_vita = models.IntegerField(default=1)
    armatura = models.IntegerField(default=0)
    guscio = models.IntegerField(default=0)
    
    istruzioni = models.TextField(blank=True, help_text="Istruzioni specifiche per lo staffer")

    class Meta:
        verbose_name = "Task Staff"
        verbose_name_plural = "3c. Task Staff"

    def save(self, *args, **kwargs):
        # Pre-popola statistiche se è un mostro e non sono impostate
        if self.ruolo == 'MOSTRO' and self.mostro_template and not self.pk:
            self.punti_vita = self.mostro_template.punti_vita_base
            self.armatura = self.mostro_template.armatura_base
            self.guscio = self.mostro_template.guscio_base
        super().save(*args, **kwargs)
        
# Sezione PAGINE WEB (CMS) del regolamento ed ambientazione

class PaginaRegolamento(SyncableModel, models.Model):
    titolo = models.CharField(max_length=200)
    slug = models.SlugField(unique=True) # Es: 'combattimento'
    
    # Per la nidificazione (Menu ad albero)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='sottopagine', on_delete=models.SET_NULL)
    ordine = models.PositiveIntegerField(default=0) # Per ordinare le voci nel menu
    
    # Contenuto
    contenuto = models.TextField(blank=True) # HTML salvato dall'editor
    
    # Immagine di copertina opzionale
    immagine = models.ImageField(upload_to='wiki_images/', null=True, blank=True)
    banner_y = models.IntegerField(default=50, verbose_name="Posizione Verticale Banner (%)")
    
    public = models.BooleanField(default=True) # Se false, è una bozza
    visibile_solo_staff = models.BooleanField(
        default=False, 
        verbose_name="Visibile solo allo Staff",
        help_text="Se attivo, la pagina sarà visibile solo a Staff e Superuser, anche se Pubblica è True."
    )

    includi_in_pdf = models.BooleanField(
        default=False,
        verbose_name="Includi nei manuali PDF",
        help_text="Se attivo, la pagina può comparire nei manuali PDF selezionati (solo contenuto pubblico).",
    )
    manuali_pdf = models.ManyToManyField(
        'ManualePdf',
        blank=True,
        related_name='pagine',
        verbose_name="Manuali PDF",
    )
    pdf_solo_indice = models.BooleanField(
        default=False,
        verbose_name="PDF: solo voce indice",
        help_text="Compare nell'indice ma senza corpo capitolo (utile per hub di navigazione).",
    )
    pdf_forza_nuova_pagina = models.BooleanField(
        default=False,
        verbose_name="PDF: forza nuova pagina",
        help_text="Inizia sempre su una pagina nuova nel PDF.",
    )
    pdf_titolo_capitolo = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="PDF: titolo capitolo",
        help_text="Titolo alternativo nel manuale; vuoto = titolo pagina.",
    )

    class Meta:
        ordering = ['ordine', 'titolo']

    def __str__(self):
        return f"{self.titolo} ({self.parent.titolo if self.parent else 'Root'})"


class ManualePdf(SyncableModel, models.Model):
    """Manuale PDF generato dalla wiki (uno o più volumi di regolamento)."""

    slug = models.SlugField(max_length=80, unique=True)
    titolo = models.CharField(max_length=200)
    sottotitolo = models.CharField(max_length=300, blank=True)
    ordine = models.PositiveIntegerField(default=0)
    attivo = models.BooleanField(
        default=True,
        help_text="Se disattivo, non compare nella homepage pubblica.",
    )
    copertina = models.ImageField(
        upload_to='wiki_manual_covers/',
        null=True,
        blank=True,
    )
    ultimo_generato_at = models.DateTimeField(null=True, blank=True)
    stile_preset = models.CharField(
        max_length=40,
        default="giocatore",
        verbose_name="Preset stile PDF",
        help_text="Preset di impaginazione; con «personalizzato» contano gli override in stile.",
    )
    stile = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Override stile PDF",
        help_text="Override JSON sul preset (font, margini, immagini, widget, indice, ecc.).",
    )

    class Meta:
        ordering = ['ordine', 'titolo']
        verbose_name = "Manuale PDF wiki"
        verbose_name_plural = "Manuali PDF wiki"

    def __str__(self):
        return self.titolo


class CreazioneGuidataFlusso(SyncableModel, models.Model):
    """Configurazione di un percorso guidato per la creazione personaggio."""

    slug = models.SlugField(max_length=80, unique=True)
    titolo = models.CharField(max_length=200)
    attivo = models.BooleanField(default=False)
    modalita_test = models.BooleanField(
        default=False,
        verbose_name='Modalità test (solo staff)',
        help_text='Se attivo, il flusso è visibile solo a staff Django, superuser e ruoli campagna Staffer/Master/Head Master.',
    )
    flusso_produzione = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='sandbox_test',
        help_text='Per flussi in modalità test: flusso di produzione su cui pubblicare le modifiche.',
    )
    campagna = models.ForeignKey(
        'personaggi.Campagna',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='flussi_creazione_guidata',
        help_text="Se vuoto, il flusso vale per tutte le campagne (priorità inferiore rispetto a flussi specifici).",
    )
    passo_iniziale = models.ForeignKey(
        'CreazioneGuidataPasso',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='flussi_come_iniziale',
    )

    class Meta:
        ordering = ['titolo']
        verbose_name = 'Flusso creazione guidata'
        verbose_name_plural = 'Flussi creazione guidata'
        constraints = [
            models.UniqueConstraint(
                fields=['flusso_produzione'],
                condition=models.Q(modalita_test=True, flusso_produzione__isnull=False),
                name='uniq_sandbox_test_per_produzione',
            ),
        ]

    def __str__(self):
        return self.titolo


class CreazioneGuidataPasso(SyncableModel, models.Model):
    """Pagina del wizard (contenuto tipo wiki)."""

    flusso = models.ForeignKey(
        CreazioneGuidataFlusso,
        on_delete=models.CASCADE,
        related_name='passi',
    )
    slug = models.SlugField(max_length=80)
    titolo = models.CharField(max_length=200)
    contenuto = models.TextField(blank=True, default='')
    immagine = models.ImageField(upload_to='creazione_guidata/', null=True, blank=True)
    ordine = models.PositiveIntegerField(default=0)
    opzioni_ui = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'presentazione: pulsanti|si_no|radio; '
            'gruppo_id; modalita_rewind: ramo|toggle; '
            'widget_fondo: {tipo: modello_aura, ...}'
        ),
    )

    class Meta:
        ordering = ['ordine', 'titolo']
        unique_together = [['flusso', 'slug']]
        verbose_name = 'Passo creazione guidata'
        verbose_name_plural = 'Passi creazione guidata'

    def __str__(self):
        return f"{self.titolo} ({self.flusso.slug}/{self.slug})"


class CreazioneGuidataScelta(SyncableModel, models.Model):
    """Scelta ramificata su un passo del wizard."""

    TIPO_NAVIGA = 'naviga'
    TIPO_IMPOSTA_CAMPO = 'imposta_campo'
    TIPO_AGGIUNGI_ABILITA = 'aggiungi_abilita'
    TIPO_COMBO = 'combo'
    TIPO_FINE = 'fine'
    TIPO_AZIONE_CHOICES = [
        (TIPO_NAVIGA, 'Naviga verso altro passo'),
        (TIPO_IMPOSTA_CAMPO, 'Imposta campo personaggio'),
        (TIPO_AGGIUNGI_ABILITA, 'Aggiungi abilità suggerite'),
        (TIPO_COMBO, 'Combinata (campo + abilità + navigazione da payload)'),
        (TIPO_FINE, 'Fine percorso'),
    ]

    passo = models.ForeignKey(
        CreazioneGuidataPasso,
        on_delete=models.CASCADE,
        related_name='scelte',
    )
    etichetta = models.CharField(max_length=200)
    descrizione = models.CharField(max_length=500, blank=True, default='')
    ordine = models.PositiveIntegerField(default=0)
    tipo_azione = models.CharField(max_length=32, choices=TIPO_AZIONE_CHOICES, default=TIPO_NAVIGA)
    passo_destinazione = models.ForeignKey(
        CreazioneGuidataPasso,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='scelte_in_entrata',
    )
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['ordine', 'etichetta']
        verbose_name = 'Scelta creazione guidata'
        verbose_name_plural = 'Scelte creazione guidata'

    def __str__(self):
        return f"{self.etichetta} ({self.tipo_azione})"


class WikiImmagine(SyncableModel, models.Model):
    """
    Modello per gestire immagini caricate nella wiki.
    Le immagini possono essere inserite come widget nel contenuto delle pagine.
    """
    titolo = models.CharField(max_length=200, help_text="Titolo descrittivo dell'immagine")
    descrizione = models.TextField(blank=True, help_text="Descrizione opzionale dell'immagine")
    immagine = models.ImageField(upload_to='wiki_images/widgets/', help_text="Immagine da caricare")
    
    # Metadati
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    creatore = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='immagini_wiki_create'
    )
    
    # Opzioni di visualizzazione
    larghezza_max = models.PositiveIntegerField(
        default=800,
        help_text="Larghezza massima in pixel (0 = dimensione originale)"
    )
    allineamento = models.CharField(
        max_length=10,
        choices=[
            ('left', 'Sinistra'),
            ('center', 'Centro'),
            ('right', 'Destra'),
            ('full', 'Larghezza piena'),
        ],
        default='center',
        help_text="Allineamento dell'immagine nel contenuto"
    )
    
    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Immagine Wiki"
        verbose_name_plural = "Immagini Wiki"

    def __str__(self):
        return f"{self.titolo} ({self.immagine.name if self.immagine else 'Nessuna immagine'})"


class WikiTierWidget(SyncableModel, models.Model):
    """
    Widget Tier configurabile per la wiki: associa un Tier con opzioni di visualizzazione
    (stile, collapsible, gradiente colori, ecc.). Usato in {{WIDGET_TIER:id}} dove id è questo widget.
    """
    tier = models.ForeignKey(Tier, on_delete=models.CASCADE, related_name='wiki_tier_widgets')
    abilities_collapsible = models.BooleanField(default=True)
    abilities_collapsed_by_default = models.BooleanField(default=False)
    abilities_solo_list = models.BooleanField(default=False)
    show_description = models.BooleanField(default=True)
    show_runtime_filters = models.BooleanField(default=False, help_text="Mostra filtri runtime sulle abilita del singolo Tier.")
    color_style = models.CharField(max_length=20, default='default')
    # Lista colori hex per gradiente (es. ["#1976D2", "#7B1FA2"]). Se vuota si usa color_style.
    gradient_colors = models.JSONField(default=list, blank=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    creatore = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wiki_tier_widgets_creati'
    )

    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Widget Tier"
        verbose_name_plural = "Widget Tier"

    def __str__(self):
        return f"Widget Tier #{self.id} ({self.tier.nome})"


class WikiTierCollectionWidget(SyncableModel, models.Model):
    """
    Widget che aggrega più Widget Tier con filtri e ordinamento.
    Usato in {{WIDGET_TIER_COLLECTION:id}} dove id è questo widget.
    """
    SOURCE_ALL = 'all'
    SOURCE_SELECTED = 'selected'
    SOURCE_CHOICES = [
        (SOURCE_ALL, 'Tutti i widget tier'),
        (SOURCE_SELECTED, 'Solo widget selezionati'),
    ]

    TIER_TYPE_ALL = 'all'
    TIER_TYPE_CHOICES = [
        (TIER_TYPE_ALL, 'Tutti i tipi'),
        ('G0', 'Tabelle Generali'),
        ('T1', 'Tier 1'),
        ('T2', 'Tier 2'),
        ('T3', 'Tier 3'),
        ('T4', 'Tier 4'),
    ]

    SORT_TIER_NAME = 'tier_name'
    SORT_WIDGET_CREATED = 'widget_created'
    SORT_CHOICES = [
        (SORT_TIER_NAME, 'Nome Tier'),
        (SORT_WIDGET_CREATED, 'Data creazione widget'),
    ]

    SORT_ASC = 'asc'
    SORT_DESC = 'desc'
    SORT_DIR_CHOICES = [
        (SORT_ASC, 'Crescente'),
        (SORT_DESC, 'Decrescente'),
    ]
    BADGE_COMPACT = 'compact'
    BADGE_EXTENDED = 'extended'
    BADGE_MODE_CHOICES = [
        (BADGE_COMPACT, 'Compatto (sigla)'),
        (BADGE_EXTENDED, 'Esteso (nome)'),
    ]

    CAR_FILTER_ANY = 'any'
    CAR_FILTER_ALL = 'all'
    CAR_FILTER_MODE_CHOICES = [
        (CAR_FILTER_ANY, 'Qualsiasi caratteristica selezionata'),
        (CAR_FILTER_ALL, 'Tutte le caratteristiche selezionate'),
    ]

    title = models.CharField(max_length=200, blank=True, help_text="Titolo opzionale del widget (per identificazione interna)")
    source_mode = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_ALL)
    tier_type_filter = models.CharField(max_length=8, choices=TIER_TYPE_CHOICES, default=TIER_TYPE_ALL)
    sort_by = models.CharField(max_length=32, choices=SORT_CHOICES, default=SORT_TIER_NAME)
    sort_dir = models.CharField(max_length=8, choices=SORT_DIR_CHOICES, default=SORT_ASC)
    caratteristiche_filter_mode = models.CharField(max_length=8, choices=CAR_FILTER_MODE_CHOICES, default=CAR_FILTER_ANY)
    show_runtime_filters = models.BooleanField(default=True, help_text="Mostra ricerca/filtro/ordinamento direttamente nel widget.")
    show_search_control = models.BooleanField(default=True, help_text="Mostra il campo ricerca testuale nei controlli runtime.")
    show_tier_type_control = models.BooleanField(default=True, help_text="Mostra il filtro per tipo Tier nei controlli runtime.")
    show_characteristics_control = models.BooleanField(default=True, help_text="Mostra i filtri per caratteristiche nei controlli runtime.")
    show_sort_controls = models.BooleanField(default=True, help_text="Mostra i controlli di ordinamento nei controlli runtime.")
    badge_mode = models.CharField(max_length=16, choices=BADGE_MODE_CHOICES, default=BADGE_COMPACT, help_text="Modalita di visualizzazione badge caratteristiche sui Tier.")
    caratteristiche = models.ManyToManyField(
        Punteggio,
        blank=True,
        related_name='wiki_tier_collection_widgets_caratteristiche',
        limit_choices_to={'tipo': 'CA'},
        help_text="Filtra i Tier in base alle caratteristiche associate (se valorizzate).",
    )
    widgets = models.ManyToManyField(
        WikiTierWidget,
        blank=True,
        related_name='collections',
        help_text="Widget Tier inclusi (usati quando source_mode = solo selezionati).",
    )

    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    creatore = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wiki_tier_collection_widgets_creati'
    )

    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Widget Collezione Tier"
        verbose_name_plural = "Widget Collezione Tier"

    def __str__(self):
        return f"Widget Collezione Tier #{self.id} ({self.title or 'senza titolo'})"


class WikiMattoniWidget(SyncableModel, models.Model):
    """
    Widget Mattoni configurabile per la wiki.
    Usato in {{WIDGET_MATTONI:id}} dove id è questo widget.
    """
    FILTER_ALL = 'all'
    FILTER_AURA = 'aura'
    FILTER_CARATTERISTICA = 'caratteristica'
    FILTER_CHOICES = [
        (FILTER_ALL, 'Tutti'),
        (FILTER_AURA, 'Per Aura'),
        (FILTER_CARATTERISTICA, 'Per Caratteristica'),
    ]

    title = models.CharField(max_length=200, blank=True, help_text="Titolo opzionale del widget (per identificazione interna)")
    filter_type = models.CharField(max_length=20, choices=FILTER_CHOICES, default=FILTER_ALL)

    aure = models.ManyToManyField(
        Punteggio,
        blank=True,
        related_name='wiki_mattoni_widgets_aure',
        limit_choices_to={'tipo': 'AU'},
        help_text="Aure da includere (se filtro = Aura).",
    )
    caratteristiche = models.ManyToManyField(
        Punteggio,
        blank=True,
        related_name='wiki_mattoni_widgets_caratteristiche',
        limit_choices_to={'tipo': 'CA'},
        help_text="Caratteristiche da includere (se filtro = Caratteristica).",
    )

    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    creatore = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wiki_mattoni_widgets_creati'
    )

    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Widget Mattoni"
        verbose_name_plural = "Widget Mattoni"

    def __str__(self):
        return f"Widget Mattoni #{self.id} ({self.title or 'senza titolo'})"


class WikiButtonWidget(SyncableModel, models.Model):
    """
    Modello per gestire widget di pulsanti configurabili nella wiki.
    Ogni widget contiene una lista di pulsanti con link a pagine wiki o sezioni app.
    """
    title = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Titolo opzionale del widget (per identificazione interna)"
    )
    
    # Metadati
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)
    creatore = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='button_widgets_creati'
    )
    
    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Widget Pulsanti"
        verbose_name_plural = "Widget Pulsanti"

    def __str__(self):
        btn_count = self.buttons.count()
        return f"Widget Pulsanti #{self.id} ({btn_count} pulsanti)"


class WikiButton(SyncableModel, models.Model):
    """
    Singolo pulsante all'interno di un WikiButtonWidget.
    """
    # Stili disponibili
    STYLE_GRADIENT = 'gradient'
    STYLE_LIGHT = 'light'
    STYLE_CHOICES = [
        (STYLE_GRADIENT, 'Gradiente (grande)'),
        (STYLE_LIGHT, 'Chiaro (compatto)'),
    ]
    
    # Dimensioni disponibili
    SIZE_SMALL = 'small'
    SIZE_MEDIUM = 'medium'
    SIZE_LARGE = 'large'
    SIZE_CHOICES = [
        (SIZE_SMALL, 'Piccolo'),
        (SIZE_MEDIUM, 'Medio'),
        (SIZE_LARGE, 'Grande'),
    ]
    
    # Schemi colori disponibili
    COLOR_INDIGO_PURPLE = 'indigo_purple'
    COLOR_RED_ORANGE = 'red_orange'
    COLOR_EMERALD_TEAL = 'emerald_teal'
    COLOR_BLUE_INDIGO = 'blue_indigo'
    COLOR_PINK_ROSE = 'pink_rose'
    COLOR_AMBER_ORANGE = 'amber_orange'
    COLOR_CYAN_BLUE = 'cyan_blue'
    COLOR_VIOLET_PURPLE = 'violet_purple'
    COLOR_SLATE_GRAY = 'slate_gray'
    COLOR_LIME_GREEN = 'lime_green'
    
    COLOR_CHOICES = [
        (COLOR_INDIGO_PURPLE, 'Indaco-Viola'),
        (COLOR_RED_ORANGE, 'Rosso-Arancio'),
        (COLOR_EMERALD_TEAL, 'Smeraldo-Verde Acqua'),
        (COLOR_BLUE_INDIGO, 'Blu-Indaco'),
        (COLOR_PINK_ROSE, 'Rosa'),
        (COLOR_AMBER_ORANGE, 'Ambra-Arancio'),
        (COLOR_CYAN_BLUE, 'Ciano-Blu'),
        (COLOR_VIOLET_PURPLE, 'Viola-Porpora'),
        (COLOR_SLATE_GRAY, 'Ardesia-Grigio'),
        (COLOR_LIME_GREEN, 'Lime-Verde'),
    ]
    
    # Tipi di link
    LINK_TYPE_WIKI = 'wiki'
    LINK_TYPE_APP = 'app'
    LINK_TYPE_CHOICES = [
        (LINK_TYPE_WIKI, 'Pagina Wiki'),
        (LINK_TYPE_APP, 'Sezione App'),
    ]
    
    widget = models.ForeignKey(
        WikiButtonWidget,
        on_delete=models.CASCADE,
        related_name='buttons'
    )
    
    # Contenuto pulsante
    title = models.CharField(max_length=100, help_text="Titolo del pulsante")
    description = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Descrizione (opzionale)"
    )
    subtext = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Testo secondario (solo per stile gradiente)"
    )
    icon = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Nome icona Lucide (es: Sparkles, BookOpen)"
    )
    
    # Stile
    style = models.CharField(
        max_length=20, 
        choices=STYLE_CHOICES, 
        default=STYLE_GRADIENT
    )
    size = models.CharField(
        max_length=20, 
        choices=SIZE_CHOICES, 
        default=SIZE_MEDIUM
    )
    color_preset = models.CharField(
        max_length=30, 
        choices=COLOR_CHOICES, 
        default=COLOR_INDIGO_PURPLE
    )
    
    # Link
    link_type = models.CharField(
        max_length=10, 
        choices=LINK_TYPE_CHOICES, 
        default=LINK_TYPE_WIKI
    )
    wiki_slug = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Slug della pagina wiki di destinazione"
    )
    app_route = models.CharField(
        max_length=200, 
        blank=True, 
        help_text="Percorso della sezione app (es: /app)"
    )
    
    # Ordinamento
    ordine = models.PositiveIntegerField(default=0, help_text="Ordine di visualizzazione")
    
    class Meta:
        ordering = ['ordine', 'id']
        verbose_name = "Pulsante"
        verbose_name_plural = "Pulsanti"

    def __str__(self):
        return f"{self.title} ({self.get_style_display()})"


# --- CONFIGURAZIONE SITO E SOCIAL ---

class ConfigurazioneSito(SyncableModel, models.Model):
    """
    Configurazione generale del sito e informazioni sull'associazione.
    Singleton - dovrebbe esistere un solo record.
    """
    # Chi Siamo
    nome_associazione = models.CharField(max_length=200, default="KOR35", help_text="Nome dell'associazione")
    descrizione_breve = models.TextField(
        default="Un'associazione ludico-culturale che organizza eventi di gioco di ruolo dal vivo (GRV/LARP).",
        help_text="Breve descrizione dell'associazione (2-3 righe)"
    )
    anno_fondazione = models.PositiveIntegerField(default=2020, help_text="Anno di fondazione")
    
    # Sede
    indirizzo = models.CharField(max_length=255, default="Via Esempio 123", help_text="Indirizzo della sede")
    citta = models.CharField(max_length=100, default="Bolzano", help_text="Città")
    cap = models.CharField(max_length=10, default="39100", help_text="CAP")
    provincia = models.CharField(max_length=2, default="BZ", help_text="Sigla provincia")
    nazione = models.CharField(max_length=50, default="Italia")
    
    # Contatti
    email = models.EmailField(default="info@kor35.it", help_text="Email principale")
    pec = models.EmailField(blank=True, help_text="Email PEC (opzionale)")
    telefono = models.CharField(max_length=50, blank=True, help_text="Telefono (opzionale)")

    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Modalita manutenzione attiva",
        help_text="Quando attiva, blocca l'app di gioco/social/staff/pilotaggio e lascia solo la console admin Django.",
    )
    maintenance_public_message = models.TextField(
        blank=True,
        default="Sistema temporaneamente in manutenzione. Riprova tra pochi minuti.",
        verbose_name="Messaggio pubblico manutenzione",
        help_text="Messaggio mostrato in alto nella Wiki al posto dell'accesso alla sezione gioco.",
    )
    maintenance_admin_note = models.TextField(
        blank=True,
        default="MODALITA MANUTENZIONE ATTIVA: non effettuare modifiche ai dati applicativi. Usare solo questa console per riattivare il sistema.",
        verbose_name="Nota visibile in Admin durante manutenzione",
        help_text="Avviso evidenziato in tutte le pagine Admin quando la manutenzione e attiva.",
    )
    creazione_guidata_aperta_giocatori = models.BooleanField(
        default=False,
        verbose_name='Creazione guidata visibile ai giocatori',
        help_text='Se disattivo, il pulsante creazione guidata non compare per i giocatori (staff/master possono ancora usare la sandbox test).',
    )
    staff_dashboard_layout = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Layout Dashboard Staff",
        help_text="Ordine e raggruppamento voci menu Dashboard Staff (globale, sincronizzato).",
    )

    # Metadata
    ultima_modifica = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configurazione Sito"
        verbose_name_plural = "Configurazione Sito"
    
    def __str__(self):
        return f"Configurazione {self.nome_associazione}"
    
    def save(self, *args, **kwargs):
        # Assicura che esista un solo record (Singleton pattern)
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_config(cls):
        """Metodo helper per recuperare la configurazione"""
        config, created = cls.objects.get_or_create(pk=1)
        return config


class LinkSocial(SyncableModel, models.Model):
    """
    Link ai social media e canali di comunicazione dell'associazione
    """
    TIPO_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('whatsapp_cambusa', 'WhatsApp — La Cambusa'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('youtube', 'YouTube'),
        ('twitter', 'Twitter'),
        ('discord', 'Discord'),
        ('telegram', 'Telegram'),
        ('email', 'Email'),
        ('altro', 'Altro'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, help_text="Tipo di social/canale")
    nome_visualizzato = models.CharField(max_length=100, help_text="Nome da mostrare (es: @kor35official)")
    url = models.CharField(max_length=500, help_text="URL o link (es: https://instagram.com/kor35)")
    descrizione = models.CharField(max_length=200, blank=True, help_text="Descrizione opzionale")
    ordine = models.PositiveIntegerField(default=0, help_text="Ordine di visualizzazione (numero più basso = primo)")
    attivo = models.BooleanField(default=True, help_text="Mostra questo link")
    
    class Meta:
        verbose_name = "Link Social"
        verbose_name_plural = "Link Social"
        ordering = ['ordine', 'tipo']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome_visualizzato}"


class PayPalImpostazioniGlobali(SyncableModel, models.Model):
    """
    Singleton (pk=1): credenziali PayPal sandbox e produzione per il pulsante/SDK.
    I segreti restano solo lato server; il client_id viene esposto via API autenticata per il JS SDK.
    """

    use_sandbox = models.BooleanField(
        default=True,
        verbose_name="Usa ambiente Sandbox",
        help_text="Se vero, ordini e token usano api-m.sandbox.paypal.com (credenziali sandbox).",
    )
    sandbox_client_id = models.CharField(max_length=255, blank=True, verbose_name="Sandbox Client ID")
    sandbox_client_secret = models.TextField(blank=True, verbose_name="Sandbox Secret")
    live_client_id = models.CharField(max_length=255, blank=True, verbose_name="Live Client ID")
    live_client_secret = models.TextField(blank=True, verbose_name="Live Secret")

    mostra_pulsante_carta = models.BooleanField(
        default=False,
        verbose_name="Mostra pulsante Carta",
        help_text="Se attivo, nel checkout PayPal puo comparire anche il pulsante carta.",
    )
    mostra_pulsante_mybank = models.BooleanField(
        default=False,
        verbose_name="Mostra pulsante MyBank",
        help_text="Se attivo, nel checkout PayPal puo comparire anche MyBank (quando supportato).",
    )

    class Meta:
        verbose_name = "Impostazioni PayPal (globale)"
        verbose_name_plural = "Impostazioni PayPal (globale)"

    def __str__(self):
        return "Impostazioni PayPal"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        row, _created = cls.objects.get_or_create(pk=1)
        return row


class IscrizioneEventoPagamento(SyncableModel, models.Model):
    """
    Tentativo / esito pagamento iscrizione evento (Orders API v2).
    """

    class Stato(models.TextChoices):
        PENDING = "PENDING", "In attesa di pagamento"
        CAPTURED = "CAPTURED", "Pagato e iscritto"
        FAILED = "FAILED", "Fallito"
        CANCELLED = "CANCELLED", "Annullato"

    class TipoOrdine(models.TextChoices):
        ISCRIZIONE = "ISCRIZIONE", "Iscrizione iniziale"
        INTEGRA = "INTEGRA", "Integrazione opzioni"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    tipo_ordine = models.CharField(
        max_length=12,
        choices=TipoOrdine.choices,
        default=TipoOrdine.ISCRIZIONE,
    )
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="iscrizioni_paypal")
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="iscrizioni_evento_paypal")
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="iscrizioni_evento_paypal",
    )
    paypal_order_id = models.CharField(max_length=80, unique=True, db_index=True)
    paypal_capture_id = models.CharField(max_length=80, blank=True)
    stato = models.CharField(max_length=20, choices=Stato.choices, default=Stato.PENDING)
    importo_euro = models.DecimalField(max_digits=10, decimal_places=2)
    sandbox_usato = models.BooleanField(default=False, help_text="True se l'ordine è stato creato in sandbox.")
    ultimo_errore = models.TextField(blank=True)

    class Meta:
        verbose_name = "Iscrizione evento (PayPal)"
        verbose_name_plural = "Iscrizioni evento (PayPal)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.evento_id} / {self.personaggio_id} ({self.stato})"


class IscrizioneEventoPagamentoOpzione(SyncableModel, models.Model):
    """Opzioni acquistate con un pagamento PayPal."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    pagamento = models.ForeignKey(
        IscrizioneEventoPagamento,
        on_delete=models.CASCADE,
        related_name="righe_opzioni",
    )
    opzione = models.ForeignKey(
        EventoIscrizioneOpzione,
        on_delete=models.PROTECT,
        related_name="acquisti",
    )
    costo_euro = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "Opzione pagamento iscrizione"
        verbose_name_plural = "Opzioni pagamento iscrizione"
        constraints = [
            models.UniqueConstraint(
                fields=["pagamento", "opzione"],
                name="uniq_iscrizione_pagamento_opzione",
            ),
        ]

    def __str__(self):
        return f"{self.pagamento_id} — {self.opzione_id}"