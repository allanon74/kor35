from django.db.models import Sum, F, Count
import re
import secrets
import string
import copy
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

# --- COSTANTI TRANSAZIONI ---
STATO_TRANSAZIONE_IN_ATTESA = 'IN_ATTESA'
STATO_TRANSAZIONE_ACCETTATA = 'ACCETTATA'
STATO_TRANSAZIONE_RIFIUTATA = 'RIFIUTATA'
STATO_TRANSAZIONE_CHOICES = [
    (STATO_TRANSAZIONE_IN_ATTESA, 'In Attesa'),
    (STATO_TRANSAZIONE_ACCETTATA, 'Accettata'),
    (STATO_TRANSAZIONE_RIFIUTATA, 'Rifiutata'),
]

# --- FUNZIONE RANGO AGGIORNATA ---
def get_testo_rango(valore):
    try:
        valore = int(valore)
    except (ValueError, TypeError):
        return ""

    if valore <= 0: return "Mondano! "
    elif valore == 1: return "" 
    elif valore == 2: return "Eroico! "
    elif valore == 3: return "Leggendario! "
    elif valore == 4: return "Mitologico! "
    elif valore == 5: return "Divino! "
    elif valore == 6: return "Cosmico! "
    else: 
        n = valore - 6
        return f"Cosmico {n}-esimo! "

def _get_icon_color_from_bg(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminanza = ((r * 299) + (g * 587) + (b * 114)) / 1000
        return 'black' if luminanza > 128 else 'white'
    except Exception:
        return 'black'

def generate_short_id(length=14):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# --- TIPI GENERICI ---
CARATTERISTICA="CA"; STATISTICA="ST"; ELEMENTO="EL"; AURA="AU"; CONDIZIONE="CO"; CULTO="CU"; VIA="VI"; ARTE="AR"; ARCHETIPO="AR"
punteggi_tipo = [(CARATTERISTICA,'Caratteristica'),(STATISTICA,'Statistica'),(ELEMENTO,'Elemento'),(AURA,'Aura'),(CONDIZIONE,'Condizione'),(CULTO,'Culto'),(VIA,'Via'),(ARTE,'Arte'),(ARCHETIPO,'Archetipo')]
TIER_1="T1"; TIER_2="T2"; TIER_3="T3"; TIER_4="T4"
tabelle_tipo = [(TIER_1,'Tier 1'),(TIER_2,'Tier 2'),(TIER_3,'Tier 3'),(TIER_4,'Tier 4')]
MODIFICATORE_ADDITIVO='ADD'; MODIFICATORE_MOLTIPLICATIVO='MOL'
MODIFICATORE_CHOICES = [(MODIFICATORE_ADDITIVO,'Additivo (+N)'),(MODIFICATORE_MOLTIPLICATIVO,'Moltiplicativo (xN)')]
META_NESSUN_EFFETTO='NE'; META_VALORE_PUNTEGGIO='VP'; META_SOLO_TESTO='TX'; META_LIVELLO_INFERIORE='LV'
METATALENTO_CHOICES = [(META_NESSUN_EFFETTO,'Nessun Effetto'),(META_VALORE_PUNTEGGIO,'Valore per Punteggio'),(META_SOLO_TESTO,'Solo Testo Addizionale'),(META_LIVELLO_INFERIORE,'Solo abilità con livello pari o inferiore')]

# --- CORE: FUNZIONE GENERALE DI FORMATTAZIONE ---
def formatta_testo_generico(testo, formula=None, statistiche_base=None, personaggio=None, context=None):
    """
    Funzione universale per la formattazione dei testi con parametri.
    """
    testo_out = testo or ""
    formula_out = formula or ""
    
    if not testo_out and not formula_out:
        return ""

    # 1. Normalizzazione Statistiche Base
    base_values = {}
    if statistiche_base:
        for item in statistiche_base:
            param = getattr(item.statistica, 'parametro', None) if hasattr(item, 'statistica') else None
            val = getattr(item, 'valore_base', 0)
            if param:
                base_values[param] = val

    # 2. Calcolo Modificatori
    mods_attivi = {}
    testo_metatalenti = ""
    
    # A. Globali Personaggio (se presente)
    if personaggio:
        mods_attivi = copy.deepcopy(personaggio.modificatori_calcolati)

    # B. Modificatori Locali dell'Item (Condizionali)
    # Si applicano sempre al calcolo del testo dell'oggetto stesso, verificando le condizioni interne
    if context:
        item_modifiers = context.get('item_modifiers', [])
        current_aura = context.get('aura')
        current_elem = context.get('elemento')

        for mod in item_modifiers:
            # Verifica Condizione Aura
            passa_aura = True
            if mod.usa_limitazione_aura:
                if not current_aura:
                     passa_aura = False 
                else:
                     # Verifica se l'aura corrente è tra quelle permesse
                     # Nota: limit_a_aure è M2M. Se siamo in un loop di oggetti, questo potrebbe fare query extra
                     # ma per un singolo oggetto (dettaglio) è accettabile.
                     if not mod.limit_a_aure.filter(pk=current_aura.pk).exists():
                         passa_aura = False
            
            # Verifica Condizione Elemento
            passa_elem = True
            if mod.usa_limitazione_elemento:
                if not current_elem:
                    passa_elem = False
                else:
                    if not mod.limit_a_elementi.filter(pk=current_elem.pk).exists():
                        passa_elem = False

            if passa_aura and passa_elem:
                p = mod.statistica.parametro
                if p:
                    if p not in mods_attivi: mods_attivi[p] = {'add': 0, 'mol': 1.0}
                    
                    if mod.tipo_modificatore == MODIFICATORE_ADDITIVO:
                        mods_attivi[p]['add'] += mod.valore
                    elif mod.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO:
                        mods_attivi[p]['mol'] *= float(mod.valore)

    # C. Logica Metatalenti (Solo se c'è personaggio e Aura di riferimento)
    if personaggio and context:
        aura_riferimento = context.get('aura')
        livello_item = context.get('livello', 0)
        
        if aura_riferimento:
            modello = personaggio.modelli_aura.filter(aura=aura_riferimento).first()
            if modello:
                caratteristiche_pg = personaggio.caratteristiche_base
                for mattone in modello.mattoni_proibiti.all():
                    funzionamento = mattone.funzionamento_metatalento
                    if funzionamento == META_NESSUN_EFFETTO: continue 
                    
                    nome_caratt = mattone.caratteristica_associata.nome
                    valore_caratt = caratteristiche_pg.get(nome_caratt, 0)
                    
                    applica = False
                    if funzionamento in [META_VALORE_PUNTEGGIO, META_SOLO_TESTO]: applica = True
                    elif funzionamento == META_LIVELLO_INFERIORE and livello_item <= valore_caratt: applica = True
                    
                    if applica:
                        if funzionamento in [META_VALORE_PUNTEGGIO, META_LIVELLO_INFERIORE]:
                            for stat_m in mattone.mattonestatistica_set.select_related('statistica').all():
                                param = stat_m.statistica.parametro
                                bonus = stat_m.valore * valore_caratt
                                if param:
                                    if param not in mods_attivi: mods_attivi[param] = {'add': 0, 'mol': 1.0}
                                    if stat_m.tipo_modificatore == MODIFICATORE_ADDITIVO: mods_attivi[param]['add'] += bonus
                                    elif stat_m.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO: mods_attivi[param]['mol'] *= float(bonus)

                        txt_add = mattone.testo_addizionale
                        if txt_add:
                            def replace_caratt(match):
                                m = match.group(1)
                                val = int(m) if m else 1
                                return str(valore_caratt * val)
                            txt_add_parsed = re.sub(r'\{(?:(\d+)\*)?caratt\}', replace_caratt, txt_add)
                            testo_metatalenti += f"<br><em>Metatalento ({mattone.nome}):</em> {txt_add_parsed}"

    # 3. Risoluzione Placeholder
    def resolve_placeholder(match):
        try:
            expr = match.group(1).strip()
            tokens = re.split(r'([+\-])', expr) 
            total = 0; current_op = '+'
            for token in tokens:
                token = token.strip()
                if not token: continue
                if token in ['+', '-']: current_op = token
                else:
                    base = base_values.get(token, 0)
                    mods = mods_attivi.get(token, {'add': 0, 'mol': 1.0})
                    val = (base + mods['add']) * mods['mol']
                    if current_op == '+': total += val
                    elif current_op == '-': total -= val
            return str(round(total, 2))
        except: return match.group(0)

    testo_completo = testo_out + testo_metatalenti
    
    # 4. Parametri Speciali
    if context:
        if 'elemento' in context and context['elemento']:
            nome_elem = context['elemento'].nome
            testo_completo = testo_completo.replace("{elem}", nome_elem)
            formula_out = formula_out.replace("{elem}", nome_elem)
        
        rango_val = base_values.get('rango')
        if rango_val is None and statistiche_base:
             r_obj = next((x for x in statistiche_base if x.statistica.nome.lower() == "rango"), None)
             if r_obj: rango_val = r_obj.valore_base
        
        if rango_val is not None:
             rango_txt = get_testo_rango(rango_val)
             testo_completo = testo_completo.replace("{rango}", rango_txt)
             formula_out = formula_out.replace("{rango}", rango_txt)

    testo_finale = re.sub(r'\{([^{}]+)\}', resolve_placeholder, testo_completo)
    formula_finale = re.sub(r'\{([^{}]+)\}', resolve_placeholder, formula_out)
    
    # 5. Output (Testo PRIMA, Formula DOPO)
    html_parts = []
    if testo_finale: html_parts.append(testo_finale)
    if formula_finale:
        if testo_finale: html_parts.append("<br/><hr style='margin:5px 0; border:0; border-top:1px dashed #ccc;'/>")
        html_parts.append(f"<strong>Formula:</strong> {formula_finale}")
        
    return "".join(html_parts)


# --- CLASSI ASTRATTE ---
class A_modello(models.Model):
    id = models.AutoField("Codice Identificativo", primary_key=True)
    class Meta: abstract = True
class A_vista(models.Model):
    id = models.AutoField(primary_key=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=100)
    testo = models.TextField(blank=True, null=True)
    def __str__(self): return f"{self.nome} ({self.id})"
    class Meta: ordering=['-data_creazione']; verbose_name="Elemento dell'Oggetto"; verbose_name_plural="Elementi dell'Oggetto"

class CondizioneStatisticaMixin(models.Model):
    # Flag per attivare le condizioni
    usa_limitazione_aura = models.BooleanField("Usa Limitazione Aura", default=False)
    limit_a_aure = models.ManyToManyField('Punteggio', blank=True, limit_choices_to={'tipo': AURA}, related_name="%(class)s_limit_aure", verbose_name="Aure consentite")
    
    usa_limitazione_elemento = models.BooleanField("Usa Limitazione Elemento", default=False)
    limit_a_elementi = models.ManyToManyField('Punteggio', blank=True, limit_choices_to={'tipo': ELEMENTO}, related_name="%(class)s_limit_elementi", verbose_name="Elementi consentiti")
    
    class Meta: abstract = True

# --- CORE MODELS ---
class Tabella(A_modello):
    nome = models.CharField(max_length=90)
    descrizione = models.TextField(null=True, blank=True)
    class Meta: verbose_name="Tabella"; verbose_name_plural="Tabelle"
    def __str__(self): return self.nome

class Tier(Tabella):
    tipo = models.CharField(choices=tabelle_tipo, max_length=2)
    foto = models.ImageField(upload_to='tiers/', null=True, blank=True)
    class Meta: verbose_name="Tier"; verbose_name_plural="Tiers"

class Punteggio(Tabella):
    sigla = models.CharField(max_length=3, unique=True)
    tipo = models.CharField(choices=punteggi_tipo, max_length=2)
    colore = ColorField(default='#1976D2')
    icona = CustomIconField(blank=True)
    ordine = models.IntegerField(default=0)
    is_mattone = models.BooleanField(default=False)
    is_soprannaturale = models.BooleanField(default=False)
    is_generica = models.BooleanField(default=False)
    permette_infusioni = models.BooleanField(default=False)
    permette_tessiture = models.BooleanField(default=False)
    caratteristica_relativa = models.ForeignKey("Punteggio", on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, null=True, blank=True, related_name="punteggi_caratteristica")
    modifica_statistiche = models.ManyToManyField('Statistica', through='CaratteristicaModificatore', related_name='modificata_da_caratteristiche', blank=True)
    class Meta: verbose_name="Punteggio"; verbose_name_plural="Punteggi"; ordering=['tipo', 'ordine', 'nome']
    @property
    def icona_url(self): return f"{settings.MEDIA_URL}{self.icona}" if self.icona else None
    def __str__(self): return f"{self.tipo} - {self.nome}"
    # Metodi grafici omessi

class Caratteristica(Punteggio):
    class Meta: proxy=True; verbose_name="Caratteristica (Gestione)"; verbose_name_plural="Caratteristiche (Gestione)"

class Statistica(Punteggio):
    parametro = models.CharField(max_length=10, unique=True, blank=True, null=True)
    valore_predefinito = models.IntegerField(default=0)
    valore_base_predefinito = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    is_primaria = models.BooleanField(default=False)
    def save(self, *args, **kwargs): self.tipo = STATISTICA; super().save(*args, **kwargs)
    class Meta: verbose_name="Statistica"; verbose_name_plural="Statistiche"

class Mattone(Punteggio):
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="mattoni_aura")
    caratteristica_associata = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, related_name="mattoni_caratteristica")
    descrizione_mattone = models.TextField(blank=True, null=True)
    descrizione_metatalento = models.TextField(blank=True, null=True)
    testo_addizionale = models.TextField(blank=True, null=True)
    funzionamento_metatalento = models.CharField(max_length=2, choices=METATALENTO_CHOICES, default=META_NESSUN_EFFETTO)
    statistiche = models.ManyToManyField(Statistica, through='MattoneStatistica', blank=True, related_name="mattoni_statistiche")
    def save(self, *args, **kwargs): self.is_mattone = True; super().save(*args, **kwargs)
    class Meta: verbose_name="Mattone"; verbose_name_plural="Mattoni"; unique_together=('aura', 'caratteristica_associata')

class MattoneStatistica(models.Model):
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: unique_together=('mattone', 'statistica')

class Aura(Punteggio):
    class Meta: proxy=True; verbose_name="Aura (Gestione)"; verbose_name_plural="Aure (Gestione)"
    def save(self, *args, **kwargs): self.type = AURA; super().save(*args, **kwargs)

class ModelloAura(models.Model):
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="modelli_definiti")
    nome = models.CharField(max_length=100)
    mattoni_proibiti = models.ManyToManyField(Mattone, blank=True, related_name="proibiti_in_modelli")
    def __str__(self): return f"{self.nome} ({self.aura.nome})"
    class Meta: verbose_name="Modello di Aura"; verbose_name_plural="Modelli di Aura"

class CaratteristicaModificatore(models.Model):
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, related_name="modificatori_dati")
    statistica_modificata = models.ForeignKey(Statistica, on_delete=models.CASCADE, related_name="modificatori_ricevuti")
    modificatore = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    ogni_x_punti = models.IntegerField(default=1)
    class Meta: unique_together=('caratteristica', 'statistica_modificata')

class AbilitaStatistica(CondizioneStatisticaMixin): # Modifiers (Mixin)
    abilita = models.ForeignKey('Abilita', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    valore = models.IntegerField(default=0)
    class Meta: unique_together=('abilita', 'statistica')

class Abilita(A_modello):
    nome = models.CharField(max_length=90)
    descrizione = models.TextField(blank=True, null=True)
    costo_pc = models.IntegerField(default=0)
    costo_crediti = models.IntegerField(default=0)
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo__in': [CARATTERISTICA, CONDIZIONE]})
    tiers = models.ManyToManyField(Tier, related_name="abilita", through="abilita_tier")
    requisiti = models.ManyToManyField(Punteggio, related_name="abilita_req", through="abilita_requisito")
    tabelle_sbloccate = models.ManyToManyField(Tabella, related_name="abilita_sbloccante", through="abilita_sbloccata")
    punteggio_acquisito = models.ManyToManyField(Punteggio, related_name="abilita_acquisizione", through="abilita_punteggio")
    statistiche = models.ManyToManyField(Statistica, through='AbilitaStatistica', blank=True, related_name="abilita_statistiche")
    class Meta: verbose_name="Abilità"; verbose_name_plural="Abilità"
    def __str__(self): return self.nome

# Through Models Abilita
class abilita_tier(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE); tabella = models.ForeignKey(Tier, on_delete=models.CASCADE); ordine = models.IntegerField(default=10)
class abilita_prerequisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti"); prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati")
class abilita_requisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE); requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}); valore = models.IntegerField(default=1)
class abilita_sbloccata(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE); sbloccata = models.ForeignKey(Tabella, on_delete=models.CASCADE)
class abilita_punteggio(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE); punteggio = models.ForeignKey(Punteggio, on_delete=models.CASCADE); valore = models.IntegerField(default=1)

# --- LEGACY ATTIVATA ---
class Attivata(A_vista):
    elementi = models.ManyToManyField(Punteggio, blank=True, through='AttivataElemento')
    statistiche_base = models.ManyToManyField(Statistica, through='AttivataStatisticaBase', blank=True, related_name='attivata_statistiche_base')
    def __str__(self): return f"Attivata (LEGACY): {self.nome}"
    @property
    def livello(self): return self.elementi.count()
    @property
    def costo_crediti(self): return self.livello * COSTO_PER_MATTONE
    @property
    def TestoFormattato(self): return formatta_testo_generico(self.testo, statistiche_base=self.attivatastatisticabase_set.select_related('statistica').all())
class AttivataElemento(models.Model):
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE); elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'is_mattone': True})
class AttivataStatisticaBase(models.Model):
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore_base = models.IntegerField(default=0)
    class Meta: unique_together=('attivata', 'statistica')

# --- TECNICHE ---
class Tecnica(A_vista):
    aura_richiesta = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="%(class)s_associate")
    class Meta: abstract=True; ordering=['nome']
    @property
    def livello(self): return self.mattoni.count()
    @property
    def costo_crediti(self): return self.livello * COSTO_PER_MATTONE

class Infusione(Tecnica):
    aura_infusione = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': AURA, 'is_soprannaturale': True}, related_name="infusioni_secondarie")
    mattoni = models.ManyToManyField(Mattone, through='InfusioneMattone', related_name="infusioni_utilizzatrici")
    statistiche_base = models.ManyToManyField(Statistica, through='InfusioneStatisticaBase', blank=True, related_name='infusione_statistiche_base')
    statistiche = models.ManyToManyField(Statistica, through='InfusioneStatistica', blank=True, related_name='infusione_statistiche') # Modificatori
    class Meta: verbose_name="Infusione"; verbose_name_plural="Infusioni"
    @property
    def TestoFormattato(self):
        return formatta_testo_generico(
            self.testo, 
            statistiche_base=self.infusionestatisticabase_set.select_related('statistica').all(),
            context={
                'livello': self.livello,
                'aura': self.aura_richiesta,
                'item_modifiers': self.infusionestatistica_set.select_related('statistica').all()
            }
        )

class Tessitura(Tecnica):
    formula = models.TextField("Formula", blank=True, null=True, help_text="Parametri: {elem}, {rango}.")
    elemento_principale = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': ELEMENTO})
    mattoni = models.ManyToManyField(Mattone, through='TessituraMattone', related_name="tessiture_utilizzatrici")
    statistiche_base = models.ManyToManyField(Statistica, through='TessituraStatisticaBase', blank=True, related_name='tessitura_statistiche_base')
    statistiche = models.ManyToManyField(Statistica, through='TessituraStatistica', blank=True, related_name='tessitura_statistiche') # Modificatori
    class Meta: verbose_name="Tessitura"; verbose_name_plural="Tessiture"
    @property
    def TestoFormattato(self):
        return formatta_testo_generico(
            self.testo, 
            formula=self.formula, 
            statistiche_base=self.tessiturastatisticabase_set.select_related('statistica').all(), 
            context={
                'elemento': self.elemento_principale,
                'livello': self.livello,
                'aura': self.aura_richiesta,
                'item_modifiers': self.tessiturastatistica_set.select_related('statistica').all()
            }
        )

class InfusioneMattone(models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE); mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE); ordine = models.IntegerField(default=0)
class TessituraMattone(models.Model):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE); mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE); ordine = models.IntegerField(default=0)

class InfusioneStatisticaBase(models.Model): # Base (Pivot)
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore_base = models.IntegerField(default=0)
class TessituraStatisticaBase(models.Model): # Base (Pivot)
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore_base = models.IntegerField(default=0)

class InfusioneStatistica(CondizioneStatisticaMixin): # Modificatori (Mixin)
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore = models.IntegerField(default=0); tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: unique_together=('infusione', 'statistica')
class TessituraStatistica(CondizioneStatisticaMixin): # Modificatori (Mixin)
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore = models.IntegerField(default=0); tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: unique_together=('tessitura', 'statistica')

# --- OGGETTO ---
class Manifesto(A_vista):
    def __str__(self): return f"Manifesto: {self.nome}"
class Inventario(A_vista):
    class Meta: verbose_name="Inventario"; verbose_name_plural="Inventari"
    def __str__(self): return f"Inventario: {self.nome}"
    def get_oggetti(self, data=None):
        if data is None: data = timezone.now()
        return Oggetto.objects.filter(tracciamento_inventario__inventario=self, tracciamento_inventario__data_inizio__lte=data, tracciamento_inventario__data_fine__isnull=True)

class OggettoInInventario(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name="tracciamento_inventario")
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="tracciamento_oggetti")
    data_inizio = models.DateTimeField(default=timezone.now)
    data_fine = models.DateTimeField(null=True, blank=True)
    class Meta: ordering=['-data_inizio']

class OggettoElemento(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE); elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': ELEMENTO})
class OggettoStatistica(CondizioneStatisticaMixin):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore = models.IntegerField(default=0); tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: unique_together=('oggetto', 'statistica')
class OggettoStatisticaBase(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE); statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE); valore_base = models.IntegerField(default=0)
    class Meta: unique_together=('oggetto', 'statistica')

class QrCode(models.Model):
    id = models.CharField(primary_key=True, max_length=14, default=generate_short_id, editable=False)
    data_creazione = models.DateTimeField(auto_now_add=True)
    testo = models.TextField(blank=True, null=True)
    vista = models.OneToOneField(A_vista, blank=True, null=True, on_delete=models.SET_NULL)
    def save(self, *args, **kwargs):
        if self._state.adding:
            while True:
                try: super().save(*args, **kwargs); break
                except IntegrityError: self.id = generate_short_id()
        else: super().save(*args, **kwargs)

class Oggetto(A_vista):
    elementi = models.ManyToManyField(Punteggio, blank=True, through='OggettoElemento')
    statistiche = models.ManyToManyField(Statistica, through='OggettoStatistica', blank=True, related_name="oggetti_statistiche")
    statistiche_base = models.ManyToManyField(Statistica, through='OggettoStatisticaBase', blank=True, related_name='oggetti_statistiche_base')
    aura = models.ForeignKey(Punteggio, blank=True, null=True, on_delete=models.SET_NULL, limit_choices_to={'tipo' : AURA}, related_name="oggetti_aura")
    @property
    def livello(self): return self.elementi.count()
    @property
    def TestoFormattato(self):
        return formatta_testo_generico(
            self.testo, 
            statistiche_base=self.oggettostatisticabase_set.select_related('statistica').all(), 
            context={
                'livello': self.livello, 
                'aura': self.aura, 
                'item_modifiers': self.oggettostatistica_set.select_related('statistica').all()
            }
        )
    @property
    def inventario_corrente(self):
        t = self.tracciamento_inventario.filter(data_fine__isnull=True).first()
        return t.inventario if t else None
    def sposta_in_inventario(self, nuovo, data=None):
        if data is None: data = timezone.now()
        with transaction.atomic():
            curr = self.tracciamento_inventario.filter(data_fine__isnull=True).first()
            if curr:
                if curr.inventario == nuovo: return
                curr.data_fine = data; curr.save()
            if nuovo: OggettoInInventario.objects.create(oggetto=self, inventario=nuovo, data_inizio=data)

# --- PERSONAGGIO ---
class TipologiaPersonaggio(models.Model):
    nome = models.CharField(max_length=100, unique=True, default="Standard")
    crediti_iniziali = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    caratteristiche_iniziali = models.IntegerField(default=8)
    giocante = models.BooleanField(default=True)
    class Meta: verbose_name="Tipologia Personaggio"
    def __str__(self): return self.nome

class PuntiCaratteristicaMovimento(models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="movimenti_pc")
    importo = models.IntegerField()
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)
    class Meta: verbose_name="Movimento PC"; ordering=['-data']

class Personaggio(Inventario):
    proprietario = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="personaggi", null=True, blank=True)
    tipologia = models.ForeignKey(TipologiaPersonaggio, on_delete=models.PROTECT, related_name="personaggi", null=True, blank=True)
    data_nascita = models.DateTimeField(default=timezone.now)
    data_morte = models.DateTimeField(null=True, blank=True)
    abilita_possedute = models.ManyToManyField(Abilita, through='PersonaggioAbilita', blank=True)
    attivate_possedute = models.ManyToManyField(Attivata, through='PersonaggioAttivata', blank=True)
    infusioni_possedute = models.ManyToManyField(Infusione, through='PersonaggioInfusione', blank=True)
    tessiture_possedute = models.ManyToManyField(Tessitura, through='PersonaggioTessitura', blank=True)
    modelli_aura = models.ManyToManyField(ModelloAura, through='PersonaggioModelloAura', blank=True, verbose_name="Modelli di Aura")
    
    class Meta: verbose_name="Personaggio"; verbose_name_plural="Personaggi"
    def __str__(self): return self.nome
    
    def save(self, *args, **kwargs):
        if not self.pk and self.tipologia is None:
            t, _ = TipologiaPersonaggio.objects.get_or_create(nome="Standard")
            self.tipologia = t
        super().save(*args, **kwargs)
    
    def aggiungi_log(self, t): PersonaggioLog.objects.create(personaggio=self, testo_log=t)
    def modifica_crediti(self, i, d): CreditoMovimento.objects.create(personaggio=self, importo=i, descrizione=d)
    def modifica_pc(self, i, d): PuntiCaratteristicaMovimento.objects.create(personaggio=self, importo=i, descrizione=d)
    @property
    def crediti(self):
        b = self.tipologia.crediti_iniziali if self.tipologia else 0
        return b + (self.movimenti_credito.aggregate(totale=Sum('importo'))['totale'] or 0)
    @property
    def punti_caratteristica(self):
        b = self.tipologia.caratteristiche_iniziali if self.tipologia else 0
        return b + (self.movimenti_pc.aggregate(totale=Sum('importo'))['totale'] or 0)
    
    @property
    def punteggi_base(self):
        if hasattr(self, '_punteggi_base_cache'): return self._punteggi_base_cache
        links = abilita_punteggio.objects.filter(abilita__personaggioabilita__personaggio=self).select_related('punteggio')
        p = {i['punteggio__nome']: i['valore_totale'] for i in links.values('punteggio__nome').annotate(valore_totale=Sum('valore'))}
        agen = Punteggio.objects.filter(tipo=AURA, is_generica=True).first()
        if agen:
            others = set(Punteggio.objects.filter(tipo=AURA).exclude(id=agen.id).values_list('nome', flat=True))
            p[agen.nome] = max([v for k,v in p.items() if k in others] or [0])
        self._punteggi_base_cache = p
        return p

    @property
    def caratteristiche_base(self):
        return {k:v for k,v in self.punteggi_base.items() if Punteggio.objects.filter(nome=k, tipo=CARATTERISTICA).exists()}

    def get_valore_aura_effettivo(self, aura):
        pb = self.punteggi_base
        if aura.is_generica:
             return max([v for k,v in pb.items() if Punteggio.objects.filter(nome=k, tipo=AURA, is_generica=False).exists()] or [0])
        return pb.get(aura.nome, 0)

    def valida_acquisto_tecnica(self, t):
        if not t.aura_richiesta: return False, "Aura mancante."
        if t.livello > self.get_valore_aura_effettivo(t.aura_richiesta): return False, "Livello > Aura."
        from collections import Counter
        cnt = Counter(t.mattoni.values_list('id', flat=True))
        base = self.caratteristiche_base
        for mid, c in cnt.items():
            try:
                m = Mattone.objects.get(pk=mid)
                if c > base.get(m.caratteristica_associata.nome, 0): return False, f"Requisito {m.nome} non soddisfatto."
            except: pass
        mod = self.modelli_aura.filter(aura=t.aura_richiesta).first()
        if mod:
            ids = set(cnt.keys())
            bad = set(mod.mattoni_proibiti.values_list('id', flat=True))
            if ids.intersection(bad): return False, "Mattoni proibiti."
        return True, "OK"

    @property
    def modificatori_calcolati(self):
        if hasattr(self, '_modificatori_calcolati_cache'): return self._modificatori_calcolati_cache
        mods = {}
        def _add(p, t, v):
            if not p: return
            if p not in mods: mods[p] = {'add': 0, 'mol': 1.0}
            if t == MODIFICATORE_ADDITIVO: mods[p]['add'] += v
            elif t == MODIFICATORE_MOLTIPLICATIVO: mods[p]['mol'] *= float(v)
            
        for l in AbilitaStatistica.objects.filter(abilita__personaggioabilita__personaggio=self).select_related('statistica'): _add(l.statistica.parametro, l.tipo_modificatore, l.valore)
        for l in OggettoStatistica.objects.filter(oggetto__tracciamento_inventario__inventario=self.inventario_ptr, oggetto__tracciamento_inventario__data_fine__isnull=True).select_related('statistica'): _add(l.statistica.parametro, l.tipo_modificatore, l.valore)
        
        cb = self.caratteristiche_base
        if cb:
            for l in CaratteristicaModificatore.objects.filter(caratteristica__nome__in=cb.keys()).select_related('caratteristica', 'statistica_modificata'):
                pts = cb.get(l.caratteristica.nome, 0)
                if pts > 0 and l.ogni_x_punti > 0:
                    b = (pts // l.ogni_x_punti) * l.modificatore
                    if b > 0: _add(l.statistica_modificata.parametro, MODIFICATORE_ADDITIVO, b)
        self._modificatori_calcolati_cache = mods
        return mods

    def get_testo_formattato_per_item(self, item):
        if not item: return ""
        ctx = {}
        stats = []
        item_mods = []
        formula = getattr(item, 'formula', None)
        
        if isinstance(item, Oggetto):
            stats = item.oggettostatisticabase_set.select_related('statistica').all()
            item_mods = item.oggettostatistica_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura, 'item_modifiers': item_mods}
        elif isinstance(item, Infusione):
            stats = item.infusionestatisticabase_set.select_related('statistica').all()
            item_mods = item.infusionestatistica_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'item_modifiers': item_mods}
        elif isinstance(item, Tessitura):
            stats = item.tessiturastatisticabase_set.select_related('statistica').all()
            item_mods = item.tessiturastatistica_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': item.elemento_principale, 'item_modifiers': item_mods}
        elif isinstance(item, Attivata):
            stats = item.attivatastatisticabase_set.select_related('statistica').all()
            
        return formatta_testo_generico(item.testo, formula=formula, statistiche_base=stats, personaggio=self, context=ctx)

# Relazioni Through Personaggio (e Log/Crediti definiti sopra)
class PersonaggioAbilita(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE); abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE); data_acquisizione = models.DateTimeField(default=timezone.now)
class PersonaggioAttivata(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE); attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE); data_acquisizione = models.DateTimeField(default=timezone.now)
class PersonaggioInfusione(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE); infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE); data_acquisizione = models.DateTimeField(default=timezone.now)
class PersonaggioTessitura(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE); tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE); data_acquisizione = models.DateTimeField(default=timezone.now)
class PersonaggioModelloAura(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE); modello_aura = models.ForeignKey(ModelloAura, on_delete=models.CASCADE)
    class Meta: verbose_name_plural="Personaggio - Modelli Aura"
    def clean(self):
        if PersonaggioModelloAura.objects.filter(personaggio=self.personaggio, modello_aura__aura=self.modello_aura.aura).exclude(pk=self.pk).exists(): raise ValidationError("Già presente.")
    def save(self, *args, **kwargs): self.clean(); super().save(*args, **kwargs)

class PersonaggioLog(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="log_eventi"); data = models.DateTimeField(default=timezone.now); testo_log = models.TextField()
    class Meta: ordering=['-data']
class CreditoMovimento(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="movimenti_credito"); importo = models.DecimalField(max_digits=10, decimal_places=2); descrizione = models.CharField(max_length=200); data = models.DateTimeField(default=timezone.now)
    class Meta: ordering=['-data']
class TransazioneSospesa(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE); mittente = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="transazioni_in_uscita_sospese"); richiedente = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="transazioni_in_entrata_sospese"); data_richiesta = models.DateTimeField(default=timezone.now); stato = models.CharField(max_length=10, choices=STATO_TRANSAZIONE_CHOICES, default=STATO_TRANSAZIONE_IN_ATTESA)
    class Meta: ordering=['-data_richiesta']
    def accetta(self):
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA: raise Exception("Processata")
        self.oggetto.sposta_in_inventario(self.richiedente); self.stato = STATO_TRANSAZIONE_ACCETTATA; self.save()
    def rifiuta(self):
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA: raise Exception("Processata")
        self.stato = STATO_TRANSAZIONE_RIFIUTATA; self.save()

# Messaging
class Gruppo(models.Model):
    nome = models.CharField(max_length=100, unique=True); membri = models.ManyToManyField('Personaggio', related_name="gruppi_appartenenza", blank=True)
    def __str__(self): return self.nome
class Messaggio(models.Model):
    TIPO_BROADCAST='BROAD'; TIPO_GRUPPO='GROUP'; TIPO_INDIVIDUALE='INDV'
    TIPO_CHOICES=[(TIPO_BROADCAST,'Broadcast'),(TIPO_GRUPPO,'Gruppo'),(TIPO_INDIVIDUALE,'Individuale')]
    mittente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="messaggi_inviati")
    tipo_messaggio = models.CharField(max_length=5, choices=TIPO_CHOICES, default=TIPO_BROADCAST)
    destinatario_personaggio = models.ForeignKey('Personaggio', on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_individuali")
    destinatario_gruppo = models.ForeignKey(Gruppo, on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_gruppo")
    titolo = models.CharField(max_length=150); testo = models.TextField(); data_invio = models.DateTimeField(default=timezone.now); salva_in_cronologia = models.BooleanField(default=True)
    class Meta: ordering=['-data_invio']

# CMS Plugins
class AbilitaPluginModel(CMSPlugin):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    def __str__(self): return self.abilita.nome
class OggettoPluginModel(CMSPlugin):
    oggetto = models.ForeignKey(Oggetto, on_delete=models.CASCADE)
    def __str__(self): return self.oggetto.nome
class AttivataPluginModel(CMSPlugin):
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE)
    def __str__(self): return self.attivata.nome
class InfusionePluginModel(CMSPlugin):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    def __str__(self): return self.infusione.nome
class TessituraPluginModel(CMSPlugin):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    def __str__(self): return self.tessitura.nome
class TabellaPluginModel(CMSPlugin):
    tabella = models.ForeignKey(Tabella, on_delete=models.CASCADE)
    def __str__(self): return self.tabella.nome
class TierPluginModel(CMSPlugin):
    tier = models.ForeignKey(Tier, on_delete=models.CASCADE, related_name='cms_kor_tier_plugin')
    def __str__(self): return self.tier.nome