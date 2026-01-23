from django.db import models
from django.conf import settings
from personaggi.models import Personaggio, Manifesto, Inventario, QrCode

# --- 1. SEZIONE TEMPLATE (L'ANAGRAFICA GENERALE) ---

class MostroTemplate(models.Model):
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

class AttaccoTemplate(models.Model):
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

class Evento(models.Model):
    titolo = models.CharField(max_length=200)
    pc_guadagnati = models.PositiveIntegerField(default=0)
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

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "1. Eventi"

    def __str__(self):
        return self.titolo

class GiornoEvento(models.Model):
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

class Quest(models.Model):
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

class QuestMostro(models.Model):
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

class PngAssegnato(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='png_richiesti')
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, limit_choices_to={'tipologia__giocante': False})
    staffer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    ordine_uscita = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "PnG Assegnato"
        verbose_name_plural = "5. PnG Assegnati"
        ordering = ['staffer', 'ordine_uscita']

class QuestVista(models.Model):
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
    
    # Riferimenti a tutti i possibili tipi di a_vista
    manifesto = models.ForeignKey(Manifesto, on_delete=models.SET_NULL, null=True, blank=True)
    inventario = models.ForeignKey(Inventario, on_delete=models.SET_NULL, null=True, blank=True)
    personaggio = models.ForeignKey(Personaggio, on_delete=models.SET_NULL, null=True, blank=True)
    oggetto = models.ForeignKey('personaggi.Oggetto', on_delete=models.SET_NULL, null=True, blank=True)
    tessitura = models.ForeignKey('personaggi.Tessitura', on_delete=models.SET_NULL, null=True, blank=True)
    infusione = models.ForeignKey('personaggi.Infusione', on_delete=models.SET_NULL, null=True, blank=True)
    cerimoniale = models.ForeignKey('personaggi.Cerimoniale', on_delete=models.SET_NULL, null=True, blank=True)
    
    qr_code = models.OneToOneField(QrCode, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Oggetto Vista Quest"
        verbose_name_plural = "6. Oggetti Vista"
        
class StaffOffGame(models.Model):
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
    
class QuestFase(models.Model):
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

class QuestTask(models.Model):
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

class PaginaRegolamento(models.Model):
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

    class Meta:
        ordering = ['ordine', 'titolo']

    def __str__(self):
        return f"{self.titolo} ({self.parent.titolo if self.parent else 'Root'})"


class WikiImmagine(models.Model):
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