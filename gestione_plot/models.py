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
        related_name='eventi_gestiti'
    )

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "1. Eventi"

    def __str__(self):
        return self.titolo

class GiornoEvento(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='giorni')
    data_ora_inizio = models.DateTimeField()
    data_ora_fine = models.DateTimeField()
    sinossi_breve = models.TextField(max_length=1000)

    class Meta:
        verbose_name = "Giorno Evento"
        verbose_name_plural = "2. Giorni Evento"
        ordering = ['data_ora_inizio']

class Quest(models.Model):
    giorno = models.ForeignKey(GiornoEvento, on_delete=models.CASCADE, related_name='quests')
    titolo = models.CharField(max_length=200)
    orario_indicativo = models.TimeField()
    descrizione_ampia = models.TextField()

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
    tipo = models.CharField(max_length=3, choices=[('INV', 'Inventario'), ('MAN', 'Manifesto')])
    manifesto = models.ForeignKey(Manifesto, on_delete=models.SET_NULL, null=True, blank=True)
    inventario = models.ForeignKey(Inventario, on_delete=models.SET_NULL, null=True, blank=True)
    qr_code = models.OneToOneField(QrCode, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Oggetto Vista Quest"
        verbose_name_plural = "6. Oggetti Vista"