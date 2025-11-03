import uuid
import secrets
import string
from django.db import models, IntegrityError
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
    
    aura = models.ForeignKey(Punteggio, blank=True, null=True, on_delete=models.SET_NULL, limit_choices_to={'tipo' : AURA}, verbose_name="Aura associata", related_name="oggetti_aura")

    def elementi_list(self):
        return ", ".join(str(elemento) for elemento in self.elementi.all())

    def __str__(self):
        return f"{self.nome} - {self.aura}"
    
    @property
    def livello(self):
        return self.elementi.count()
    
    
class Manifesto(A_vista):

    def __str__(self):
        return f"Manifesto: {self.nome}"