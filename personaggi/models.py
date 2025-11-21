from django.db.models import Sum, F
import re
import secrets
import string
from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from colorfield.fields import ColorField
from django_icon_picker.field import IconField
from cms.models.pluginmodel import CMSPlugin
from django.utils.html import format_html
from icon_widget.fields import CustomIconField

# --- COSTANTI ---
COSTO_PER_MATTONE = 100

# --- COSTANTI RANGO (NUOVO) ---
RANGO_NORMALE = 1
RANGO_EROICO = 2
RANGO_LEGGENDARIO = 3
RANGO_MITOLOGICO = 4
RANGO_DIVINO = 5
RANGO_COSMICO = 6

RANGO_CHOICES = [
    (RANGO_NORMALE, 'Normale'),
    (RANGO_EROICO, 'Eroico'),
    (RANGO_LEGGENDARIO, 'Leggendario'),
    (RANGO_MITOLOGICO, 'Mitologico'),
    (RANGO_DIVINO, 'Divino'),
    (RANGO_COSMICO, 'Cosmico'),
]

def get_testo_rango(valore):
    dict_rango = dict(RANGO_CHOICES)
    return dict_rango.get(valore, "Sconosciuto")

def _get_icon_color_from_bg(hex_color):
    """
    Determina se un colore di sfondo hex è chiaro o scuro
    e restituisce 'white' o 'black' per il testo/icona.
    """
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminanza = ((r * 299) + (g * 587) + (b * 114)) / 1000
        return 'black' if luminanza > 128 else 'white'
    except Exception:
        return 'black'

# tipi generici per DDL
CARATTERISTICA = "CA"
STATISTICA = "ST"
ELEMENTO = "EL"
AURA = "AU"
CONDIZIONE = "CO"
CULTO = "CU"   
VIA = "VI"
ARTE = "AR"
ARCHETIPO = "AR"
# MATTONE_TYPE = "MA" # Nuovo tipo per distinguere i Mattoni se necessario, o si può usare ELEMENTO

punteggi_tipo = [
    (CARATTERISTICA, 'Caratteristica'),
    (STATISTICA, 'Statistica'),
    (ELEMENTO, 'Elemento'),
    (AURA, 'Aura',),
    (CONDIZIONE, 'Condizione',),
    (CULTO, 'Culto',),
    (VIA, 'Via',),
    (ARTE, 'Arte',),
    (ARCHETIPO, 'Archetipo',),
    # (MATTONE_TYPE, 'Mattone (Elemento)',),
]

TIER_1 = "T1"
TIER_2 = "T2"
TIER_3 = "T3"
TIER_4 = "T4"

tabelle_tipo = [
    (TIER_1, 'Tier 1'),
    (TIER_2, 'Tier 2'),
    (TIER_3, 'Tier 3'),
    (TIER_4, 'Tier 4'),
]

# --- Scelte per i modificatori ---
MODIFICATORE_ADDITIVO = 'ADD'
MODIFICATORE_MOLTIPLICATIVO = 'MOL'
MODIFICATORE_CHOICES = [
    (MODIFICATORE_ADDITIVO, 'Additivo (+N)'),
    (MODIFICATORE_MOLTIPLICATIVO, 'Moltiplicativo (xN)'),
]

# --- Scelte per Metatalento ---
META_NESSUN_EFFETTO = 'NE'
META_VALORE_PUNTEGGIO = 'VP'
META_SOLO_TESTO = 'TX'
META_LIVELLO_INFERIORE = 'LV'

METATALENTO_CHOICES = [
    (META_NESSUN_EFFETTO, 'Nessun Effetto'),
    (META_VALORE_PUNTEGGIO, 'Valore per Punteggio'),
    (META_SOLO_TESTO, 'Solo Testo Addizionale'),
    (META_LIVELLO_INFERIORE, 'Solo abilità con livello pari o inferiore al punteggio'),
]

# Classi astratte

class A_modello(models.Model):
    id = models.AutoField("Codice Identificativo", primary_key = True, )
    class Meta:
        abstract = True
        
class A_vista(models.Model):
    """
    Classe base concreta. Usata da Oggetto, Tecnica (e quindi Infusione/Tessitura) e Attivata (Legacy).
    NON è abstract per permettere le FK generiche (es. QrCode).
    """
    id = models.AutoField(primary_key=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=100)
    testo = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} ({self.id})"
    
    class Meta:
        ordering = ['-data_creazione'] 
        verbose_name = "Elemento dell'Oggetto"
        verbose_name_plural = "Elementi dell'Oggetto"

class CondizioneStatisticaMixin(models.Model):
    """
    Mixin per aggiungere filtri condizionali alle statistiche (Oggetti, Tessiture, Infusioni).
    """
    limit_a_aure = models.ManyToManyField(
        'Punteggio', 
        blank=True, 
        limit_choices_to={'tipo': AURA},
        related_name="%(class)s_limit_aure",
        verbose_name="Applica solo se Aura..."
    )
    limit_a_elementi = models.ManyToManyField(
        'Punteggio', 
        blank=True, 
        limit_choices_to={'tipo': ELEMENTO},
        related_name="%(class)s_limit_elementi",
        verbose_name="Applica solo se Elemento..."
    )

    class Meta:
        abstract = True


#definizioni classi

class Tabella(A_modello):
    nome = models.CharField("Nome", max_length = 90, )
    descrizione = models.TextField("descrizione", null=True, blank=True, )

    class Meta:
        verbose_name = "Tabella"
        verbose_name_plural = "Tabelle"

    def __str__(self):
        return self.nome

class Tier(Tabella):
    tipo = models.CharField('Tier', choices=tabelle_tipo, max_length=2)    
    foto = models.ImageField(upload_to='tiers/', null=True, blank=True)

    class Meta:
        verbose_name = "Tier"
        verbose_name_plural = "Tiers"

class Punteggio(Tabella):
    sigla = models.CharField('Sigla', max_length=3, unique=True, )
    tipo = models.CharField('Tipo di punteggio', choices=punteggi_tipo, max_length=2)
    colore = ColorField('Colore', default='#1976D2', help_text="Colore associato al punteggio (es. per icone).")
    icona = CustomIconField(blank=True)
    ordine = models.IntegerField(default=0, help_text="Valore per l'ordinamento (più basso appare prima)")
    is_mattone = models.BooleanField("è un mattone?", default=False)
    
    # NUOVI CAMPI PER LE AURE
    is_soprannaturale = models.BooleanField("Aura Soprannaturale", default=False, help_text="Se attivo è soprannaturale, altrimenti naturale.")
    is_generica = models.BooleanField("Aura Generica", default=False, help_text="Se attivo, il valore è calcolato sul max delle altre aure.")
    permette_infusioni = models.BooleanField(default=False)
    permette_tessiture = models.BooleanField(default=False)
    
    caratteristica_relativa = models.ForeignKey(
        "Punteggio",
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo' : CARATTERISTICA},
        null=True, blank=True,
        verbose_name = "Caratteristica relativa",
        related_name = "punteggi_caratteristica",
        )
    modifica_statistiche = models.ManyToManyField(
        'Statistica',
        through='CaratteristicaModificatore',
        related_name='modificata_da_caratteristiche',
        blank=True
    )
 
    class Meta:
        verbose_name = "Punteggio"
        verbose_name_plural = "Punteggi"
        ordering =['tipo', 'ordine', 'nome']
        
    def svg_icon(self):
        return format_html(
            '<img src="{}" height="30" width="30" alt="{}"/>'.format(
                f"/{self.icon}"
                if self.icon.endswith(".svg")
                else f"https://api.iconify.design/{self.icon}.svg",
                f"Icon for {self.name}"
            )
        )

    @property
    def icona_url(self):
        if self.icona:
            return f"{settings.MEDIA_URL}{self.icona}"
        return None

    @property
    def icona_html(self):
        url = self.icona_url
        colore = self.colore
        
        if url and colore:
            style = (
                f"width: 24px; "
                f"height: 24px; "
                f"background-color: {colore}; "
                f"mask-image: url({url}); "
                f"-webkit-mask-image: url({url}); "
                f"mask-repeat: no-repeat; "
                f"-webkit-mask-repeat: no-repeat; "
                f"mask-size: contain; "
                f"-webkit-mask-size: contain; "
                f"display: inline-block; "
                f"vertical-align: middle;"
            )
            return format_html('<div style="{}"></div>', style)
        return ""
    
    def icona_cerchio(self, inverted=True):
        url_icona_locale = self.icona_url 
        colore_sfondo = self.colore
        
        if not url_icona_locale or not colore_sfondo:
            return ""

        colore_icona_contrasto = _get_icon_color_from_bg(colore_sfondo)

        if inverted:
            colore_icona_contrasto = self.colore
            colore_sfondo = _get_icon_color_from_bg(colore_sfondo)
            
        stile_cerchio = (
            f"display: inline-block; "
            f"width: 30px; "
            f"height: 30px; "
            f"background-color: {colore_sfondo}; "
            f"border-radius: 50%; "
            f"vertical-align: middle; "
            f"text-align: center; "
            f"line-height: 30px;"
        )
        
        stile_icona_maschera = (
            f"display: inline-block; "
            f"width: 24px; "
            f"height: 24px; "
            f"vertical-align: middle; "
            f"background-color: {colore_icona_contrasto}; "
            f"mask-image: url({url_icona_locale}); "
            f"-webkit-mask-image: url({url_icona_locale}); "
            f"mask-repeat: no-repeat; "
            f"-webkit-mask-repeat: no-repeat; "
            f"mask-size: contain; "
            f"-webkit-mask-size: contain; "
        )

        return format_html(
            '<div style="{}">'
            '  <div style="{}"></div>'
            '</div>',
            stile_cerchio,
            stile_icona_maschera
        )
    
    @property
    def icona_cerchio_html(self):
        return self.icona_cerchio(inverted=False)
    
    @property
    def icona_cerchio_inverted_html(self):
        return self.icona_cerchio(inverted=True)
    
    def __str__(self):
        result = "{tipo} - {nome}"
        return result.format(nome=self.nome, tipo = self.tipo)

class Caratteristica(Punteggio):
    class Meta:
        proxy = True
        verbose_name = "Caratteristica (Gestione)"
        verbose_name_plural = "Caratteristiche (Gestione)"


class Statistica(Punteggio):
    parametro = models.CharField(
        max_length=10,
        unique=True,
        blank=True, 
        null=True,
        help_text="La variabile da usare nel testo, es. 'pv' (senza parentesi graffe)."
    )
    valore_predefinito = models.IntegerField(
        default=0,
        help_text="Valore di default per questa statistica."
    )
    valore_base_predefinito = models.IntegerField(
        default=0,
        help_text="Valore BASE di default per questa statistica (per i VALORI INIZIALI)."
    )
    tipo_modificatore = models.CharField(
        max_length=3,
        choices=MODIFICATORE_CHOICES,
        default=MODIFICATORE_ADDITIVO,
        help_text="Come questo punteggio si combina con altri."
    )
    is_primaria = models.BooleanField(
        default=False,
        help_text="Seleziona se questa è una statistica primaria da mostrare in homepage."
    )

    def save(self, *args, **kwargs):
        self.tipo = STATISTICA
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Statistica"
        verbose_name_plural = "Statistiche"

# --- NUOVO MODELLO MATTONE ---
class Mattone(Punteggio):
    aura = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': AURA},
        related_name="mattoni_aura",
        verbose_name="Aura associata"
    )
    caratteristica_associata = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': CARATTERISTICA},
        related_name="mattoni_caratteristica",
        verbose_name="Caratteristica associata"
    )
    descrizione_mattone = models.TextField("Descrizione Mattone", blank=True, null=True)
    descrizione_metatalento = models.TextField("Descrizione Metatalento", blank=True, null=True)
    
    testo_addizionale = models.TextField(
        "Testo Addizionale", 
        blank=True, 
        null=True,
        help_text="Supporta parametri statistiche (es. {pv}) e il parametro {caratt}. Supporta moltiplicatori: {3*caratt}."
    )
    
    funzionamento_metatalento = models.CharField(
        max_length=2,
        choices=METATALENTO_CHOICES,
        default=META_NESSUN_EFFETTO,
        verbose_name="Funzionamento del Metatalento"
    )
    
    statistiche = models.ManyToManyField(
        Statistica,
        through='MattoneStatistica',
        blank=True,
        verbose_name="Statistiche modificate",
        related_name="mattoni_statistiche"
    )

    def save(self, *args, **kwargs):
        self.is_mattone = True
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Mattone"
        verbose_name_plural = "Mattoni"
        unique_together = ('aura', 'caratteristica_associata')

class MattoneStatistica(models.Model):
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(
        max_length=3,
        choices=MODIFICATORE_CHOICES,
        default=MODIFICATORE_ADDITIVO
    )
    class Meta:
        unique_together = ('mattone', 'statistica')

# --- PROXY MODEL PER AURA ---
class Aura(Punteggio):
    class Meta:
        proxy = True
        verbose_name = "Aura (Gestione)"
        verbose_name_plural = "Aure (Gestione)"
        
    def save(self, *args, **kwargs):
        self.type = AURA
        super().save(*args, **kwargs)

# --- MODELLO DI AURA ---
class ModelloAura(models.Model):
    aura = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': AURA},
        related_name="modelli_definiti"
    )
    nome = models.CharField(max_length=100)
    mattoni_proibiti = models.ManyToManyField(
        Mattone, 
        blank=True, 
        related_name="proibiti_in_modelli"
    )

    def clean(self):
        # Validazione: i mattoni proibiti devono appartenere all'aura selezionata
        # Nota: questo check funziona bene nel save o clean, ma per M2M serve attenzione
        # perché le relazioni vengono salvate dopo l'oggetto principale.
        super().clean()

    def __str__(self):
        return f"{self.nome} ({self.aura.nome})"

    class Meta:
        verbose_name = "Modello di Aura"
        verbose_name_plural = "Modelli di Aura"


class CaratteristicaModificatore(models.Model):
    caratteristica = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': CARATTERISTICA},
        related_name = "modificatori_dati",
    )
    statistica_modificata = models.ForeignKey(
        Statistica, 
        on_delete=models.CASCADE,
        related_name = "modificatori_ricevuti",
    )
    modificatore = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.0,
        help_text="Es: +1, +0.5, ecc. (valore additivo)"
    )
    ogni_x_punti = models.IntegerField(
        default=1,
        help_text="Applica il modificatore ogni X punti di caratteristica."
    )
    
    class Meta:
        verbose_name = "Modificatore da Caratteristica"
        verbose_name_plural = "Modificatori da Caratteristiche"
        unique_together = ('caratteristica', 'statistica_modificata')
 
class AbilitaStatistica(models.Model):
    abilita = models.ForeignKey('Abilita', on_delete=models.CASCADE)
    statistica = models.ForeignKey(
        Statistica, 
        on_delete=models.CASCADE
    )
    tipo_modificatore = models.CharField(
        max_length=3,
        choices=MODIFICATORE_CHOICES,
        default=MODIFICATORE_ADDITIVO
    )
    valore = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('abilita', 'statistica')

    def __str__(self):
        return f"{self.abilita.nome} - {self.statistica.nome}: {self.valore}"

class Abilita(A_modello):
    nome = models.CharField("Nome dell'abilità", max_length = 90, )
    descrizione = models.TextField('Descrizione', null=True, blank=True,)
    costo_pc = models.IntegerField("Costo base dell'abilità in Punti Caratteristica", default=0, )
    costo_crediti = models.IntegerField("Costo base dell'abilità in Crediti", default=0, )
    
    caratteristica = models.ForeignKey(
        Punteggio,  
        on_delete=models.CASCADE,
        verbose_name="Caratteristica", 
        limit_choices_to={'tipo__in' : [CARATTERISTICA, CONDIZIONE, ]},
    )
    tiers = models.ManyToManyField(
        Tier,
        related_name = "abilita",
        through = "abilita_tier",
        help_text = "Tiers in cui è presente l'abilità",
    )
    requisiti = models.ManyToManyField(
        Punteggio,
        related_name = "abilita_req",
        through = "abilita_requisito",
        help_text = "Caratteristiche requisito di sblocco",
    )
    tabelle_sbloccate = models.ManyToManyField(
        Tabella,
        related_name = "abilita_sbloccante",
        through = "abilita_sbloccata",
        help_text = "Tabelle sbloccate dall'abilità",
    )
    punteggio_acquisito = models.ManyToManyField(
        Punteggio,
        related_name = "abilita_acquisizione",
        through = "abilita_punteggio",
        help_text = "Caratteristiche requisito di sblocco",
    )
    statistiche = models.ManyToManyField(
        Statistica,
        through='AbilitaStatistica',
        blank=True,
        verbose_name="Statistiche modificate", 
        related_name="abilita_statistiche",
    )
 
    class Meta:
        verbose_name = "Abilità"
        verbose_name_plural = "Abilità"

    def __str__(self):
        return self.nome

# --- RIMOSSE CLASSI: Spell, Mattone (vecchio), spell_elemento, spell_mattone ---

# Classi Through

class abilita_tier(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
    tabella = models.ForeignKey(Tier, on_delete=models.CASCADE, )
    ordine = models.IntegerField("Ordine in tabella", default=10, )
    
    class Meta:
        verbose_name = "Abilità - Tier"
        verbose_name_plural = "Abilità - Tiers"
        ordering = ["ordine", "abilita__nome", ]

    def __str__(self):
        testo = "{abilita} - {tabella} ({costo})"
        return testo.format(abilita=self.abilita.nome, tabella=self.tabella.nome, costo=self.abilita.costo_crediti)

class abilita_prerequisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti", )
    prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati", )

    class Meta:
        verbose_name = "Abilità - Prerequisito"
        verbose_name_plural = "Abilità - Prerequisiti"

    def __str__(self):
        testo = "{abilita} necessita {prerequisito}"
        return testo.format(abilita=self.abilita.nome, prerequisito=self.prerequisito.nome)

 
class abilita_requisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo' : CARATTERISTICA})
    valore = models.IntegerField("Punteggio della caratteristica", default=1, )
    
    class Meta:
        verbose_name = "Abilità - Requisito"
        verbose_name_plural = "Abilità - Requisiti"

    def __str__(self):
        testo = "{abilita} necessita {requisito}: {valore}"
        return testo.format(abilita=self.abilita.nome, requisito=self.requisito.nome, valore=self.valore)

class abilita_sbloccata(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
    sbloccata = models.ForeignKey(Tabella, on_delete=models.CASCADE, )

    class Meta:
        verbose_name = "Abilità - Tabella sbloccata"
        verbose_name_plural = "Abilità - Tabelle sbloccate"

    def __str__(self):
        testo = "{abilita} sblocca {sbloccata}"
        return testo.format(abilita=self.abilita.nome, sbloccata=self.sbloccata.nome)

    
class abilita_punteggio(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, )
    punteggio = models.ForeignKey(Punteggio, on_delete=models.CASCADE, )
    valore = models.IntegerField("Punteggio della caratteristica", default=1, )

    class Meta:
        verbose_name = "Abilità - Punteggio assegnato"
        verbose_name_plural = "Abilità - Punteggi assegnati"

    def __str__(self):
        testo = "{abilita} -> {punteggio} ({valore})"
        return testo.format(abilita=self.abilita.nome, punteggio=self.punteggio.nome, valore=self.valore)

# --- LEGACY: ATTIVATA (MANTENUTA TEMPORANEAMENTE) ---
class Attivata(A_vista):
    
    elementi = models.ManyToManyField(
        Punteggio, 
        blank=True, 
        verbose_name="Elementi associati",
        through='AttivataElemento',
    )
    
    statistiche_base = models.ManyToManyField(
        Statistica,
        through='AttivataStatisticaBase',
        blank=True,
        verbose_name="Statistiche (Valori Base)",
        related_name='attivata_statistiche_base'
    )

    def __str__(self):
        return f"Attivata (LEGACY): {self.nome}"

    @property
    def livello(self):
        return self.elementi.count()

    @property
    def costo_crediti(self):
        """
        Calcola il costo in crediti (che qui è inteso come costo per attivazione/apprendimento?)
        basato sulla costante.
        """
        return self.livello * COSTO_PER_MATTONE

    @property
    def TestoFormattato(self):
        if not self.testo:
            return ""
        
        testo_formattato = self.testo
        stats_links = self.attivatastatisticabase_set.select_related('statistica').all()
        
        for link in stats_links:
            param = link.statistica.parametro
            valore = link.valore_base
            
            if param:
                testo_formattato = testo_formattato.replace(f"{{{param}}}", str(valore))
                
        return testo_formattato

class AttivataElemento(models.Model):
    attivata = models.ForeignKey(
        'Attivata', 
        on_delete=models.CASCADE
    )
    elemento = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE,
        limit_choices_to={'is_mattone': True}, # Aggiornato per includere Mattoni
        verbose_name="Elemento / Mattone"
    )

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

# --- NUOVE CLASSI: TECNICA, INFUSIONE, TESSITURA ---

class Tecnica(A_vista):
    """
    Classe base astratta per Infusioni e Tessiture.
    Inherita da A_vista (concreta) tramite Multi-table inheritance (implicita se non abstract)
    o usiamo A_vista come semplice mixin di campi se fosse astratta.
    Qui Tecnica è astratta ma eredita da A_vista Concreta. 
    """
    aura_richiesta = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE,
        limit_choices_to={'tipo': AURA},
        related_name="%(class)s_associate",
        verbose_name="Aura Requisito"
    )

    class Meta:
        abstract = True
        ordering = ['nome']

    @property
    def livello(self):
        return self.mattoni.count()

    @property
    def costo_crediti(self):
        return self.livello * COSTO_PER_MATTONE

class Infusione(Tecnica):
    aura_infusione = models.ForeignKey(
        Punteggio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'tipo': AURA, 'is_soprannaturale': True},
        related_name="infusioni_secondarie",
        verbose_name="Aura di Infusione (Secondaria)"
    )
    
    mattoni = models.ManyToManyField(
        Mattone,
        through='InfusioneMattone',
        verbose_name="Mattoni Componenti",
        related_name="infusioni_utilizzatrici"
    )
    
    statistiche_base = models.ManyToManyField(
        Statistica,
        through='InfusioneStatisticaBase',
        blank=True,
        verbose_name="Statistiche (Valori Base)",
        related_name='infusione_statistiche_base'
    )

    class Meta:
        verbose_name = "Infusione"
        verbose_name_plural = "Infusioni"

    @property
    def TestoFormattato(self):
        # Wrapper per admin
        txt = self.testo or ""
        # Logica parsing stat base locale
        for link in self.infusionestatisticabase_set.select_related('statistica').all():
             if link.statistica.parametro:
                 txt = txt.replace(f"{{{link.statistica.parametro}}}", str(link.valore_base))
        return txt

class Tessitura(Tecnica):
    formula = models.TextField(
        "Formula", 
        blank=True, null=True, 
        help_text="Parametri: {elem} (Elem. Principale), {rango} (Testo Rango). Usa anche statistiche pg."
    )
    elemento_principale = models.ForeignKey(
        Punteggio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'tipo': ELEMENTO},
        verbose_name="Elemento Principale"
    )
    
    mattoni = models.ManyToManyField(
        Mattone,
        through='TessituraMattone',
        verbose_name="Mattoni Componenti",
        related_name="tessiture_utilizzatrici"
    )

    statistiche_base = models.ManyToManyField(
        Statistica,
        through='TessituraStatisticaBase',
        blank=True,
        verbose_name="Statistiche (Valori Base)",
        related_name='tessitura_statistiche_base'
    )

    class Meta:
        verbose_name = "Tessitura"
        verbose_name_plural = "Tessiture"
    
    @property
    def TestoFormattato(self):
        txt = self.testo or ""
        # Parsing Stat Base
        for link in self.tessiturastatisticabase_set.select_related('statistica').all():
             if link.statistica.parametro:
                 txt = txt.replace(f"{{{link.statistica.parametro}}}", str(link.valore_base))
        
        # Parsing Elemento e Rango
        if self.elemento_principale:
            txt = txt.replace("{elem}", self.elemento_principale.nome)
        
        # Parsing Rango
        # Cerca statistica 'Rango' nelle stats base di questa tessitura
        rango_stat = self.tessiturastatisticabase_set.filter(statistica__nome__iexact="Rango").first()
        if rango_stat:
            txt = txt.replace("{rango}", get_testo_rango(rango_stat.valore_base))
            
        return txt


# --- Through Models Tecnica ---

class InfusioneMattone(models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=0)
    
class TessituraMattone(models.Model):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=0)

class InfusioneStatisticaBase(CondizioneStatisticaMixin):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)

class TessituraStatisticaBase(CondizioneStatisticaMixin):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)

    
class Manifesto(A_vista):

    def __str__(self):
        return f"Manifesto: {self.nome}"


class Inventario(A_vista):
    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventari"

    def __str__(self):
        return f"Inventario: {self.nome}"

    def get_oggetti(self, data=None):
        if data is None:
            data = timezone.now()
        
        return Oggetto.objects.filter(
            tracciamento_inventario__inventario=self,
            tracciamento_inventario__data_inizio__lte=data,
            tracciamento_inventario__data_fine__isnull=True
        )

class OggettoInInventario(models.Model):
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
        ordering = ['-data_inizio']

    def __str__(self):
        stato = "Attuale" if self.data_fine is None else f"Fino a {self.data_fine.strftime('%Y-%m-%d')}"
        return f"{self.oggetto.nome} in {self.inventario.nome} (Da {self.data_inizio.strftime('%Y-%m-%d')} - {stato})"


class TipologiaPersonaggio(models.Model):
    nome = models.CharField(max_length=100, unique=True, default="Standard")
    crediti_iniziali = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    caratteristiche_iniziali = models.IntegerField(
        default=8
    )
    giocante = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipologia Personaggio"
        verbose_name_plural = "Tipologie Personaggio"

    def __str__(self):
        return self.nome

def get_default_tipologia():
    tipologia, created = TipologiaPersonaggio.objects.get_or_create(
        nome="Standard" 
    )
    return tipologia.pk


class PuntiCaratteristicaMovimento(models.Model):
    personaggio = models.ForeignKey(
        'Personaggio',
        on_delete=models.CASCADE,
        related_name="movimenti_pc"
    )
    importo = models.IntegerField()
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Movimento Punti Caratteristica"
        verbose_name_plural = "Movimenti Punti Caratteristica"
        ordering = ['-data']

    def __str__(self):
        return f"{self.personaggio.nome}: {self.importo} PC ({self.descrizione})"


class Personaggio(Inventario):
    proprietario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="personaggi",
        null=True, 
        blank=True,
        help_text="L'account utente che controlla questo personaggio."
    )
    
    tipologia = models.ForeignKey(
        TipologiaPersonaggio,
        on_delete=models.PROTECT,
        related_name="personaggi",
        null=True, blank=True,
    )
    
    data_nascita = models.DateTimeField(default=timezone.now)
    data_morte = models.DateTimeField(null=True, blank=True)
    
    abilita_possedute = models.ManyToManyField(
        'Abilita',
        through='PersonaggioAbilita',
        blank=True
    )
    
    # LEGACY
    attivate_possedute = models.ManyToManyField(
        Attivata,
        through='PersonaggioAttivata',
        blank=True
    )
    
    # NEW
    infusioni_possedute = models.ManyToManyField(
        Infusione,
        through='PersonaggioInfusione',
        blank=True
    )
    tessiture_possedute = models.ManyToManyField(
        Tessitura,
        through='PersonaggioTessitura',
        blank=True
    )
    
    # --- Nuova Relazione M2M per i Modelli di Aura ---
    modelli_aura = models.ManyToManyField(
        ModelloAura,
        through='PersonaggioModelloAura',
        blank=True,
        verbose_name="Modelli di Aura"
    )

    class Meta:
        verbose_name = "Personaggio"
        verbose_name_plural = "Personaggi"

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.pk and self.tipologia is None:
            tipologia_standard, created = TipologiaPersonaggio.objects.get_or_create(
                nome="Standard"
            )
            self.tipologia = tipologia_standard
        
        super().save(*args, **kwargs)
        
    def aggiungi_log(self, testo_log):
        PersonaggioLog.objects.create(personaggio=self, testo_log=testo_log)
    
    def modifica_crediti(self, importo, descrizione):
        CreditoMovimento.objects.create(
            personaggio=self,
            importo=importo,
            descrizione=descrizione
        )

    def modifica_pc(self, importo, descrizione):
        PuntiCaratteristicaMovimento.objects.create(
            personaggio=self,
            importo=importo,
            descrizione=descrizione
        )

    @property
    def crediti(self):
        if not self.tipologia: # Fallback se la tipologia è None
             base = 0
        else:
             base = self.tipologia.crediti_iniziali
        movimenti = self.movimenti_credito.aggregate(totale=Sum('importo'))['totale'] or 0
        return base + movimenti
    
    @property
    def punti_caratteristica(self):
        if not self.tipologia: # Fallback se la tipologia è None
            base = 0
        else:
            base = self.tipologia.caratteristiche_iniziali
        movimenti = self.movimenti_pc.aggregate(totale=Sum('importo'))['totale'] or 0
        return base + movimenti
    
    @property
    def punteggi_base(self):
        """
        Calcola i valori base di TUTTI i punteggi (CA, AU, CU, ecc.)
        sommando i bonus 'punteggio_acquisito' dalle abilità possedute.
        Usa una cache.
        """
        if hasattr(self, '_punteggi_base_cache'):
            return self._punteggi_base_cache

        links = abilita_punteggio.objects.filter(
            abilita__personaggioabilita__personaggio=self
        ).select_related('punteggio')
        
        query_aggregata = links.values(
            'punteggio__nome' 
        ).annotate(
            valore_totale=Sum('valore') 
        ).order_by('punteggio__nome')
        
        punteggi = {
            item['punteggio__nome']: item['valore_totale'] 
            for item in query_aggregata
        }
            
        self._punteggi_base_cache = punteggi
        return self._punteggi_base_cache

    @property
    def caratteristiche_base(self):
        return {
            nome: val for nome, val in self.punteggi_base.items()
            if Punteggio.objects.filter(nome=nome, tipo=CARATTERISTICA).exists()
        }

    def get_valore_aura_effettivo(self, aura):
        """
        Calcola il valore dell'aura. Se è generica, prende il max delle altre.
        """
        punteggi = self.punteggi_base 
        
        if aura.is_generica:
            # Filtra solo le aure (escludendo la generica stessa per evitare loop se mal configurata)
            valori_aure = [
                val for nome, val in punteggi.items() 
                if Punteggio.objects.filter(nome=nome, tipo=AURA, is_generica=False).exists()
            ]
            return max(valori_aure) if valori_aure else 0
            
        return punteggi.get(aura.nome, 0)

    def valida_acquisto_tecnica(self, tecnica):
        """
        Verifica se il personaggio può acquistare la Infusione/Tessitura.
        Restituisce (Bool, MessaggioErrore).
        """
        # 1. Controllo Livello Tecnica vs Punteggio Aura
        livello_tecnica = tecnica.livello
        if not tecnica.aura_richiesta:
             return False, "Tecnica senza Aura richiesta."
             
        valore_aura = self.get_valore_aura_effettivo(tecnica.aura_richiesta)
        
        if livello_tecnica > valore_aura:
            return False, f"Livello tecnica ({livello_tecnica}) supera il tuo punteggio in {tecnica.aura_richiesta.nome} ({valore_aura})."

        # 2. Controllo Mattoni (Count vs Caratteristica Relativa)
        # Conta quanti mattoni di ogni tipo ci sono
        from collections import Counter
        mattoni_ids = tecnica.mattoni.values_list('id', flat=True)
        counter_mattoni = Counter(mattoni_ids)
        
        caratteristiche_pg = self.caratteristiche_base
        
        for mattone_id, count in counter_mattoni.items():
            try:
                mattone = Mattone.objects.get(pk=mattone_id)
                carat_nome = mattone.caratteristica_associata.nome
                valore_carat = caratteristiche_pg.get(carat_nome, 0)
                
                if count > valore_carat:
                    return False, f"La tecnica richiede {count}x {mattone.nome}, ma hai solo {valore_carat} in {carat_nome}."
            except Mattone.DoesNotExist:
                continue

        # 3. Controllo Modello di Aura (Subset Mattoni)
        # Cerca se il PG ha un modello per l'aura richiesta
        modello = self.modelli_aura.filter(aura=tecnica.aura_richiesta).first()
        
        if modello:
            # Se ha un modello, la tecnica DEVE usare SOLO mattoni non proibiti?
            # La logica del modello è restrittiva: "solo tessiture con mattoni dello specifico subset"
            # Quindi dobbiamo vedere se TUTTI i mattoni della tecnica SONO nel subset, o se NON sono nei proibiti.
            # Implementazione basata su "mattoni_proibiti" nel modello:
            mattoni_tecnica = set(mattoni_ids)
            mattoni_proibiti = set(modello.mattoni_proibiti.values_list('id', flat=True))
            
            intersezione = mattoni_tecnica.intersection(mattoni_proibiti)
            if intersezione:
                 nomi_proibiti = ", ".join([m.nome for m in Mattone.objects.filter(id__in=intersezione)])
                 return False, f"Il tuo modello di aura ({modello.nome}) ti vieta l'uso di: {nomi_proibiti}."

        return True, "Acquisto valido."

    @property
    def modificatori_calcolati(self):
        """
        [CALCOLO 2 - AGGIORNATO]
        Include i Metatalenti (da ModelloAura e Mattoni proibiti).
        """
        if hasattr(self, '_modificatori_calcolati_cache'):
            return self._modificatori_calcolati_cache

        mods = {} 
        
        def _add_mod(stat_parametro, tipo, valore): 
            if not stat_parametro: return
                
            if stat_parametro not in mods:
                mods[stat_parametro] = {'add': 0, 'mol': 1.0}
            
            if tipo == MODIFICATORE_ADDITIVO:
                mods[stat_parametro]['add'] += valore
            elif tipo == MODIFICATORE_MOLTIPLICATIVO:
                mods[stat_parametro]['mol'] *= float(valore) 

        # 1. Bonus da Abilità possedute
        bonus_abilita = AbilitaStatistica.objects.filter(
            abilita__personaggioabilita__personaggio=self
        ).select_related('statistica')
        
        for link in bonus_abilita:
            _add_mod(link.statistica.parametro, link.tipo_modificatore, link.valore)

        # 2. Bonus da Oggetti posseduti (nell'inventario)
        bonus_oggetti = OggettoStatistica.objects.filter(
            oggetto__tracciamento_inventario__inventario=self.inventario_ptr,
            oggetto__tracciamento_inventario__data_fine__isnull=True
        ).select_related('statistica')
        
        for link in bonus_oggetti:
            _add_mod(link.statistica.parametro, link.tipo_modificatore, link.valore)

        caratteristiche_base = self.caratteristiche_base 
        
        # 3. Bonus da Caratteristiche base
        if caratteristiche_base:
            links_caratteristiche = CaratteristicaModificatore.objects.filter(
                caratteristica__nome__in=caratteristiche_base.keys()
            ).select_related('caratteristica', 'statistica_modificata')
            
            for link in links_caratteristiche:
                nome_caratteristica = link.caratteristica.nome
                punti_caratteristica = caratteristiche_base.get(nome_caratteristica, 0)
                
                if punti_caratteristica > 0 and link.ogni_x_punti > 0:
                    bonus = (punti_caratteristica // link.ogni_x_punti) * link.modificatore
                    if bonus > 0:
                        _add_mod(link.statistica_modificata.parametro, MODIFICATORE_ADDITIVO, bonus)

        # 4. Bonus da Metatalenti (Mattoni Proibiti nei Modelli Aura)
        # Recuperiamo tutti i modelli aura associati
        # NOTA: I modificatori specifici delle Attivate derivanti dai Metatalenti non vengono
        # aggiunti ai modificatori globali del personaggio qui, ma calcolati dentro `get_testo_formattato_per_item`
        
        self._modificatori_calcolati_cache = mods
        return self._modificatori_calcolati_cache
    
    def _processa_placeholder(self, match, mods, base_stats):
        """
        Metodo helper per calcolare un'espressione come {pv+pf-des}.
        """
        try:
            espressione = match.group(1).strip()
            tokens = re.split(r'([+\-])', espressione) 
            total = 0
            current_op = '+'

            for token in tokens:
                token = token.strip()
                if not token: continue

                if token in ['+', '-']:
                    current_op = token
                else:
                    valore_base = base_stats.get(token, 0)
                    stat_mods = mods.get(token, {'add': 0, 'mol': 1.0})
                    valore_finale = (valore_base + stat_mods['add']) * stat_mods['mol']
                    
                    if current_op == '+': total += valore_finale
                    elif current_op == '-': total -= valore_finale
                        
            return str(round(total, 2))
        except Exception:
            return match.group(0)

    
    def get_testo_formattato_per_item(self, item):
        """
        [CALCOLO 3 - RISCRITTO PER METATALENTI]
        Calcola il testo formattato applicando Metatalenti e Parsing variabili.
        Supporta Oggetto, Infusione, Tessitura, Attivata (Legacy).
        """
        if not item: return ""
        
        testo_base = item.testo if item.testo else ""
        
        is_infusione = isinstance(item, Infusione)
        is_tessitura = isinstance(item, Tessitura)
        is_attivata_old = isinstance(item, Attivata)
        is_tecnica = is_infusione or is_tessitura
        
        mods_personaggio = self.modificatori_calcolati
        
        # Cloniamo i mods per non sporcare la cache globale se aggiungiamo bonus locali
        import copy
        mods_attivi = copy.deepcopy(mods_personaggio)

        links_base = []
        statistiche_metatalento_text = ""
        
        aura_riferimento = None
        livello_item = 0
        
        if isinstance(item, Oggetto):
            links_base = item.oggettostatisticabase_set.select_related('statistica').all()
            aura_riferimento = item.aura
            livello_item = item.livello
            
        elif is_tecnica:
            if is_infusione:
                links_base = item.infusionestatisticabase_set.select_related('statistica').all()
            else:
                links_base = item.tessiturastatisticabase_set.select_related('statistica').all()
            
            aura_riferimento = item.aura_richiesta
            livello_item = item.livello
            
        elif is_attivata_old:
            links_base = item.attivatastatisticabase_set.select_related('statistica').all()
            # Logica legacy: cerca di dedurre l'aura dal primo elemento
            primo_elemento = item.elementi.first()
            if primo_elemento:
                 try:
                     # Assumiamo che l'elemento sia un Mattone o abbia relazione con Aura
                     # Se Punteggio ha relazione 'mattoni_aura', potremmo risalire
                     if hasattr(primo_elemento, 'mattone'): 
                        aura_riferimento = primo_elemento.mattone.aura
                     else:
                        # Fallback se Mattone è una sottoclasse di Punteggio ma non linkato direttamente
                        # In questo modello Mattone eredita da Punteggio.
                        try:
                            m = Mattone.objects.get(pk=primo_elemento.pk)
                            aura_riferimento = m.aura
                        except Mattone.DoesNotExist:
                            pass
                 except: pass
            livello_item = item.livello
            
        # --- LOGICA METATALENTI ---
        if aura_riferimento:
            modello = self.modelli_aura.filter(aura=aura_riferimento).first()
            if modello:
                for mattone in modello.mattoni_proibiti.all():
                    funzionamento = mattone.funzionamento_metatalento
                    if funzionamento == META_NESSUN_EFFETTO:
                        continue
                    
                    nome_caratt = mattone.caratteristica_associata.nome
                    valore_caratt = self.caratteristiche_base.get(nome_caratt, 0)
                    
                    applica_effetto = False
                    if funzionamento in [META_VALORE_PUNTEGGIO, META_SOLO_TESTO]:
                        applica_effetto = True
                    elif funzionamento == META_LIVELLO_INFERIORE:
                        if livello_item <= valore_caratt:
                            applica_effetto = True
                    
                    if applica_effetto:
                        # A. Modifica Statistiche (Se previsto)
                        if funzionamento in [META_VALORE_PUNTEGGIO, META_LIVELLO_INFERIORE]:
                            stats_mattone = MattoneStatistica.objects.filter(mattone=mattone).select_related('statistica')
                            for stat_m in stats_mattone:
                                param = stat_m.statistica.parametro
                                bonus = stat_m.valore * valore_caratt # Moltiplicato per caratteristica
                                
                                if param:
                                    if param not in mods_attivi:
                                        mods_attivi[param] = {'add': 0, 'mol': 1.0}
                                    
                                    if stat_m.tipo_modificatore == MODIFICATORE_ADDITIVO:
                                        mods_attivi[param]['add'] += bonus
                                    elif stat_m.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO:
                                        mods_attivi[param]['mol'] *= float(bonus)

                        # B. Testo Addizionale
                        txt_add = mattone.testo_addizionale
                        if txt_add:
                            def replace_caratt(match):
                                moltiplicatore = match.group(1)
                                molt_val = int(moltiplicatore) if moltiplicatore else 1
                                return str(valore_caratt * molt_val)
                            
                            txt_add_parsed = re.sub(r'\{(?:(\d+)\*)?caratt\}', replace_caratt, txt_add)
                            statistiche_metatalento_text += f"\n<br><em>Metatalento ({mattone.nome}):</em> {txt_add_parsed}"

        # Concatena testo base + testo metatalenti
        testo_completo = testo_base + statistiche_metatalento_text
        
        # Parsing Extra per Tessiture (Rango, Elem)
        if is_tessitura:
             if item.elemento_principale:
                 testo_completo = testo_completo.replace("{elem}", item.elemento_principale.nome)
             # Rango
             rango_stat = next((l for l in links_base if l.statistica.nome.lower() == "rango"), None)
             if rango_stat:
                 testo_completo = testo_completo.replace("{rango}", get_testo_rango(rango_stat.valore_base))

        base_stats = {
            link.statistica.parametro: link.valore_base 
            for link in links_base 
            if link.statistica.parametro
        }

        # Risoluzione finale placeholder
        testo_finale = re.sub(
            r'\{([^{}]+)\}', 
            lambda match: self._processa_placeholder(match, mods_attivi, base_stats), 
            testo_completo
        )
            
        return testo_finale

# --- 2. MODELLI "THROUGH" PER PERSONAGGIO ---
class PersonaggioAbilita(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

class PersonaggioAttivata(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

class PersonaggioInfusione(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

class PersonaggioTessitura(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

class PersonaggioModelloAura(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    modello_aura = models.ForeignKey(ModelloAura, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Personaggio - Modello Aura"
        verbose_name_plural = "Personaggio - Modelli Aura"
        
    def clean(self):
        # Verifica che il personaggio non abbia già un modello per questa Aura
        aura_target = self.modello_aura.aura
        esistente = PersonaggioModelloAura.objects.filter(
            personaggio=self.personaggio,
            modello_aura__aura=aura_target
        ).exclude(pk=self.pk)
        
        if esistente.exists():
            raise ValidationError(f"Il personaggio ha già un modello associato per l'aura {aura_target.nome}.")
            
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


# --- 3. MODELLI DI LOG E CREDITI ---
class PersonaggioLog(models.Model):
    personaggio = models.ForeignKey(
        Personaggio, 
        on_delete=models.CASCADE,
        related_name="log_eventi"
    )
    data = models.DateTimeField(default=timezone.now)
    testo_log = models.TextField()

    class Meta:
        verbose_name = "Log Evento Personaggio"
        verbose_name_plural = "Log Eventi Personaggio"
        ordering = ['-data']

class CreditoMovimento(models.Model):
    personaggio = models.ForeignKey(
        Personaggio,
        on_delete=models.CASCADE,
        related_name="movimenti_credito"
    )
    importo = models.DecimalField(max_digits=10, decimal_places=2)
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Movimento Crediti"
        verbose_name_plural = "Movimenti Crediti"
        ordering = ['-data']

# --- 4. MODELLO PER TRANSAZIONI SOSPESE ---
STATO_TRANSAZIONE_IN_ATTESA = 'IN_ATTESA'
STATO_TRANSAZIONE_ACCETTATA = 'ACCETTATA'
STATO_TRANSAZIONE_RIFIUTATA = 'RIFIUTATA'
STATO_TRANSAZIONE_CHOICES = [
    (STATO_TRANSAZIONE_IN_ATTESA, 'In Attesa'),
    (STATO_TRANSAZIONE_ACCETTATA, 'Accettata'),
    (STATO_TRANSAZIONE_RIFIUTATA, 'Rifiutata'),
]

class TransazioneSospesa(models.Model):
    oggetto = models.ForeignKey(
        'Oggetto', 
        on_delete=models.CASCADE
    )
    mittente = models.ForeignKey(
        Inventario, 
        on_delete=models.CASCADE,
        related_name="transazioni_in_uscita_sospese"
    )
    richiedente = models.ForeignKey(
        Personaggio, 
        on_delete=models.CASCADE,
        related_name="transazioni_in_entrata_sospese"
    )
    data_richiesta = models.DateTimeField(default=timezone.now)
    stato = models.CharField(
        max_length=10,
        choices=STATO_TRANSAZIONE_CHOICES,
        default=STATO_TRANSAZIONE_IN_ATTESA
    )
    
    class Meta:
        verbose_name = "Transazione Sospesa"
        verbose_name_plural = "Transazioni Sospese"
        ordering = ['-data_richiesta']

    def accetta(self):
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA:
            raise Exception("Transazione già processata.")
        
        self.oggetto.sposta_in_inventario(self.richiedente) 
        self.stato = STATO_TRANSAZIONE_ACCETTATA
        self.save()
        
        self.richiedente.aggiungi_log(f"Ricevuto {self.oggetto.nome} da {self.mittente.nome}.")
        if hasattr(self.mittente, 'personaggio'):
            if isinstance(self.mittente, Personaggio):
                self.mittente.aggiungi_log(f"Consegnato {self.oggetto.nome} a {self.richiedente.nome}.")
            elif hasattr(self.mittente, 'personaggio'):
                self.mittente.personaggio.aggiungi_log(f"Consegnato {self.oggetto.nome} a {self.richiedente.nome}.")

    def rifiuta(self):
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA:
            raise Exception("Transazione già processata.")
        
        self.stato = STATO_TRANSAZIONE_RIFIUTATA
        self.save()
        self.richiedente.aggiungi_log(f"Richiesta per {self.oggetto.nome} da {self.mittente.nome} rifiutata.")
        

def generate_short_id(length=14):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# through

class OggettoElemento(models.Model):
    oggetto = models.ForeignKey(
        'Oggetto', 
        on_delete=models.CASCADE
    )
    elemento = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE,
        limit_choices_to={'tipo': ELEMENTO}, 
        verbose_name="Elemento"
    )
    
class OggettoStatistica(CondizioneStatisticaMixin):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(
        Statistica, 
        on_delete=models.CASCADE
    )
    valore = models.IntegerField(default=0)
    
    tipo_modificatore = models.CharField(
        max_length=3,
        choices=MODIFICATORE_CHOICES,
        default=MODIFICATORE_ADDITIVO
    )

    class Meta:
        unique_together = ('oggetto', 'statistica')

    def __str__(self):
        return f"{self.oggetto.nome} - {self.statistica.nome}: {self.valore}"

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


# abstract

class QrCode(models.Model):
    id = models.CharField(
        primary_key=True,
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
        if self._state.adding:
            while True:
                try:
                    super().save(*args, **kwargs)
                    break
                except IntegrityError:
                    self.id = generate_short_id()
        else:
            super().save(*args, **kwargs)

class Oggetto(A_vista):
    elementi = models.ManyToManyField(
        Punteggio, 
        blank=True, 
        verbose_name="Elementi associati",
        through='OggettoElemento',
    )
    statistiche = models.ManyToManyField(
        Statistica,
        through='OggettoStatistica',
        blank=True,
        verbose_name="Statistiche modificate", 
        related_name = "oggetti_statistiche",
    )
    
    statistiche_base = models.ManyToManyField(
        Statistica,
        through='OggettoStatisticaBase',
        blank=True,
        verbose_name="Statistiche (Valori Base)",
        related_name='oggetti_statistiche_base'
    )
    
    aura = models.ForeignKey(Punteggio, blank=True, null=True, on_delete=models.SET_NULL, limit_choices_to={'tipo' : AURA}, verbose_name="Aura associata", related_name="oggetti_aura")

    def elementi_list(self):
        return ", ".join(str(elemento) for elemento in self.elementi.all())

    def __str__(self):
        return f"{self.nome} ({self.aura.sigla if self.aura else 'Nessuna Aura'})"
    
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
                testo_formattato = re.sub(r'\{' + re.escape(param) + r'\}', str(valore), testo_formattato)
        return testo_formattato
    
    @property
    def inventario_corrente(self):
        tracciamento_attuale = self.tracciamento_inventario.filter(
            data_fine__isnull=True
        ).first()
        
        return tracciamento_attuale.inventario if tracciamento_attuale else None

    def sposta_in_inventario(self, nuovo_inventario, data_spostamento=None):
        """
        Metodo principale per spostare un oggetto in un nuovo inventario.
        """
        if data_spostamento is None:
            data_spostamento = timezone.now()

        with transaction.atomic():
            tracciamento_attuale = self.tracciamento_inventario.filter(
                data_fine__isnull=True
            ).first()
            
            if tracciamento_attuale:
                if tracciamento_attuale.inventario == nuovo_inventario:
                    return 
                
                tracciamento_attuale.data_fine = data_spostamento
                tracciamento_attuale.save()

            if nuovo_inventario is not None:
                OggettoInInventario.objects.create(
                    oggetto=self,
                    inventario=nuovo_inventario,
                    data_inizio=data_spostamento
                )

# --- MESSAGING MODELS ---

class Gruppo(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    membri = models.ManyToManyField('Personaggio', related_name="gruppi_appartenenza", blank=True)
    
    class Meta:
        verbose_name = "Gruppo di Personaggi"
        verbose_name_plural = "Gruppi di Personaggi"
    
    def __str__(self):
        return self.nome

class Messaggio(models.Model):
    TIPO_BROADCAST = 'BROAD'
    TIPO_GRUPPO = 'GROUP'
    TIPO_INDIVIDUALE = 'INDV'
    TIPO_CHOICES = [
        (TIPO_BROADCAST, 'Broadcast (Tutti)'),
        (TIPO_GRUPPO, 'Gruppo'),
        (TIPO_INDIVIDUALE, 'Individuale'),
    ]
    
    mittente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="messaggi_inviati")
    tipo_messaggio = models.CharField(max_length=5, choices=TIPO_CHOICES, default=TIPO_BROADCAST)
    
    destinatario_personaggio = models.ForeignKey('Personaggio', on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_individuali")
    destinatario_gruppo = models.ForeignKey(Gruppo, on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_gruppo")
    
    titolo = models.CharField(max_length=150)
    testo = models.TextField()
    data_invio = models.DateTimeField(default=timezone.now)
    
    # Flag per la cronologia/notifica
    salva_in_cronologia = models.BooleanField(default=True, help_text="Se disattivato, il messaggio non appare nella cronologia pubblica del gioco.")
    
    class Meta:
        verbose_name = "Messaggio"
        verbose_name_plural = "Messaggi Inviati"
        ordering = ['-data_invio']
        
    def __str__(self):
        dest = self.destinatario_personaggio or self.destinatario_gruppo or "Tutti"
        return f"[{self.get_tipo_messaggio_display()}] {self.titolo} a {dest}"


# --- MODELLI PER I PLUGIN CMS ---

class AbilitaPluginModel(CMSPlugin):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)

    def __str__(self):
        return self.abilita.nome

class OggettoPluginModel(CMSPlugin):
    oggetto = models.ForeignKey(Oggetto, on_delete=models.CASCADE)

    def __str__(self):
        return self.oggetto.nome

class AttivataPluginModel(CMSPlugin):
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE)

    def __str__(self):
        return self.attivata.nome        

class InfusionePluginModel(CMSPlugin):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)

    def __str__(self):
        return self.infusione.nome   

class TessituraPluginModel(CMSPlugin):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)

    def __str__(self):
        return self.tessitura.nome      

class TabellaPluginModel(CMSPlugin):
    tabella = models.ForeignKey(Tabella, on_delete = models.CASCADE)
    
    def __str__(self):
        return "{tabella}".format(tabella = self.tabella.nome)

class TierPluginModel(CMSPlugin):
    tier = models.ForeignKey(Tier, on_delete = models.CASCADE, related_name='cms_kor_tier_plugin')
    
    def __str__(self):
        return "{tier}".format(tier = self.tier.nome)