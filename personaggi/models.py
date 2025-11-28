from django.db.models import Sum, F, Count
import re
import secrets
import string
import copy
from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.conf import settings
from django.contrib.auth.models import User
from colorfield.fields import ColorField
from django_icon_picker.field import IconField
from cms.models.pluginmodel import CMSPlugin
from django.utils.html import format_html
from icon_widget.fields import CustomIconField

# --- COSTANTI ---
COSTO_PER_MATTONE_INFUSIONE = 100
COSTO_PER_MATTONE_TESSITURA = 100
COSTO_PER_MATTONE_OGGETTO = 100

# --- COSTANTI TRANSAZIONI ---
STATO_TRANSAZIONE_IN_ATTESA = 'IN_ATTESA'
STATO_TRANSAZIONE_ACCETTATA = 'ACCETTATA'
STATO_TRANSAZIONE_RIFIUTATA = 'RIFIUTATA'

STATO_TRANSAZIONE_CHOICES = [
    (STATO_TRANSAZIONE_IN_ATTESA, 'In Attesa'),
    (STATO_TRANSAZIONE_ACCETTATA, 'Accettata'),
    (STATO_TRANSAZIONE_RIFIUTATA, 'Rifiutata'),
]

STATO_PROPOSTA_BOZZA = 'BOZZA'
STATO_PROPOSTA_IN_VALUTAZIONE = 'VALUTAZIONE'
STATO_PROPOSTA_APPROVATA = 'APPROVATA'
STATO_PROPOSTA_RIFIUTATA = 'RIFIUTATA'

STATO_PROPOSTA_CHOICES = [
    (STATO_PROPOSTA_BOZZA, 'Bozza'),
    (STATO_PROPOSTA_IN_VALUTAZIONE, 'In Valutazione'),
    (STATO_PROPOSTA_APPROVATA, 'Approvata'),
    (STATO_PROPOSTA_RIFIUTATA, 'Rifiutata'),
]

TIPO_PROPOSTA_INFUSIONE = 'INF'
TIPO_PROPOSTA_TESSITURA = 'TES'

TIPO_PROPOSTA_CHOICES = [
    (TIPO_PROPOSTA_INFUSIONE, 'Infusione'),
    (TIPO_PROPOSTA_TESSITURA, 'Tessitura'),
]

# Aggiungi enum per i tipi
TIPO_OGGETTO_FISICO = 'FIS'
TIPO_OGGETTO_MATERIA = 'MAT'
TIPO_OGGETTO_MOD = 'MOD'
TIPO_OGGETTO_INNESTO = 'INN'
TIPO_OGGETTO_MUTAZIONE = 'MUT'

TIPO_OGGETTO_CHOICES = [
    (TIPO_OGGETTO_FISICO, 'Oggetto Fisico'),
    (TIPO_OGGETTO_MATERIA, 'Materia (Mondana)'),
    (TIPO_OGGETTO_MOD, 'Mod (Tecnologica)'),
    (TIPO_OGGETTO_INNESTO, 'Innesto (Tecnologico)'),
    (TIPO_OGGETTO_MUTAZIONE, 'Mutazione (Innata)'),
]

# Enum per slot corpo (Innesti/Mutazioni)
SLOT_TESTA = 'HD'
SLOT_TRONCO = 'TR'
SLOT_BRACCIO_DX = 'RA'
SLOT_BRACCIO_SX = 'LA'
SLOT_GAMBA_DX = 'RL'
SLOT_GAMBA_SX = 'LL'

SLOT_CORPO_CHOICES = [
    (SLOT_TESTA, 'Testa'),
    (SLOT_TRONCO, 'Tronco'),
    (SLOT_BRACCIO_DX, 'Braccio Dx'),
    (SLOT_BRACCIO_SX, 'Braccio Sx'),
    (SLOT_GAMBA_DX, 'Gamba Dx'),
    (SLOT_GAMBA_SX, 'Gamba Sx'),
]

# --- FUNZIONI DI UTILITÀ ---

def get_testo_rango(valore):
    """
    Restituisce la stringa del rango in base al valore numerico.
    """
    try:
        valore = int(valore)
    except (ValueError, TypeError):
        return ""

    if valore <= 0:
        return "Mondano! "
    elif valore == 1:
        return "" 
    elif valore == 2:
        return "Eroico! "
    elif valore == 3:
        return "Leggendario! "
    elif valore == 4:
        return "Mitologico! "
    elif valore == 5:
        return "Divino! "
    elif valore == 6:
        return "Cosmico! "
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

# --- FUNZIONI PER FORMATTAZIONE TESTO ---

def evaluate_expression(expression, context_dict):
    """
    Valuta una espressione stringa (es: "forza > 5" o "10 - destrezza")
    usando il contesto fornito. Restituisce il risultato o 0/False in caso di errore.
    """
    if not expression:
        return 0
    
    # Pulizia base per sicurezza
    if "__" in expression or "import" in expression or "lambda" in expression:
        return 0

    # Normalizza il contesto
    safe_context = {str(k).lower(): v for k, v in context_dict.items() if k}
    safe_context['max'] = max
    safe_context['min'] = min
    safe_context['abs'] = abs
    safe_context['int'] = int
    safe_context['round'] = round

    try:
        return eval(str(expression).lower(), {"__builtins__": {}}, safe_context)
    except Exception:
        return 0

def formatta_testo_generico(testo, formula=None, statistiche_base=None, personaggio=None, context=None, solo_formula=False):
    """
    Funzione universale per la formattazione dei testi con parametri.
    """
    testo_out = testo or ""
    formula_out = formula or ""
    
    if not testo_out and not formula_out:
        return ""

    # 1. Normalizzazione Statistiche Base
    base_values = {}
    # Contesto di valutazione per formule e condizioni
    eval_context = {}

    if statistiche_base:
        for item in statistiche_base:
            param = getattr(item.statistica, 'parametro', None) if hasattr(item, 'statistica') else None
            val = getattr(item, 'valore_base', 0)
            if param:
                base_values[param] = val
                eval_context[param] = val

    # 2. Preparazione Dati Personaggio (per eval_context e modificatori)
    mods_attivi = {}
    
    if personaggio:
        # A. Modificatori Globali del Personaggio
        mods_attivi = copy.deepcopy(personaggio.modificatori_calcolati)
        
        # Popola eval_context con i dati del PG
        eval_context.update(personaggio.caratteristiche_base)
        
        for param, mod_data in mods_attivi.items():
            val_base = eval_context.get(param, 0) 
            val_finale = (val_base + mod_data['add']) * mod_data['mol']
            eval_context[param] = val_finale

    # 3. Variabili di Contesto Specifico (es. livello tecnica)
    if context:
        eval_context.update(context) 
        if 'caratteristica_associata_valore' in context:
             eval_context['caratt'] = context['caratteristica_associata_valore']

    # 4. Applicazione Modificatori Locali (Condizionali)
    testo_metatalenti = ""

    if context:
        item_modifiers = context.get('item_modifiers', [])
        current_aura = context.get('aura')
        current_elem = context.get('elemento')

        for mod in item_modifiers:
            # Verifica Condizioni
            passa_aura = True
            if mod.usa_limitazione_aura:
                if not current_aura or not mod.limit_a_aure.filter(pk=current_aura.pk).exists():
                    passa_aura = False
            
            passa_elem = True
            if mod.usa_limitazione_elemento:
                if not current_elem or not mod.limit_a_elementi.filter(pk=current_elem.pk).exists():
                    passa_elem = False
            
            # Verifica Condizione Testuale (Es. "forza > 5")
            passa_text = True
            if mod.usa_condizione_text and mod.condizione_text:
                local_ctx = eval_context.copy()
                # Se è un modificatore di un Mattone, aggiungiamo {caratt} specifica
                if hasattr(mod, 'mattone') and mod.mattone.caratteristica_associata:
                    nome_c = mod.mattone.caratteristica_associata.nome
                    val_c = eval_context.get(nome_c, 0)
                    local_ctx['caratt'] = val_c
                
                if not evaluate_expression(mod.condizione_text, local_ctx):
                    passa_text = False

            if passa_aura and passa_elem and passa_text:
                p = mod.statistica.parametro
                if p:
                    if p not in mods_attivi:
                        mods_attivi[p] = {'add': 0, 'mol': 1.0}
                    
                    if mod.tipo_modificatore == MODIFICATORE_ADDITIVO:
                        mods_attivi[p]['add'] += mod.valore
                    elif mod.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO:
                        mods_attivi[p]['mol'] *= float(mod.valore)

    # 5. Logica Metatalenti (Testo Addizionale e Bonus Aura)
    if personaggio and context:
        aura_riferimento = context.get('aura')
        livello_item = context.get('livello', 0)
        
        if aura_riferimento:
            modello = personaggio.modelli_aura.filter(aura=aura_riferimento).first()
            if modello:
                caratteristiche_pg = personaggio.caratteristiche_base
                for mattone in modello.mattoni_proibiti.all():
                    funz = mattone.funzionamento_metatalento
                    if funz == META_NESSUN_EFFETTO: continue 
                    
                    nome_caratt = mattone.caratteristica_associata.nome
                    val_caratt = caratteristiche_pg.get(nome_caratt, 0)
                    
                    # Verifica condizione di attivazione del mattone
                    applica = False
                    if funz in [META_VALORE_PUNTEGGIO, META_SOLO_TESTO]:
                        applica = True
                    elif funz == META_LIVELLO_INFERIORE and livello_item <= val_caratt:
                        applica = True
                    
                    if applica:
                        # Applicazione bonus numerici (se non già gestiti)
                        if funz in [META_VALORE_PUNTEGGIO, META_LIVELLO_INFERIORE]:
                            for stat_m in mattone.mattonestatistica_set.select_related('statistica').all():
                                p = stat_m.statistica.parametro
                                b = stat_m.valore * val_caratt
                                if p:
                                    if p not in mods_attivi: mods_attivi[p] = {'add': 0, 'mol': 1.0}
                                    if stat_m.tipo_modificatore == MODIFICATORE_ADDITIVO:
                                        mods_attivi[p]['add'] += b
                                    elif stat_m.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO:
                                        mods_attivi[p]['mol'] *= float(b)

                        # Testo Addizionale
                        txt_add = mattone.testo_addizionale
                        if txt_add:
                            # Risoluzione {3*caratt}
                            def repl(m):
                                factor = int(m.group(1)) if m.group(1) else 1
                                return str(val_caratt * factor)
                            parsed = re.sub(r'\{(?:(\d+)\*)?caratt\}', repl, txt_add)
                            testo_metatalenti += f"<br><em>Metatalento ({mattone.nome}):</em> {parsed}"

    # 6. Risoluzione Placeholder (es. {7-forza})
    def resolve_placeholder(match):
        expr = match.group(1).strip()
        
        # Tenta valutazione matematica (es. 7 - caratt)
        val_math = evaluate_expression(expr, eval_context)
        if val_math or val_math == 0: # Accetta anche 0 come risultato valido
             try:
                 return str(int(round(float(val_math))))
             except:
                 return str(val_math)
        
        # Fallback: logica base+modificatori (es. {pv})
        try:
            tokens = re.split(r'([+\-])', expr) 
            total = 0; op = '+'
            for t in tokens:
                t = t.strip()
                if not t: continue
                if t in ['+', '-']: op = t
                else:
                    base = base_values.get(t, 0)
                    mods = mods_attivi.get(t, {'add': 0.0, 'mol': 1.0})
                    val = (base + mods['add']) * mods['mol']
                    if op == '+': total += val
                    elif op == '-': total -= val
            return str(int(round(total)))
        except:
            return match.group(0)

    # 7. Gestione Blocchi {if ...}
    def replace_conditional_block(match):
        condizione = match.group(1)
        contenuto = match.group(2)
        if evaluate_expression(condizione, eval_context):
            return contenuto
        return ""
    
    if solo_formula:
        testo_metatalenti = ""

    testo_completo = testo_out + testo_metatalenti
    
    # 8. Sostituzioni Finali
    # Parametri testuali (Elem, Rango)
    if context:
        if context.get('elemento'):
            elem_obj = context['elemento']
            repl = elem_obj.nome
            # Gestione Dichiarazione
            if hasattr(elem_obj, 'dichiarazione') and elem_obj.dichiarazione:
                 repl = elem_obj.dichiarazione
            elif hasattr(elem_obj, 'mattone') and elem_obj.mattone.dichiarazione:
                 repl = elem_obj.mattone.dichiarazione
                 
            testo_completo = testo_completo.replace("{elem}", repl)
            formula_out = formula_out.replace("{elem}", repl)
        
        rango_val = base_values.get('rango')
        if rango_val is None and statistiche_base:
             r_obj = next((x for x in statistiche_base if getattr(x.statistica, 'nome', '').lower() == "rango"), None)
             if r_obj: rango_val = r_obj.valore_base
        
        if rango_val is not None:
             r_txt = get_testo_rango(rango_val)
             testo_completo = testo_completo.replace("{rango}", r_txt)
             formula_out = formula_out.replace("{rango}", r_txt)

    # Risoluzione IF
    pattern_if = re.compile(r'\{if\s+(.+?)\}(.*?)\{endif\}', re.DOTALL | re.IGNORECASE)
    testo_finale = pattern_if.sub(replace_conditional_block, testo_completo)
    formula_finale = pattern_if.sub(replace_conditional_block, formula_out)

    # Risoluzione Valori
    testo_finale = re.sub(r'\{([^{}]+)\}', resolve_placeholder, testo_finale)
    formula_finale = re.sub(r'\{([^{}]+)\}', resolve_placeholder, formula_finale)
    
    # Output
    parts = []
    if testo_finale:
        parts.append(testo_finale)
    if formula_finale:
        if testo_finale:
            parts.append("<br/><hr style='margin:5px 0; border:0; border-top:1px dashed #ccc;'/>")
        parts.append(f"<strong>Formula:</strong> {formula_finale}")
        
    return "".join(parts)


# --- TIPI GENERICI ---

CARATTERISTICA = "CA"
STATISTICA = "ST"
ELEMENTO = "EL"
AURA = "AU"
CONDIZIONE = "CO"
CULTO = "CU"   
VIA = "VI"
ARTE = "AR"
ARCHETIPO = "AR"

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

MODIFICATORE_ADDITIVO = 'ADD'
MODIFICATORE_MOLTIPLICATIVO = 'MOL'
MODIFICATORE_CHOICES = [
    (MODIFICATORE_ADDITIVO, 'Additivo (+N)'),
    (MODIFICATORE_MOLTIPLICATIVO, 'Moltiplicativo (xN)'),
]

META_NESSUN_EFFETTO = 'NE'
META_VALORE_PUNTEGGIO = 'VP'
META_SOLO_TESTO = 'TX'
META_LIVELLO_INFERIORE = 'LV'

METATALENTO_CHOICES = [
    (META_NESSUN_EFFETTO, 'Nessun Effetto'),
    (META_VALORE_PUNTEGGIO, 'Valore per Punteggio'),
    (META_SOLO_TESTO, 'Solo Testo Addizionale'),
    (META_LIVELLO_INFERIORE, 'Solo abilità con livello pari o inferiore'),
]

# --- CLASSI ASTRATTE ---

class A_modello(models.Model):
    id = models.AutoField("Codice Identificativo", primary_key=True)
    
    class Meta:
        abstract = True
        
class A_vista(models.Model):
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
    Mixin per aggiungere filtri condizionali alle statistiche.
    """
    usa_limitazione_aura = models.BooleanField("Usa Limitazione Aura", default=False)
    limit_a_aure = models.ManyToManyField(
        'Punteggio', 
        blank=True, 
        limit_choices_to={'tipo': AURA}, 
        related_name="%(class)s_limit_aure", 
        verbose_name="Aure consentite"
    )
    
    usa_limitazione_elemento = models.BooleanField("Usa Limitazione Elemento", default=False)
    limit_a_elementi = models.ManyToManyField(
        'Punteggio', 
        blank=True, 
        limit_choices_to={'tipo': ELEMENTO}, 
        related_name="%(class)s_limit_elementi", 
        verbose_name="Elementi consentiti"
    )

    # Campi per condizione testuale
    usa_condizione_text = models.BooleanField("Usa Condizione Testuale", default=False)
    condizione_text = models.CharField(
        "Condizione (es. caratt>6)", 
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Espressione logica. Variabili: {caratt}, {livello}, {pv}, ecc."
    )
    
    class Meta:
        abstract = True

# --- CORE MODELS ---

class Tabella(A_modello):
    nome = models.CharField(max_length=90)
    descrizione = models.TextField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Tabella"
        verbose_name_plural = "Tabelle"

    def __str__(self):
        return self.nome

class Tier(Tabella):
    tipo = models.CharField(choices=tabelle_tipo, max_length=2)
    foto = models.ImageField(upload_to='tiers/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Tier"
        verbose_name_plural = "Tiers"

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
    
    caratteristica_relativa = models.ForeignKey(
        "Punteggio", 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': CARATTERISTICA}, 
        null=True, blank=True, 
        related_name="punteggi_caratteristica"
    )
    modifica_statistiche = models.ManyToManyField(
        'Statistica', 
        through='CaratteristicaModificatore', 
        related_name='modificata_da_caratteristiche', 
        blank=True
    )
    aure_infusione_consentite = models.ManyToManyField(
        'self', 
        blank=True, 
        symmetrical=False, 
        related_name='puo_essere_infusa_in',
        help_text="Seleziona quali aure possono essere usate come fonte di mattoni quando questa aura è selezionata come 'Aura Richiesta'."
    )    
    class Meta:
        verbose_name = "Punteggio"
        verbose_name_plural = "Punteggi"
        ordering = ['tipo', 'ordine', 'nome']
        
    def svg_icon(self):
        return format_html(
            '<img src="{}" height="30" width="30" alt="{}"/>'.format(
                f"/{self.icon}" if self.icon.endswith(".svg") else f"https://api.iconify.design/{self.icon}.svg",
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
                f"width: 24px; height: 24px; background-color: {colore}; "
                f"mask-image: url({url}); -webkit-mask-image: url({url}); "
                f"mask-size: contain; -webkit-mask-size: contain; "
                f"display: inline-block; vertical-align: middle;"
            )
            return format_html('<div style="{}"></div>', style)
        return ""
    
    def icona_cerchio(self, inverted=True):
        url = self.icona_url 
        if not url or not self.colore:
            return ""

        colore_sfondo = _get_icon_color_from_bg(self.colore) if inverted else self.colore
        colore_icona = self.colore if inverted else _get_icon_color_from_bg(self.colore)
        
        style_c = (
            f"display: inline-block; width: 30px; height: 30px; "
            f"background-color: {colore_sfondo}; border-radius: 50%; "
            f"vertical-align: middle; text-align: center; line-height: 30px;"
        )
        style_i = (
            f"display: inline-block; width: 24px; height: 24px; "
            f"vertical-align: middle; background-color: {colore_icona}; "
            f"mask-image: url({url}); -webkit-mask-image: url({url}); "
            f"mask-size: contain; -webkit-mask-size: contain;"
        )
        return format_html('<div style="{}"><div style="{}"></div></div>', style_c, style_i)
    
    @property
    def icona_cerchio_html(self):
        return self.icona_cerchio(inverted=False)
    
    @property
    def icona_cerchio_inverted_html(self):
        return self.icona_cerchio(inverted=True)
    
    def __str__(self):
        return f"{self.tipo} - {self.nome}"

class Caratteristica(Punteggio):
    class Meta:
        proxy = True
        verbose_name = "Caratteristica (Gestione)"
        verbose_name_plural = "Caratteristiche (Gestione)"

class Statistica(Punteggio):
    parametro = models.CharField(max_length=10, unique=True, blank=True, null=True)
    valore_predefinito = models.IntegerField(default=0)
    valore_base_predefinito = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    is_primaria = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        self.tipo = STATISTICA
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = "Statistica"
        verbose_name_plural = "Statistiche"
    
    @classmethod
    def get_help_text_parametri(cls, extra_params=None):
        stats = cls.objects.filter(parametro__isnull=False).exclude(parametro__exact='').order_by('nome')
        items = []
        for s in stats:
            items.append(f"&bull; <b>{{{s.parametro}}}</b>: {s.nome}")
        if extra_params:
            for p_code, p_desc in extra_params:
                items.append(f"&bull; <b>{p_code}</b>: {p_desc}")
        return mark_safe("<b>Variabili disponibili:</b><br>" + "<br>".join(items))

class Mattone(Punteggio):
    aura = models.ForeignKey(
        Punteggio, on_delete=models.CASCADE, 
        limit_choices_to={'tipo': AURA}, related_name="mattoni_aura"
    )
    caratteristica_associata = models.ForeignKey(
        Punteggio, on_delete=models.CASCADE, 
        limit_choices_to={'tipo': CARATTERISTICA}, related_name="mattoni_caratteristica"
    )
    descrizione_mattone = models.TextField(blank=True, null=True)
    descrizione_metatalento = models.TextField(blank=True, null=True)
    testo_addizionale = models.TextField(blank=True, null=True)
    
    dichiarazione = models.TextField("Dichiarazione", blank=True, null=True, help_text="Testo per {elem}.")
    
    funzionamento_metatalento = models.CharField(
        max_length=2, choices=METATALENTO_CHOICES, default=META_NESSUN_EFFETTO
    )
    
    statistiche = models.ManyToManyField(
        Statistica, through='MattoneStatistica', 
        blank=True, related_name="mattoni_statistiche"
    )

    def save(self, *args, **kwargs):
        self.is_mattone = True
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Mattone"
        verbose_name_plural = "Mattoni"
        unique_together = ('aura', 'caratteristica_associata')
        ordering = ['tipo', 'ordine', 'nome'] 

class MattoneStatistica(CondizioneStatisticaMixin):
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    
    class Meta:
        unique_together = ('mattone', 'statistica')
    
    def __str__(self):
        return f"{self.statistica.nome}: {self.valore}"

class Aura(Punteggio):
    class Meta:
        proxy = True
        verbose_name = "Aura (Gestione)"
        verbose_name_plural = "Aure (Gestione)"
        
    def save(self, *args, **kwargs):
        self.type = AURA
        super().save(*args, **kwargs)

class ModelloAuraRequisitoDoppia(models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_doppia_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Requisito Doppia Formula"
        verbose_name_plural = "Requisiti Doppia Formula"
        
class ModelloAuraRequisitoMattone(models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_mattone_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Requisito Formula x Mattone"
        verbose_name_plural = "Requisiti Formula x Mattone"

class ModelloAuraRequisitoCaratt(models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_caratt_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Requisito Formula x Caratteristica"
        verbose_name_plural = "Requisiti Formula x Caratteristica"

class ModelloAura(models.Model):
    aura = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': AURA}, 
        related_name="modelli_definiti"
    )
    nome = models.CharField(max_length=100)
    descrizione = models.TextField(blank=True, null=True, verbose_name="Descrizione Breve")
    
    mattoni_proibiti = models.ManyToManyField(
        Mattone, 
        blank=True, 
        related_name="proibiti_in_modelli",
        verbose_name="Mattoni Proibiti"
    )
    
    # NUOVO CAMPO
    mattoni_obbligatori = models.ManyToManyField(
        Mattone, 
        blank=True, 
        related_name="obbligatori_in_modelli",
        verbose_name="Mattoni Obbligatori",
        help_text="Le tessiture DEVONO contenere almeno uno di questi mattoni per poter essere apprese."
    )
    
    # --- DOPPIA FORMULA ---
    usa_doppia_formula = models.BooleanField(default=False, verbose_name="Abilita Doppia Formula")
    elemento_secondario = models.ForeignKey(
        Punteggio, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'tipo': ELEMENTO}, related_name="modelli_secondari"
    )
    
    # Condizionale Doppia Formula
    usa_condizione_doppia = models.BooleanField(
        default=False, 
        verbose_name="Richiede Condizione per Doppia",
        help_text="Se attivo, la doppia formula appare solo se i requisiti sotto sono soddisfatti."
    )
    requisiti_doppia = models.ManyToManyField(
        Punteggio, through=ModelloAuraRequisitoDoppia, blank=True, related_name="modelli_req_doppia"
    )
    
    # --- NUOVO: FORMULA PER MATTONE ---
    usa_formula_per_mattone = models.BooleanField(
        default=False, verbose_name="Abilita Formula per Mattone"
    )
    
    # Condizionale Formula Mattone
    usa_condizione_mattone = models.BooleanField(
        default=False, 
        verbose_name="Richiede Condizione per F. Mattone",
        help_text="Se attivo, le formule dei mattoni appaiono solo se i requisiti sotto sono soddisfatti."
    )
    requisiti_mattone = models.ManyToManyField(
        Punteggio, through=ModelloAuraRequisitoMattone, blank=True, related_name="modelli_req_mattone"
    )
    
    # --- FORMULA PER CARATTERISTICA ---
    usa_formula_per_caratteristica = models.BooleanField(
        default=False, verbose_name="Abilita Formula per Caratteristica"
    )
    
    # Condizionale Formula Caratteristica
    usa_condizione_caratt = models.BooleanField(
        default=False, 
        verbose_name="Richiede Condizione per F. Caratt.",
        help_text="Se attivo, le formule extra appaiono solo se i requisiti sotto sono soddisfatti."
    )
    requisiti_caratt = models.ManyToManyField(
        Punteggio, through=ModelloAuraRequisitoCaratt, blank=True, related_name="modelli_req_caratt"
    )
    
    class Meta:
        verbose_name = "Modello di Aura"
        verbose_name_plural = "Modelli di Aura"
        
    def __str__(self):
        return f"Modello {self.aura.nome} - {self.nome}"

class CaratteristicaModificatore(models.Model):
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, related_name="modificatori_dati")
    statistica_modificata = models.ForeignKey(Statistica, on_delete=models.CASCADE, related_name="modificatori_ricevuti")
    modificatore = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    ogni_x_punti = models.IntegerField(default=1)
    
    class Meta:
        unique_together = ('caratteristica', 'statistica_modificata')

class AbilitaStatistica(CondizioneStatisticaMixin):
    abilita = models.ForeignKey('Abilita', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    valore = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('abilita', 'statistica')
    
    def __str__(self):
        return f"{self.statistica.nome}: {self.valore}"

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
    
    class Meta:
        verbose_name = "Abilità"
        verbose_name_plural = "Abilità"
        
    def __str__(self): return self.nome

# Through Models Abilita
class abilita_tier(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    tabella = models.ForeignKey(Tier, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=10)

class abilita_prerequisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti")
    prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati")
    
    class Meta:
        verbose_name = "Abilità richieste come prerequisito di acquisto"

class abilita_requisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    requisito = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo__in': (CARATTERISTICA, CONDIZIONE, STATISTICA)}
        )
    valore = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "Punteggi richiesti come requisito di acquisto"

class abilita_sbloccata(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    sbloccata = models.ForeignKey(Tabella, on_delete=models.CASCADE)
    
class abilita_punteggio(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    punteggio = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "Punteggi assegnati dall'abilità"

# --- LEGACY: ATTIVATA ---
class Attivata(A_vista):
    elementi = models.ManyToManyField(Punteggio, blank=True, through='AttivataElemento')
    statistiche_base = models.ManyToManyField(Statistica, through='AttivataStatisticaBase', blank=True, related_name='attivata_statistiche_base')
    
    def __str__(self): return f"Attivata (LEGACY): {self.nome}"
    
    @property
    def livello(self): return self.elementi.count()
    
    @property
    def costo_crediti(self): return self.livello * COSTO_PER_MATTONE_TESSITURA
    
    @property
    def TestoFormattato(self):
        return formatta_testo_generico(
            self.testo, 
            statistiche_base=self.attivatastatisticabase_set.select_related('statistica').all()
        )

class AttivataElemento(models.Model):
    attivata = models.ForeignKey('Attivata', on_delete=models.CASCADE)
    elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'is_mattone': True})

class AttivataStatisticaBase(models.Model):
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    class Meta: unique_together = ('attivata', 'statistica')
    def __str__(self): return f"{self.statistica.nome}: {self.valore_base}"

# --- TECNICHE ---

class Tecnica(A_vista):
    aura_richiesta = models.ForeignKey(
        Punteggio, on_delete=models.CASCADE, 
        limit_choices_to={'tipo': AURA}, related_name="%(class)s_associate"
    )
    
    class Meta:
        abstract = True
        ordering = ['nome']
        
    @property
    def livello(self): return self.mattoni.count()

class Infusione(Tecnica):
    aura_infusione = models.ForeignKey(
        Punteggio, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'tipo': AURA, 'is_soprannaturale': True}, related_name="infusioni_secondarie"
    )
    mattoni = models.ManyToManyField(Mattone, through='InfusioneMattone', related_name="infusioni_utilizzatrici")
    
    # Infusione ha SOLO statistiche_base
    statistiche_base = models.ManyToManyField(
        Statistica, through='InfusioneStatisticaBase', 
        blank=True, related_name='infusione_statistiche_base'
    )
    
    proposta_creazione = models.OneToOneField(
        'PropostaTecnica', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='infusione_generata',
        verbose_name="Proposta Originale"
    )
    statistica_cariche = models.ForeignKey(
        Statistica, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name="infusioni_cariche",
        verbose_name="Statistica per Cariche Max",
        help_text="Se vuoto, l'oggetto non ha cariche."
    )    
    metodo_ricarica = models.TextField(
        "Metodo di Ricarica", 
        blank=True, null=True, 
        help_text="Descrizione parametrizzata (es. 'Spendi {costo} crediti'). Obbligatorio per Tech."
    )
    costo_ricarica_crediti = models.IntegerField(
        "Costo Ricarica (Crediti)", 
        default=0,
        help_text="Costo per ricaricare una singola carica (default 0)."
    )
    durata_attivazione = models.IntegerField(
        "Durata Attivazione (secondi)", 
        default=0, 
        help_text="Se > 0, attiva un timer nel frontend all'uso della carica."
    )

    def clean(self):
        super().clean()
        # Validazione Regola Tecnologica: Obbligo ricarica e cariche
        # Assumiamo che l'aura tecnologica abbia un nome o ID specifico, 
        # qui uso una logica generica basata sul nome, adattala al tuo DB.
        if self.aura_richiesta and "tecnologic" in self.aura_richiesta.nome.lower():
            if not self.statistica_cariche:
                raise ValidationError("Le infusioni tecnologiche devono definire una statistica per le cariche massime.")
            if not self.metodo_ricarica:
                raise ValidationError("Le infusioni tecnologiche devono specificare il metodo di ricarica.")
    
    class Meta:
        verbose_name = "Infusione"
        verbose_name_plural = "Infusioni"
    
    @property
    def costo_crediti(self): return self.livello * COSTO_PER_MATTONE_INFUSIONE
        
    @property
    def TestoFormattato(self):
        return formatta_testo_generico(
            self.testo, 
            statistiche_base=self.infusionestatisticabase_set.select_related('statistica').all(),
            context={'livello': self.livello, 'aura': self.aura_richiesta}
        )

class Tessitura(Tecnica):
    formula = models.TextField("Formula", blank=True, null=True, help_text="Parametri: {elem}, {rango}.")
    elemento_principale = models.ForeignKey(
        Punteggio, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'tipo': ELEMENTO}
    )
    mattoni = models.ManyToManyField(Mattone, through='TessituraMattone', related_name="tessiture_utilizzatrici")
    
    # Tessitura ha SOLO statistiche_base
    statistiche_base = models.ManyToManyField(
        Statistica, through='TessituraStatisticaBase', 
        blank=True, related_name='tessitura_statistiche_base'
    )
    
    proposta_creazione = models.OneToOneField(
        'PropostaTecnica', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='tessitura_generata',
        verbose_name="Proposta Originale"
    )
    
    class Meta:
        verbose_name = "Tessitura"
        verbose_name_plural = "Tessiture"
    
    @property
    def costo_crediti(self): return self.livello * COSTO_PER_MATTONE_TESSITURA
    
    @property
    def TestoFormattato(self):
        return formatta_testo_generico(
            self.testo, 
            formula=self.formula, 
            statistiche_base=self.tessiturastatisticabase_set.select_related('statistica').all(), 
            context={
                'elemento': self.elemento_principale,
                'livello': self.livello,
                'aura': self.aura_richiesta
            }
        )

class InfusioneMattone(models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=0)

class TessituraMattone(models.Model):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=0)

class InfusioneStatisticaBase(models.Model): # Base
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.statistica.nome}: {self.valore_base}"

class TessituraStatisticaBase(models.Model): # Base
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.statistica.nome}: {self.valore_base}"


# --- OGGETTO E INVENTARIO ---

class Manifesto(A_vista):
    def __str__(self): return f"Manifesto: {self.nome}"

class Inventario(A_vista):
    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventari"
    
    def __str__(self): return f"Inventario: {self.nome}"
    
    def get_oggetti(self, data=None):
        if data is None: data = timezone.now()
        return Oggetto.objects.filter(
            tracciamento_inventario__inventario=self,
            tracciamento_inventario__data_inizio__lte=data,
            tracciamento_inventario__data_fine__isnull=True
        )

class OggettoInInventario(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name="tracciamento_inventario")
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="tracciamento_oggetti")
    data_inizio = models.DateTimeField(default=timezone.now)
    data_fine = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['-data_inizio']

# --- TIPOLOGIA E SATELLITI ---

class TipologiaPersonaggio(models.Model):
    nome = models.CharField(max_length=100, unique=True, default="Standard")
    crediti_iniziali = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    caratteristiche_iniziali = models.IntegerField(default=8)
    giocante = models.BooleanField(default=True)
    class Meta: verbose_name="Tipologia Personaggio"
    def __str__(self): return self.nome

def get_default_tipologia():
    t, _ = TipologiaPersonaggio.objects.get_or_create(nome="Standard")
    return t.pk

class PuntiCaratteristicaMovimento(models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="movimenti_pc")
    importo = models.IntegerField()
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)
    class Meta: verbose_name="Movimento PC"; ordering=['-data']

class CreditoMovimento(models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="movimenti_credito")
    importo = models.DecimalField(max_digits=10, decimal_places=2)
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)
    class Meta: ordering=['-data']
    
class PersonaggioLog(models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="log_eventi")
    data = models.DateTimeField(default=timezone.now)
    testo_log = models.TextField()
    class Meta: ordering=['-data']

# --- OGGETTO (DEFINIZIONE) ---

class OggettoElemento(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': ELEMENTO})

class OggettoStatistica(CondizioneStatisticaMixin): # Modificatori
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    
    class Meta:
        unique_together = ('oggetto', 'statistica')
        
    def __str__(self):
        return f"{self.statistica.nome}: {self.valore}"

class OggettoStatisticaBase(models.Model): # Base
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('oggetto', 'statistica')
        
    def __str__(self):
        return f"{self.statistica.nome}: {self.valore_base}"

class QrCode(models.Model):
    id = models.CharField(primary_key=True, max_length=14, default=generate_short_id, editable=False)
    data_creazione = models.DateTimeField(auto_now_add=True)
    testo = models.TextField(blank=True, null=True)
    vista = models.OneToOneField(A_vista, blank=True, null=True, on_delete=models.SET_NULL)
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
            
class ClasseOggetto(models.Model):
    """
    Definisce una categoria di oggetti (es. Spada, Fucile, Armatura)
    e le regole per l'installazione di Mod e Materia.
    """
    nome = models.CharField(max_length=50, unique=True)
    
    # Limite GLOBALE di Mod installabili su questa classe
    max_mod_totali = models.IntegerField(
        default=0, 
        verbose_name="Max Mod Totali",
        help_text="Numero massimo assoluto di Mod installabili."
    )

    # Relazione per definire i limiti specifici per caratteristica (Through Model)
    limitazioni_mod = models.ManyToManyField(
        Punteggio,
        through='ClasseOggettoLimiteMod',
        related_name='classi_oggetti_regole_mod',
        verbose_name="Limiti Mod per Caratteristica"
    )
    
    # Per le Materia: quali caratteristiche sono permesse
    mattoni_materia_permessi = models.ManyToManyField(
        Punteggio, 
        limit_choices_to={'tipo': CARATTERISTICA},
        related_name='classi_oggetti_materia_permessa',
        blank=True,
        verbose_name="Caratt. Materia Permesse"
    )

    class Meta:
        verbose_name = "Classe Oggetto (Regole)"
        verbose_name_plural = "Classi Oggetto (Regole)"

    def __str__(self):
        return self.nome

class ClasseOggettoLimiteMod(models.Model):
    """
    Definisce quante Mod basate su una certa Caratteristica 
    possono essere montate su una specifica ClasseOggetto.
    Es: Su 'Spada' -> Max 1 Mod di 'Forza'.
    """
    classe_oggetto = models.ForeignKey(ClasseOggetto, on_delete=models.CASCADE)
    caratteristica = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE,
        limit_choices_to={'tipo': CARATTERISTICA}
    )
    max_installabili = models.IntegerField(
        default=1,
        verbose_name="Max Mod di questo tipo",
        help_text="Quante mod con mattoni di questa caratteristica possono essere montate."
    )

    class Meta:
        unique_together = ('classe_oggetto', 'caratteristica')
        verbose_name = "Limite Mod per Caratteristica"
        

class Oggetto(A_vista):
    # --- CAMPI ESISTENTI (Relazioni base) ---
    elementi = models.ManyToManyField(
        Punteggio, blank=True, through='OggettoElemento'
    )
    statistiche = models.ManyToManyField(
        Statistica, through='OggettoStatistica', blank=True, 
        related_name="oggetti_statistiche"
    )
    statistiche_base = models.ManyToManyField(
        Statistica, through='OggettoStatisticaBase', blank=True, 
        related_name='oggetti_statistiche_base'
    )
    aura = models.ForeignKey(
        Punteggio, blank=True, null=True, on_delete=models.SET_NULL, 
        limit_choices_to={'tipo' : AURA}, related_name="oggetti_aura"
    )

    # --- NUOVI CAMPI GESTIONE AVANZATA (Nuovo Sistema) ---
    tipo_oggetto = models.CharField(
        max_length=3, 
        choices=TIPO_OGGETTO_CHOICES, 
        default=TIPO_OGGETTO_FISICO
    )
    
    classe_oggetto = models.ForeignKey(
        ClasseOggetto, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name="Classe (Slot/Regole)"
    )
    
    is_tecnologico = models.BooleanField(default=False, verbose_name="È Tecnologico?")
    
    # Dati Vendita / Gioco
    costo_acquisto = models.IntegerField(default=0, verbose_name="Costo (Crediti)")
    attacco_base = models.CharField(max_length=50, blank=True, null=True, help_text="Es. 2d6")
    in_vendita = models.BooleanField(default=False, verbose_name="In vendita al negozio?")

    # --- ORIGINE (Per Materia/Mod/Innesti) ---
    # Punta a 'Infusione' definita nello stesso file (personaggi/models.py)
    infusione_generatrice = models.ForeignKey(
        'Infusione', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='oggetti_generati',
        help_text="L'infusione da cui deriva questa Materia/Mod/Innesto"
    )

    # --- INCASTONAMENTO (Socketing) ---
    ospitato_su = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='potenziamenti_installati',
        help_text="L'oggetto su cui questo potenziamento è montato."
    )
    
    # --- SLOT CORPO (Per Innesti/Mutazioni) ---
    slot_corpo = models.CharField(
        max_length=2,
        choices=SLOT_CORPO_CHOICES,
        blank=True, null=True,
        help_text="Solo per Innesti e Mutazioni"
    )

    # --- GESTIONE CARICHE ---
    cariche_attuali = models.IntegerField(default=0)

    # --- METODI ---
    @property
    def livello(self): return self.elementi.count()
    
    @property
    def TestoFormattato(self):
        # ... (Logica esistente per il testo, aggiornala se necessario per usare cariche) ...
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
            # Se l'oggetto era montato su qualcosa, smontalo
            if self.ospitato_su:
                self.ospitato_su = None
                self.save()

            curr = self.tracciamento_inventario.filter(data_fine__isnull=True).first()
            if curr:
                if curr.inventario == nuovo: return
                curr.data_fine = data; curr.save()
            if nuovo: OggettoInInventario.objects.create(oggetto=self, inventario=nuovo, data_inizio=data)

    def clean(self):
        # Validazioni di base per il database
        if self.ospitato_su == self:
            raise ValidationError("Un oggetto non può essere installato su se stesso.")
        
        # Le validazioni complesse (limiti mod, tipi materia, ecc.) 
        # verranno gestite nel Service Layer (Passo 2/3) per avere messaggi d'errore migliori
        # e accesso ai dati correlati senza appesantire il save() del modello base.

class Personaggio(Inventario):
    proprietario = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="personaggi", null=True, blank=True)
    tipologia = models.ForeignKey(TipologiaPersonaggio, on_delete=models.PROTECT, related_name="personaggi", default=get_default_tipologia)
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
            max_val = 0
            for k, v in p.items():
                if k in others and v > max_val: max_val = v
            p[agen.nome] = max_val
        self._punteggi_base_cache = p
        return p
    @property
    def caratteristiche_base(self):
        return {k:v for k,v in self.punteggi_base.items() if Punteggio.objects.filter(nome=k, tipo=CARATTERISTICA).exists()}
    def get_valore_aura_effettivo(self, aura):
        pb = self.punteggi_base
        if aura.is_generica: return max([v for k,v in pb.items() if Punteggio.objects.filter(nome=k, tipo=AURA, is_generica=False).exists()] or [0])
        return pb.get(aura.nome, 0)
    
    def valida_acquisto_tecnica(self, t):
        # 1. Controllo Aura
        if not t.aura_richiesta: 
            return False, "Aura mancante."
        
        if t.livello > self.get_valore_aura_effettivo(t.aura_richiesta): 
            return False, "Livello tecnica superiore al valore Aura."

        # 2. Controllo Requisiti Mattoni (Quantità vs Caratteristica)
        from collections import Counter
        # Ottieni gli ID dei mattoni della tecnica
        mattoni_tecnica_ids = list(t.mattoni.values_list('id', flat=True))
        cnt = Counter(mattoni_tecnica_ids)
        base = self.caratteristiche_base
        
        for mid, c in cnt.items():
            try:
                m = Mattone.objects.get(pk=mid)
                if c > base.get(m.caratteristica_associata.nome, 0): 
                    return False, f"Requisito {m.nome} non soddisfatto (Richiede {c}, hai {base.get(m.caratteristica_associata.nome, 0)})."
            except: pass

        # 3. Controllo Modello Aura (Proibiti e Obbligatori)
        modello = self.modelli_aura.filter(aura=t.aura_richiesta).first()
        
        if modello:
            set_mattoni_tecnica = set(mattoni_tecnica_ids)
            
            # A. Check Proibiti (Nessuno dei mattoni della tecnica deve essere proibito)
            ids_proibiti = set(modello.mattoni_proibiti.values_list('id', flat=True))
            intersezione_proibiti = set_mattoni_tecnica.intersection(ids_proibiti)
            
            if intersezione_proibiti:
                nomi_vietati = ", ".join(Mattone.objects.filter(id__in=intersezione_proibiti).values_list('nome', flat=True))
                return False, f"Usa mattoni proibiti dal tuo modello aura: {nomi_vietati}."

            # B. Check Obbligatori (La tecnica DEVE contenere TUTTI i tipi di mattoni obbligatori elencati)
            ids_obbligatori = set(modello.mattoni_obbligatori.values_list('id', flat=True))
            
            # Se ci sono obblighi, verifichiamo che l'insieme degli obbligatori sia un sottoinsieme dei mattoni della tecnica
            if ids_obbligatori and not ids_obbligatori.issubset(set_mattoni_tecnica):
                mancanti = ids_obbligatori - set_mattoni_tecnica
                nomi_mancanti = ", ".join(Mattone.objects.filter(id__in=mancanti).values_list('nome', flat=True))
                return False, f"La tecnica non contiene i mattoni obbligatori richiesti dal modello: {nomi_mancanti}."

        return True, "OK"
    
    @property
    def modificatori_calcolati(self):
        if hasattr(self, '_modificatori_calcolati_cache'): 
            return self._modificatori_calcolati_cache
        
        # Import locale per evitare circular dependency con oggetti.models
        # Assumiamo che le costanti siano state definite in oggetti/models.py come da Passo 1
        from oggetti.models import (
            TIPO_OGGETTO_FISICO, 
            TIPO_OGGETTO_MATERIA, 
            TIPO_OGGETTO_MOD, 
            TIPO_OGGETTO_INNESTO, 
            TIPO_OGGETTO_MUTAZIONE
        )

        mods = {}
        
        # Funzione helper interna per sommare i modificatori
        def _add(p, t, v):
            if not p: return
            if p not in mods: mods[p] = {'add': 0.0, 'mol': 1.0}
            valore = float(v)
            if t == MODIFICATORE_ADDITIVO: mods[p]['add'] += valore
            elif t == MODIFICATORE_MOLTIPLICATIVO: mods[p]['mol'] *= valore 

        # --- 1. ABILITÀ (Logica esistente) ---
        for l in AbilitaStatistica.objects.filter(abilita__personaggioabilita__personaggio=self).select_related('statistica'): 
            _add(l.statistica.parametro, l.tipo_modificatore, l.valore)
        
        # --- 2. OGGETTI E POTENZIAMENTI (Nuova Logica) ---
        # Recuperiamo tutti gli oggetti nell'inventario del personaggio
        # Usiamo prefetch_related per ottimizzare le query:
        # - oggettostatistica_set: i modificatori dell'oggetto stesso
        # - potenziamenti_installati: Materia/Mod montate sull'oggetto
        # - potenziamenti_installati__oggettostatistica_set: i modificatori dei potenziamenti
        
        oggetti_inventario = self.get_oggetti().prefetch_related(
            'oggettostatistica_set__statistica',
            'potenziamenti_installati__oggettostatistica_set__statistica'
        )
        
        for oggetto in oggetti_inventario:
            is_oggetto_attivo = False
            
            # A. Determina se l'oggetto genitore è attivo
            if oggetto.tipo_oggetto == TIPO_OGGETTO_FISICO:
                # Assumiamo che gli oggetti fisici in inventario siano attivi (o equipaggiati)
                is_oggetto_attivo = True
            elif oggetto.tipo_oggetto == TIPO_OGGETTO_MUTAZIONE:
                # Le mutazioni sono sempre attive
                is_oggetto_attivo = True
            elif oggetto.tipo_oggetto == TIPO_OGGETTO_INNESTO:
                # Gli innesti sono attivi solo se hanno cariche
                if oggetto.cariche_attuali > 0:
                    is_oggetto_attivo = True
            
            # Nota: MATERIA e MOD sciolte in inventario (non montate) sono ignorate qui (rimangono False)

            if is_oggetto_attivo:
                # B. Applica i modificatori dell'oggetto stesso
                for stat_link in oggetto.oggettostatistica_set.all():
                    _add(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)
                
                # C. Controlla i potenziamenti installati (Materia/Mod)
                # 'potenziamenti_installati' è il related_name definito in Oggetto.ospitato_su
                for potenziamento in oggetto.potenziamenti_installati.all():
                    is_potenziamento_attivo = False
                    
                    if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA:
                        # La Materia è attiva se è incastonata (che è vero se siamo in questo loop)
                        is_potenziamento_attivo = True
                    
                    elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD:
                        # La Mod è attiva se incastonata AND ha cariche > 0
                        if potenziamento.cariche_attuali > 0:
                            is_potenziamento_attivo = True
                    
                    # Se il potenziamento è attivo, somma le sue statistiche al personaggio
                    if is_potenziamento_attivo:
                        for stat_link_pot in potenziamento.oggettostatistica_set.all():
                            _add(stat_link_pot.statistica.parametro, stat_link_pot.tipo_modificatore, stat_link_pot.valore)

        # --- 3. CARATTERISTICHE (Logica esistente) ---
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
        """
        Genera il testo formattato (descrizione + formule) per un dato item.
        Gestisce logiche condizionali, modelli aura e formule multiple.
        """
        if not item: return ""
        
        # --- LOGICA OGGETTO ---
        if isinstance(item, Oggetto):
            stats = item.oggettostatisticabase_set.select_related('statistica').all()
            item_mods = item.oggettostatistica_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura, 'item_modifiers': item_mods}
            return formatta_testo_generico(
                item.testo, 
                formula=getattr(item, 'formula', None), 
                statistiche_base=stats, 
                personaggio=self, 
                context=ctx
            )
            
        # --- LOGICA INFUSIONE ---
        elif isinstance(item, Infusione):
            stats = item.infusionestatisticabase_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura_richiesta}
            return formatta_testo_generico(
                item.testo, 
                statistiche_base=stats, 
                personaggio=self, 
                context=ctx
            )

        # --- LOGICA ATTIVATA ---
        elif isinstance(item, Attivata):
            stats = item.attivatastatisticabase_set.select_related('statistica').all()
            return formatta_testo_generico(
                item.testo, 
                statistiche_base=stats, 
                personaggio=self
            )

        # --- LOGICA TESSITURA ---
        elif isinstance(item, Tessitura):
            stats = item.tessiturastatisticabase_set.select_related('statistica').all()
            
            # 1. CHECK PRELIMINARE: La formula usa il parametro {elem}?
            # Se NO, non ha senso generare varianti multiple basate sull'elemento.
            formula_text = item.formula or ""
            if "{elem}" not in formula_text:
                ctx = {
                    'livello': item.livello, 
                    'aura': item.aura_richiesta, 
                    'elemento': item.elemento_principale
                }
                return formatta_testo_generico(
                    item.testo, 
                    formula=formula_text, 
                    statistiche_base=stats, 
                    personaggio=self, 
                    context=ctx
                )

            # 2. LOGICA AVANZATA (Formule Multiple)
            modello = self.modelli_aura.filter(aura=item.aura_richiesta).first()
            elementi_map = {} 
            
            # Elemento Principale (Base)
            if item.elemento_principale:
                elementi_map[item.elemento_principale.id] = item.elemento_principale
            
            if modello:
                punteggi_pg = self.punteggi_base 

                def verifica_requisiti(requisiti_queryset):
                    for req_link in requisiti_queryset:
                        nome_req = req_link.requisito.nome
                        valore_posseduto = punteggi_pg.get(nome_req, 0)
                        if valore_posseduto < req_link.valore:
                            return False
                    return True

                # A. Doppia Formula
                if modello.usa_doppia_formula and modello.elemento_secondario:
                    attiva_doppia = True
                    if modello.usa_condizione_doppia:
                        attiva_doppia = verifica_requisiti(modello.req_doppia_rel.select_related('requisito').all())
                    
                    if attiva_doppia:
                        elementi_map[modello.elemento_secondario.id] = modello.elemento_secondario

                # B. Formula per Caratteristica
                if modello.usa_formula_per_caratteristica:
                    attiva_caratt = True
                    if modello.usa_condizione_caratt:
                        attiva_caratt = verifica_requisiti(modello.req_caratt_rel.select_related('requisito').all())
                    
                    if attiva_caratt:
                        elementi_extra = Punteggio.objects.filter(
                            tipo=ELEMENTO, 
                            caratteristica_relativa__nome__in=punteggi_pg.keys()
                        )
                        for el in elementi_extra:
                            if punteggi_pg.get(el.caratteristica_relativa.nome, 0) > 0:
                                elementi_map[el.id] = el
                
                # C. Formula per Mattone (NUOVO)
                if modello.usa_formula_per_mattone:
                    attiva_mattone = True
                    if modello.usa_condizione_mattone:
                        attiva_mattone = verifica_requisiti(modello.req_mattone_rel.select_related('requisito').all())
                    
                    if attiva_mattone:
                        # Recupera le caratteristiche associate ai mattoni di questa specifica tessitura
                        # Nota: item qui è la Tessitura
                        caratt_mattoni_ids = item.mattoni.values_list('caratteristica_associata', flat=True)
                        
                        # Trova gli Elementi che sono "relativi" a quelle caratteristiche
                        elementi_da_mattoni = Punteggio.objects.filter(
                            tipo=ELEMENTO,
                            caratteristica_relativa__id__in=caratt_mattoni_ids
                        )
                        
                        for el in elementi_da_mattoni:
                            # Aggiungiamo alla mappa (evita duplicati grazie alla chiave id)
                            elementi_map[el.id] = el

            elementi_da_calcolare = list(elementi_map.values())

            # Fallback se nessun elemento è trovato (raro se {elem} è presente, ma per sicurezza)
            if not elementi_da_calcolare:
                ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': None}
                return formatta_testo_generico(
                    item.testo, 
                    formula=item.formula, 
                    statistiche_base=stats, 
                    personaggio=self, 
                    context=ctx
                )

            # 3. GENERAZIONE OUTPUT MULTIPLO
            # A. Descrizione (usa elemento principale come contesto base)
            ctx_base = {
                'livello': item.livello, 
                'aura': item.aura_richiesta, 
                'elemento': item.elemento_principale
            }
            descrizione_html = formatta_testo_generico(
                item.testo, 
                formula=None, 
                statistiche_base=stats, 
                personaggio=self, 
                context=ctx_base
            )
            
            # B. Loop Formule
            formule_html = []
            for elem in elementi_da_calcolare:
                val_caratt = 0
                if elem.caratteristica_relativa:
                    val_caratt = self.caratteristiche_base.get(elem.caratteristica_relativa.nome, 0)
                
                ctx_loop = {
                    'livello': item.livello, 
                    'aura': item.aura_richiesta, 
                    'elemento': elem,
                    'caratteristica_associata_valore': val_caratt
                }
                
                risultato_formula = formatta_testo_generico(
                    None, 
                    formula=item.formula, 
                    statistiche_base=stats, 
                    personaggio=self, 
                    context=ctx_loop, 
                    solo_formula=True,
                )
                
                valore_pura_formula = risultato_formula.replace("<strong>Formula:</strong>", "").strip()
                
                if valore_pura_formula:
                    style_container = f"margin-top: 4px; padding: 4px 8px; border-left: 3px solid {elem.colore}; background-color: rgba(255,255,255,0.05); border-radius: 0 4px 4px 0;"
                    style_label = f"color: {elem.colore}; font-weight: bold; margin-right: 6px;"
                    
                    block = (
                        f"<div style='{style_container}'>"
                        f"<span style='{style_label}'>{elem.nome}:</span>{valore_pura_formula}"
                        f"</div>"
                    )
                    formule_html.append(block)

            if formule_html:
                separator = "<hr style='margin: 10px 0; border: 0; border-top: 1px dashed #555;'/>"
                sezione_formule = "".join(formule_html)
                return f"{descrizione_html}{separator}<div style='font-size: 0.95em;'><strong>Formule:</strong>{sezione_formule}</div>"
            
            return descrizione_html

        return ""
    
    def get_valore_statistica(self, sigla):
        """
        Recupera il valore totale (base + modificatori) di una statistica data la sua SIGLA.
        Utile per statistiche derivate come RCT (Tecniche), RCO (Oggetti), RCA (Abilità).
        """
        try:
            # Cerca la statistica per sigla (es. 'RCT', 'RCO')
            stat_obj = Statistica.objects.filter(sigla=sigla).first()
            if not stat_obj or not stat_obj.parametro:
                return 0
            
            # Recupera i modificatori calcolati per quel parametro
            mods = self.modificatori_calcolati.get(stat_obj.parametro, {'add': 0, 'mol': 1.0})
            
            # Calcolo valore: (BaseDefault + Add) * Mol
            # Nota: Le statistiche di sconto spesso partono da base 0
            valore_base = stat_obj.valore_base_predefinito
            valore_finale = (valore_base + mods['add']) * mods['mol']
            return int(round(valore_finale))
        except Exception:
            return 0

    def get_costo_item_scontato(self, item):
        """
        Calcola il costo effettivo in crediti di un oggetto/tecnica applicando gli sconti.
        Restituisce il valore intero scontato.
        """
        # 1. Determina il costo base
        costo_base = 0
        if hasattr(item, 'costo_crediti'):
            costo_base = item.costo_crediti
            # Per le tecniche (Infusione, ecc.) costo_crediti è una property calcolata (livello * 100)
            # Per Oggetti e Abilità è un campo del database.
        
        if costo_base <= 0: 
            return 0
        
        # 2. Determina la percentuale di sconto in base al tipo
        sconto_perc = 0
        
        if isinstance(item, (Infusione, Tessitura, Attivata)):
            # RCT: Riduzione Costi Tecniche
            sconto_perc = self.get_valore_statistica('RCT')
            
        elif isinstance(item, Oggetto):
            # RCO: Riduzione Costi Oggetti
            sconto_perc = self.get_valore_statistica('RCO')
            
        elif isinstance(item, Abilita):
            # RCA: Riduzione Costi Abilità
            sconto_perc = self.get_valore_statistica('RCA')
            
        # 3. Applica lo sconto
        if sconto_perc > 0:
            # Limite massimo sconto (es. 90% per evitare costi negativi o zero se non voluto)
            sconto_perc = min(sconto_perc, 50) # Limite massimo di sconto al 50% 
            riduzione = (costo_base * sconto_perc) / 100
            return int(max(0, costo_base - riduzione))
            
        return int(costo_base)
        

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

class TransazioneSospesa(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    mittente = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="transazioni_in_uscita_sospese")
    richiedente = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="transazioni_in_entrata_sospese")
    data_richiesta = models.DateTimeField(default=timezone.now)
    stato = models.CharField(max_length=10, choices=STATO_TRANSAZIONE_CHOICES, default=STATO_TRANSAZIONE_IN_ATTESA)
    class Meta: ordering=['-data_richiesta']
    def accetta(self):
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA: raise Exception("Processata")
        self.oggetto.sposta_in_inventario(self.richiedente); self.stato = STATO_TRANSAZIONE_ACCETTATA; self.save()
    def rifiuta(self):
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA: raise Exception("Processata")
        self.stato = STATO_TRANSAZIONE_RIFIUTATA; self.save()

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
    
    class Meta: 
        ordering=['-data_invio']
    
class LetturaMessaggio(models.Model):
    messaggio = models.ForeignKey(Messaggio, on_delete=models.CASCADE, related_name="stati_lettura")
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="messaggi_stati")
    letto = models.BooleanField(default=False)
    data_lettura = models.DateTimeField(null=True, blank=True)
    cancellato = models.BooleanField(default=False)  # Soft delete per il ricevente

    class Meta:
        unique_together = ('messaggio', 'personaggio')
        verbose_name = "Stato Lettura Messaggio"
        verbose_name_plural = "Stati Lettura Messaggi"

    def __str__(self):
        return f"{self.personaggio.nome} - {self.messaggio.titolo} ({'Letto' if self.letto else 'Non letto'})"

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
    
    
class PropostaTecnica(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name='proposte_tecniche')
    tipo = models.CharField(max_length=3, choices=TIPO_PROPOSTA_CHOICES)
    stato = models.CharField(max_length=15, choices=STATO_PROPOSTA_CHOICES, default=STATO_PROPOSTA_BOZZA)
    
    nome = models.CharField(max_length=100)
    descrizione = models.TextField("Ragionamento/Descrizione")
    
    # AGGIUNTO related_name='proposte_aura'
    aura = models.ForeignKey(
        Punteggio, 
        on_delete=models.CASCADE, 
        limit_choices_to={'tipo': AURA},
        related_name='proposte_aura'
    )
    
    # AGGIUNTO related_name='proposte_in_cui_usato'
    mattoni = models.ManyToManyField(
        Mattone, 
        through='PropostaTecnicaMattone',
        related_name='proposte_in_cui_usato'
    )
    
    costo_invio_pagato = models.IntegerField(default=0, help_text="Crediti spesi per l'invio")
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_invio = models.DateTimeField(null=True, blank=True)
    
    note_staff = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Proposta Tecnica"
        verbose_name_plural = "Proposte Tecniche"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome} ({self.personaggio.nome})"

    @property
    def livello(self):
        return self.mattoni.count()

class PropostaTecnicaMattone(models.Model):
    proposta = models.ForeignKey(PropostaTecnica, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    # L'ordine è importante per le tessere
    ordine = models.IntegerField(default=0) 

    class Meta:
        ordering = ['ordine']