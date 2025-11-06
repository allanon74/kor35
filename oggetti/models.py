import uuid
import secrets
import string
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils import timezone
from personaggi.models import Punteggio, punteggi_tipo, AURA, ELEMENTO, Statistica

def generate_short_id(length=14):
    """
    Genera un ID casuale sicuro di 14 caratteri.
    Usa A-Z, a-z, 0-9.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# through

class OggettoElemento(models.Model):
    """
    Modello intermedio per permettere a un Oggetto di avere
    più volte lo stesso Elemento (Punteggio).
    """
    oggetto = models.ForeignKey(
        'Oggetto', 
        on_delete=models.CASCADE
    )
    elemento = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE,
        # Applicando qui il filtro, l'inline nell'admin
        # mostrerà solo Punteggi di tipo ELEMENTO.
        limit_choices_to={'tipo': ELEMENTO}, 
        verbose_name="Elemento"
    )
    
class AttivataElemento(models.Model):
    """
    Modello intermedio per permettere a un Oggetto di avere
    più volte lo stesso Elemento (Punteggio).
    """
    attivata = models.ForeignKey(
        'Attivata', 
        on_delete=models.CASCADE
    )
    elemento = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE,
        # Applicando qui il filtro, l'inline nell'admin
        # mostrerà solo Punteggi di tipo ELEMENTO.
        limit_choices_to={'tipo': ELEMENTO}, 
        verbose_name="Elemento"
    )


class OggettoStatistica(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(
        Statistica, 
        on_delete=models.CASCADE
    )
    valore = models.IntegerField(default=0)

    class Meta:
        unique_together = ('oggetto', 'statistica') # Impedisce duplicati

    def __str__(self):
        return f"{self.oggetto.nome} - {self.statistica.nome}: {self.valore}"

# --- 1. NUOVO MODELLO "THROUGH" per Oggetto <-> Valore Base ---
class OggettoStatisticaBase(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)

    class Meta:
        unique_together = ('oggetto', 'statistica')
        verbose_name = "Statistica (Valore Base)"
        verbose_name_plural = "Statistiche (Valori Base)"

    def __str__(self):
        return f"{self.oggetto.nome} - {self.statistica.nome}: {self.valore_base}"


# --- 2. NUOVO MODELLO "THROUGH" per Attivate <-> Valore Base ---
class AttivataStatisticaBase(models.Model):
    attivata = models.ForeignKey('Attivata', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)



    class Meta:
        unique_together = ('attivata', 'statistica')
        verbose_name = "Statistica (Valore Base)"
        verbose_name_plural = "Statistiche (Valori Base)"

    def __str__(self):
        return f"{self.attivata.nome} - {self.statistica.nome}: {self.valore_base}"


# abstract

class A_vista(models.Model):
    id = models.AutoField(primary_key=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=100)
    testo = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} ({self.id})"
    
    class Meta:
        ordering = ['-data_creazione'] 
        # abstract = True
    
    class Meta:
        verbose_name = "Elemento dell'Oggetto"
        verbose_name_plural = "Elementi dell'Oggetto"


# Create your models here.
class QrCode(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id = models.CharField(
        primary_key=True,  # <-- QUESTO È IL PUNTO CHIAVE
        max_length=14,
        default=generate_short_id,
        editable=False
    )
    data_creazione = models.DateTimeField(auto_now_add=True)
    testo = models.TextField(blank=True, null=True)
    vista = models.OneToOneField(A_vista, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return "({codice})".format(codice=self.id)
    
    def save(self, *args, **kwargs):
        """
        Sovrascrive il metodo save per gestire le (improbabili)
        collisioni della chiave primaria.
        """
        # _state.adding è True solo quando l'oggetto viene creato
        if self._state.adding:
            while True:  # Inizia un ciclo di tentativi
                try:
                    # Prova a salvare l'oggetto. 
                    # L'ID è già stato generato dal 'default'.
                    super().save(*args, **kwargs)
                    # Se il salvataggio va a buon fine, usciamo dal ciclo
                    break
                except IntegrityError:
                    # Se fallisce per IntegrityError, significa che l'ID esiste.
                    # Generiamo un nuovo ID e il ciclo 'while' riproverà.
                    self.id = generate_short_id()
        else:
            # Se non è un nuovo oggetto (_state.adding è False),
            # è un aggiornamento. Salviamo normalmente.
            super().save(*args, **kwargs)


class Inventario(A_vista):
    """
    Rappresenta un contenitore di Oggetti.
    (es. forziere, negozio, deposito, o un Personaggio).
    """
    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventari"

    def __str__(self):
        return f"Inventario: {self.nome}"

    def get_oggetti(self, data=None):
        """
        Restituisce un queryset di oggetti in questo inventario
        in un momento specifico.
        Se data è None, restituisce gli oggetti attuali.
        """
        if data is None:
            data = timezone.now()
        
        return Oggetto.objects.filter(
            tracciamento_inventario__inventario=self,
            tracciamento_inventario__data_inizio__lte=data,
            tracciamento_inventario__data_fine__isnull=True
        )

# --- 2. NUOVO MODELLO "THROUGH" PER IL TRACCIAMENTO STORICO ---
class OggettoInInventario(models.Model):
    """
    Traccia la cronologia di un Oggetto in un Inventario.
    Un record "attivo" (data_fine=None) indica la posizione attuale.
    """
    oggetto = models.ForeignKey(
        'Oggetto', 
        on_delete=models.CASCADE,
        related_name="tracciamento_inventario"
    )
    inventario = models.ForeignKey(
        Inventario, 
        on_delete=models.CASCADE,
        related_name="tracciamento_oggetti"
    )
    data_inizio = models.DateTimeField(default=timezone.now)
    data_fine = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Se Nullo, l'oggetto è attualmente in questo inventario."
    )

    class Meta:
        verbose_name = "Tracciamento Oggetto in Inventario"
        verbose_name_plural = "Tracciamenti Oggetto in Inventario"
        ordering = ['-data_inizio'] # Ordina per il più recente

    def __str__(self):
        stato = "Attuale" if self.data_fine is None else f"Fino a {self.data_fine.strftime('%Y-%m-%d')}"
        return f"{self.oggetto.nome} in {self.inventario.nome} (Da {self.data_inizio.strftime('%Y-%m-%d')} - {stato})"



class Oggetto(A_vista):
    # a_vista_ptr = models.OneToOneField(
    #     A_vista,
    #     on_delete=models.CASCADE,
    #     parent_link=True,
    #     # related_name='istanza_oggetto', # Nome univoco per evitare conflitti
    #     null=True # <-- Questo è il punto chiave temporaneo
    # )
    # elementi = models.ManyToManyField(Punteggio, blank=True, limit_choices_to={'tipo' : ELEMENTO}, verbose_name="Elementi associati")
    
    elementi = models.ManyToManyField(
        Punteggio, 
        blank=True, 
        verbose_name="Elementi associati",
        through='OggettoElemento', # Specifica il modello intermedio
        # Rimuovi limit_choices_to da qui, è stato spostato
        # nel modello OggettoElemento.
    )
    statistiche = models.ManyToManyField(
        Statistica,
        through='OggettoStatistica',
        blank=True,
        verbose_name="Statistiche modificate", 
        related_name = "oggetti_statistiche",
    )
    
    # --- 3. NUOVO CAMPO ManyToMany per i VALORI BASE ---
    statistiche_base = models.ManyToManyField(
        Statistica,
        through='OggettoStatisticaBase',
        blank=True,
        verbose_name="Statistiche (Valori Base)",
        related_name='oggetti_statistiche_base' # Nuovo related_name univoco
    )
    
    aura = models.ForeignKey(Punteggio, blank=True, null=True, on_delete=models.SET_NULL, limit_choices_to={'tipo' : AURA}, verbose_name="Aura associata", related_name="oggetti_aura")

    def elementi_list(self):
        return ", ".join(str(elemento) for elemento in self.elementi.all())

    def __str__(self):
        return f"{self.nome} - {self.aura}"
    
    @property
    def livello(self):
        return self.elementi.count()
    
    @property
    def TestoFormattato(self):
        if not self.testo:
            return ""
        testo_formattato = self.testo
        
        stats_links = self.oggettostatisticabase_set.select_related('statistica').all()
        
        for link in stats_links:
            param = link.statistica.parametro
            valore = link.valore_base
        
            if param:
                testo_formattato = testo_formattato.replace(f"{{{param}}}", str(valore))
        return testo_formattato
    
    @property
    def inventario_corrente(self):
        """
        Restituisce l'istanza di Inventario in cui questo oggetto
        si trova attualmente.
        """
        tracciamento_attuale = self.tracciamento_inventario.filter(
            data_fine__isnull=True
        ).first() # .first() perché ce ne dovrebbe essere solo uno
        
        return tracciamento_attuale.inventario if tracciamento_attuale else None

    def sposta_in_inventario(self, nuovo_inventario, data_spostamento=None):
        """
        Metodo principale per spostare un oggetto in un nuovo inventario.
        Gestisce la cronologia.
        """
        if data_spostamento is None:
            data_spostamento = timezone.now()

        # 1. Trova e chiudi il record di tracciamento attuale (se esiste)
        tracciamento_attuale = self.tracciamento_inventario.filter(
            data_fine__isnull=True
        ).first()
        
        if tracciamento_attuale:
            if tracciamento_attuale.inventario == nuovo_inventario:
                # L'oggetto è già in questo inventario, non fare nulla
                return
            
            tracciamento_attuale.data_fine = data_spostamento
            tracciamento_attuale.save()

        # 2. Crea il nuovo record di tracciamento (se nuovo_inventario non è None)
        # Se nuovo_inventario è None, l'oggetto viene "lasciato a terra"
        if nuovo_inventario is not None:
            OggettoInInventario.objects.create(
                oggetto=self,
                inventario=nuovo_inventario,
                data_inizio=data_spostamento
            )
    # -----------------------------------------
    
        
    
class Attivata(A_vista):
    
    elementi = models.ManyToManyField(
        Punteggio, 
        blank=True, 
        verbose_name="Elementi associati",
        through='AttivataElemento', # Specifica il modello intermedio
        # Rimuovi limit_choices_to da qui, è stato spostato
        # nel modello Through AttivataElemento.
    )
    
    statistiche_base = models.ManyToManyField(
        Statistica,
        through='AttivataStatisticaBase',
        blank=True,
        verbose_name="Statistiche (Valori Base)",
        related_name='attivata_statistiche_base' # related_name univoco
    )

    def __str__(self):
        return f"Attivata: {self.nome}"

    @property
    def livello(self):
        return self.elementi.count()

    @property
    def TestoFormattato(self):
        """
        Sostituisce i placeholder {sigla} nel testo
        con i valori da AttivataStatisticaBase.
        """
        if not self.testo:
            return ""
        
        testo_formattato = self.testo
        
        # Usiamo il related_name 'attivatastatisticabase_set'
        stats_links = self.attivatastatisticabase_set.select_related('statistica').all()
        
        for link in stats_links:
            param = link.statistica.parametro
            valore = link.valore_base
            
            if param:
                testo_formattato = testo_formattato.replace(f"{{{param}}}", str(valore))
                
        return testo_formattato

    
class Manifesto(A_vista):

    def __str__(self):
        return f"Manifesto: {self.nome}"