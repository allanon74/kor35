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
from cms.models.pluginmodel import CMSPlugin
from django.utils.html import format_html
from icon_widget.fields import CustomIconField

# --- COSTANTI DI SISTEMA (FALLBACK) ---
COSTO_PER_MATTONE_INFUSIONE = 100
COSTO_PER_MATTONE_TESSITURA = 100
COSTO_PER_MATTONE_OGGETTO = 100
COSTO_PER_MATTONE_CREAZIONE = 10 # Costo invio proposta
COSTO_DEFAULT_PER_MATTONE = 100
COSTO_DEFAULT_INVIO_PROPOSTA = 10

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

# --- COSTANTI SLOT CORPO ---
SLOT_TESTA_1 = 'HD1'
SLOT_TESTA_2 = 'HD2'
SLOT_TRONCO_1 = 'TR1'
SLOT_TRONCO_2 = 'TR2'
SLOT_BRACCIO_DX = 'RA'
SLOT_BRACCIO_SX = 'LA'
SLOT_GAMBA_DX = 'RL'
SLOT_GAMBA_SX = 'LL'

SLOT_CORPO_CHOICES = [
    (SLOT_TESTA_1, 'Testa 1'),
    (SLOT_TESTA_2, 'Testa 2'),
    (SLOT_TRONCO_1, 'Tronco 1'),
    (SLOT_TRONCO_2, 'Tronco 2'),
    (SLOT_BRACCIO_DX, 'Braccio Dx'),
    (SLOT_BRACCIO_SX, 'Braccio Sx'),
    (SLOT_GAMBA_DX, 'Gamba Dx'),
    (SLOT_GAMBA_SX, 'Gamba Sx'),
]

def get_testo_rango(valore):
    try: valore = int(valore)
    except (ValueError, TypeError): return ""
    if valore <= 0: return "Mondano! "
    elif valore == 1: return "" 
    elif valore == 2: return "Eroico! "
    elif valore == 3: return "Leggendario! "
    elif valore == 4: return "Mitologico! "
    elif valore == 5: return "Divino! "
    elif valore == 6: return "Cosmico! "
    else: return f"Cosmico {valore - 6}-esimo! "

def _get_icon_color_from_bg(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return 'black' if ((r*299)+(g*587)+(b*114))/1000 > 128 else 'white'
    except Exception: return 'black'

def generate_short_id(length=14):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def evaluate_expression(expression, context_dict):
    if not expression: return 0
    if "__" in expression or "import" in expression or "lambda" in expression: return 0
    safe_context = {str(k).lower(): v for k, v in context_dict.items() if k}
    safe_context.update({'max': max, 'min': min, 'abs': abs, 'int': int, 'round': round})
    try: return eval(str(expression).lower(), {"__builtins__": {}}, safe_context)
    except Exception: return 0

def formatta_testo_generico(testo, formula=None, statistiche_base=None, personaggio=None, context=None, solo_formula=False):
    testo_out = testo or ""
    formula_out = formula or ""
    if not testo_out and not formula_out: return ""

    base_values = {}
    eval_context = {}

    if statistiche_base:
        for item in statistiche_base:
            param = getattr(item.statistica, 'parametro', None) if hasattr(item, 'statistica') else None
            val = getattr(item, 'valore_base', 0)
            if param:
                base_values[param] = val
                eval_context[param] = val

    mods_attivi = {}
    if personaggio:
        # 1. Prendi i modificatori GLOBALI (senza condizioni)
        mods_attivi = copy.deepcopy(personaggio.modificatori_calcolati)
        
        # 2. Se c'è un contesto (es. stiamo processando una formula Fuoco), 
        # calcola i modificatori CONDIZIONALI
        if context:
            extra_mods = personaggio.get_modificatori_extra_da_contesto(context)
            
            # Fondi extra_mods dentro mods_attivi
            for param, valori in extra_mods.items():
                if param not in mods_attivi:
                    mods_attivi[param] = {'add': 0.0, 'mol': 1.0}
                mods_attivi[param]['add'] += valori['add']
                mods_attivi[param]['mol'] *= valori['mol']

        eval_context.update(personaggio.caratteristiche_base)
        for param, mod_data in mods_attivi.items():
            val_base = eval_context.get(param, 0) 
            val_finale = (val_base + mod_data['add']) * mod_data['mol']
            eval_context[param] = val_finale

    if context:
        eval_context.update(context) 
        if 'caratteristica_associata_valore' in context:
             eval_context['caratt'] = context['caratteristica_associata_valore']

    testo_metatalenti = ""
    if context:
        item_modifiers = context.get('item_modifiers', [])
        current_aura = context.get('aura')
        current_elem = context.get('elemento')

        for mod in item_modifiers:
            passa_aura = not mod.usa_limitazione_aura or (current_aura and mod.limit_a_aure.filter(pk=current_aura.pk).exists())
            passa_elem = not mod.usa_limitazione_elemento or (current_elem and mod.limit_a_elementi.filter(pk=current_elem.pk).exists())
            passa_text = True
            if mod.usa_condizione_text and mod.condizione_text:
                local_ctx = eval_context.copy()
                if hasattr(mod, 'mattone') and mod.mattone.caratteristica_associata:
                    nome_c = mod.mattone.caratteristica_associata.nome
                    local_ctx['caratt'] = eval_context.get(nome_c, 0)
                if not evaluate_expression(mod.condizione_text, local_ctx): passa_text = False

            if passa_aura and passa_elem and passa_text:
                p = mod.statistica.parametro
                if p:
                    if p not in mods_attivi: mods_attivi[p] = {'add': 0, 'mol': 1.0}
                    if mod.tipo_modificatore == MODIFICATORE_ADDITIVO: mods_attivi[p]['add'] += mod.valore
                    elif mod.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO: mods_attivi[p]['mol'] *= float(mod.valore)

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
                    val_caratt = caratteristiche_pg.get(mattone.caratteristica_associata.nome, 0)
                    applica = (funz in [META_VALORE_PUNTEGGIO, META_SOLO_TESTO]) or (funz == META_LIVELLO_INFERIORE and livello_item <= val_caratt)
                    
                    if applica:
                        if funz in [META_VALORE_PUNTEGGIO, META_LIVELLO_INFERIORE]:
                            for stat_m in mattone.mattonestatistica_set.select_related('statistica').all():
                                p = stat_m.statistica.parametro
                                b = stat_m.valore * val_caratt
                                if p:
                                    if p not in mods_attivi: mods_attivi[p] = {'add': 0, 'mol': 1.0}
                                    if stat_m.tipo_modificatore == MODIFICATORE_ADDITIVO: mods_attivi[p]['add'] += b
                                    elif stat_m.tipo_modificatore == MODIFICATORE_MOLTIPLICATIVO: mods_attivi[p]['mol'] *= float(b)
                        if mattone.testo_addizionale:
                            def repl(m): return str(val_caratt * (int(m.group(1)) if m.group(1) else 1))
                            parsed = re.sub(r'\{(?:(\d+)\*)?caratt\}', repl, mattone.testo_addizionale)
                            testo_metatalenti += f"<br><em>Metatalento ({mattone.nome}):</em> {parsed}"

    def resolve_placeholder(match):
        expr = match.group(1).strip()
        val_math = evaluate_expression(expr, eval_context)
        if val_math or val_math == 0: 
             try: return str(int(round(float(val_math))))
             except: return str(val_math)
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
        except: return match.group(0)

    def replace_conditional_block(match):
        if evaluate_expression(match.group(1), eval_context): return match.group(2)
        return ""
    
    if solo_formula: testo_metatalenti = ""
    testo_completo = testo_out + testo_metatalenti
    
    if context:
        if context.get('elemento'):
            elem_obj = context['elemento']
            repl = getattr(elem_obj, 'dichiarazione', None) or (elem_obj.mattone.dichiarazione if hasattr(elem_obj, 'mattone') else elem_obj.nome)
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

    pattern_if = re.compile(r'\{if\s+(.+?)\}(.*?)\{endif\}', re.DOTALL | re.IGNORECASE)
    testo_finale = pattern_if.sub(replace_conditional_block, testo_completo)
    formula_finale = pattern_if.sub(replace_conditional_block, formula_out)

    testo_finale = re.sub(r'\{([^{}]+)\}', resolve_placeholder, testo_finale)
    formula_finale = re.sub(r'\{([^{}]+)\}', resolve_placeholder, formula_finale)
    
    parts = []
    if testo_finale: parts.append(testo_finale)
    if formula_finale:
        if testo_finale: parts.append("<br/><hr style='margin:5px 0; border:0; border-top:1px dashed #ccc;'/>")
        parts.append(f"<strong>Formula:</strong> {formula_finale}")
        
    return "".join(parts)

# --- TIPI ---
CARATTERISTICA = "CA"; STATISTICA = "ST"; ELEMENTO = "EL"; AURA = "AU"; CONDIZIONE = "CO"; CULTO = "CU"; VIA = "VI"; ARTE = "AR"; ARCHETIPO = "AR"
punteggi_tipo = [(CARATTERISTICA, 'Caratteristica'), (STATISTICA, 'Statistica'), (ELEMENTO, 'Elemento'), (AURA, 'Aura'), (CONDIZIONE, 'Condizione'), (CULTO, 'Culto'), (VIA, 'Via'), (ARTE, 'Arte'), (ARCHETIPO, 'Archetipo')]
TIER_1 = "T1"; TIER_2 = "T2"; TIER_3 = "T3"; TIER_4 = "T4"
tabelle_tipo = [(TIER_1, 'Tier 1'), (TIER_2, 'Tier 2'), (TIER_3, 'Tier 3'), (TIER_4, 'Tier 4')]
MODIFICATORE_ADDITIVO = 'ADD'; MODIFICATORE_MOLTIPLICATIVO = 'MOL'
MODIFICATORE_CHOICES = [(MODIFICATORE_ADDITIVO, 'Additivo (+N)'), (MODIFICATORE_MOLTIPLICATIVO, 'Moltiplicativo (xN)')]
META_NESSUN_EFFETTO = 'NE'; META_VALORE_PUNTEGGIO = 'VP'; META_SOLO_TESTO = 'TX'; META_LIVELLO_INFERIORE = 'LV'
METATALENTO_CHOICES = [(META_NESSUN_EFFETTO, 'Nessun Effetto'), (META_VALORE_PUNTEGGIO, 'Valore per Punteggio'), (META_SOLO_TESTO, 'Solo Testo Addizionale'), (META_LIVELLO_INFERIORE, 'Solo abilità con livello pari o inferiore')]

class A_modello(models.Model):
    id = models.AutoField("Codice Identificativo", primary_key=True)
    class Meta: abstract = True
        
class A_vista(models.Model):
    id = models.AutoField(primary_key=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=100)
    testo = models.TextField(blank=True, null=True)
    def __str__(self): return f"{self.nome} ({self.id})"
    class Meta: ordering = ['-data_creazione']; verbose_name = "Elemento dell'Oggetto"; verbose_name_plural = "Elementi dell'Oggetto"

class CondizioneStatisticaMixin(models.Model):
    usa_limitazione_aura = models.BooleanField("Usa Limitazione Aura", default=False)
    limit_a_aure = models.ManyToManyField('Punteggio', blank=True, limit_choices_to={'tipo': AURA}, related_name="%(class)s_limit_aure", verbose_name="Aure consentite")
    usa_limitazione_elemento = models.BooleanField("Usa Limitazione Elemento", default=False)
    limit_a_elementi = models.ManyToManyField('Punteggio', blank=True, limit_choices_to={'tipo': ELEMENTO}, related_name="%(class)s_limit_elementi", verbose_name="Elementi consentiti")
    usa_condizione_text = models.BooleanField("Usa Condizione Testuale", default=False)
    condizione_text = models.CharField("Condizione", max_length=255, blank=True, null=True, help_text="Es. caratt>6")
    class Meta: abstract = True

class Tabella(A_modello):
    nome = models.CharField(max_length=90)
    descrizione = models.TextField(null=True, blank=True)
    class Meta: verbose_name = "Tabella"; verbose_name_plural = "Tabelle"
    def __str__(self): return self.nome

class Tier(Tabella):
    tipo = models.CharField(choices=tabelle_tipo, max_length=2)
    foto = models.ImageField(upload_to='tiers/', null=True, blank=True)
    class Meta: verbose_name = "Tier"; verbose_name_plural = "Tiers"

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
    # NUOVI FLAG: Cosa può produrre questa Aura?
    produce_mod = models.BooleanField(default=False, verbose_name="Produce MOD (Oggetti)")
    produce_materia = models.BooleanField(default=False, verbose_name="Produce MATERIA (Oggetti)")
    produce_innesti = models.BooleanField(default=False, verbose_name="Produce INNESTI (Corpo)")
    produce_mutazioni = models.BooleanField(default=False, verbose_name="Produce MUTAZIONI (Corpo)")
    
    # COSTI CREAZIONE / ACQUISTO (Tecnica approvata)
    stat_costo_creazione_infusione = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_inf')
    stat_costo_creazione_tessitura = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_tes')
    stat_costo_acquisto_infusione = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_acquisto_inf')
    stat_costo_acquisto_tessitura = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_acquisto_tes')
    
    # NUOVI CAMPI: COSTO INVIO PROPOSTA (Burocrazia)
    stat_costo_invio_proposta_infusione = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_invio_prop_inf', verbose_name="Stat. Costo Invio Proposta (Inf)")
    stat_costo_invio_proposta_tessitura = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_invio_prop_tes', verbose_name="Stat. Costo Invio Proposta (Tes)")

    # COSTI CRAFTING (Forgiatura)
    stat_costo_forgiatura = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_forgia')
    stat_tempo_forgiatura = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_tempo_forgia')
    
    caratteristica_relativa = models.ForeignKey("Punteggio", on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, null=True, blank=True, related_name="punteggi_caratteristica")
    modifica_statistiche = models.ManyToManyField('Statistica', through='CaratteristicaModificatore', related_name='modificata_da_caratteristiche', blank=True)
    aure_infusione_consentite = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='puo_essere_infusa_in')    
    class Meta: verbose_name = "Punteggio"; verbose_name_plural = "Punteggi"; ordering = ['tipo', 'ordine', 'nome']
    @property
    def icona_url(self): return f"{settings.MEDIA_URL}{self.icona}" if self.icona else None
    @property
    def icona_html(self):
        if self.icona and self.colore: return format_html('<div style="width: 24px; height: 24px; background-color: {}; mask-image: url({}); -webkit-mask-image: url({}); mask-size: contain; -webkit-mask-size: contain; display: inline-block; vertical-align: middle;"></div>', self.colore, self.icona_url, self.icona_url)
        return ""
    def icona_cerchio(self, inverted=True):
        if not self.icona or not self.colore: return ""
        bg = _get_icon_color_from_bg(self.colore) if inverted else self.colore
        fg = self.colore if inverted else _get_icon_color_from_bg(self.colore)
        return format_html('<div style="display: inline-block; width: 30px; height: 30px; background-color: {}; border-radius: 50%; vertical-align: middle; text-align: center; line-height: 30px;"><div style="display: inline-block; width: 24px; height: 24px; vertical-align: middle; background-color: {}; mask-image: url({}); -webkit-mask-image: url({}); mask-size: contain; -webkit-mask-size: contain;"></div></div>', bg, fg, self.icona_url, self.icona_url)
    @property
    def icona_cerchio_html(self): return self.icona_cerchio(inverted=False)
    @property
    def icona_cerchio_inverted_html(self): return self.icona_cerchio(inverted=True)
    def __str__(self): return f"{self.tipo} - {self.nome}"

class Caratteristica(Punteggio):
    class Meta: proxy = True; verbose_name = "Caratteristica"; verbose_name_plural = "Caratteristiche"

class Statistica(Punteggio):
    parametro = models.CharField(max_length=10, unique=True, blank=True, null=True)
    valore_predefinito = models.IntegerField(default=0)
    valore_base_predefinito = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    is_primaria = models.BooleanField(default=False)
    def save(self, *args, **kwargs): self.tipo = STATISTICA; super().save(*args, **kwargs)
    class Meta: verbose_name = "Statistica"; verbose_name_plural = "Statistiche"
    @classmethod
    def get_help_text_parametri(cls, extra_params=None):
        stats = cls.objects.filter(parametro__isnull=False).exclude(parametro__exact='').order_by('nome')
        items = [f"&bull; <b>{{{s.parametro}}}</b>: {s.nome}" for s in stats]
        if extra_params: items.extend([f"&bull; <b>{p_code}</b>: {p_desc}" for p_code, p_desc in extra_params])
        return mark_safe("<b>Variabili disponibili:</b><br>" + "<br>".join(items))

class Mattone(Punteggio):
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="mattoni_aura")
    caratteristica_associata = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, related_name="mattoni_caratteristica")
    descrizione_mattone = models.TextField(blank=True, null=True)
    descrizione_metatalento = models.TextField(blank=True, null=True)
    testo_addizionale = models.TextField(blank=True, null=True)
    dichiarazione = models.TextField("Dichiarazione", blank=True, null=True)
    funzionamento_metatalento = models.CharField(max_length=2, choices=METATALENTO_CHOICES, default=META_NESSUN_EFFETTO)
    statistiche = models.ManyToManyField(Statistica, through='MattoneStatistica', blank=True, related_name="mattoni_statistiche")
    def save(self, *args, **kwargs): self.is_mattone = True; super().save(*args, **kwargs)
    class Meta: verbose_name = "Mattone"; verbose_name_plural = "Mattoni"; unique_together = ('aura', 'caratteristica_associata'); ordering = ['tipo', 'ordine', 'nome'] 

class MattoneStatistica(CondizioneStatisticaMixin):
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: unique_together = ('mattone', 'statistica')
    def __str__(self): return f"{self.statistica.nome}: {self.valore}"

class Aura(Punteggio):
    class Meta: proxy = True; verbose_name = "Aura"; verbose_name_plural = "Aure"
    def save(self, *args, **kwargs): self.type = AURA; super().save(*args, **kwargs)

class ModelloAuraRequisitoDoppia(models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_doppia_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)
        
class ModelloAuraRequisitoMattone(models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_mattone_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

class ModelloAuraRequisitoCaratt(models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_caratt_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

class ModelloAura(models.Model):
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="modelli_definiti")
    nome = models.CharField(max_length=100)
    descrizione = models.TextField(blank=True, null=True, verbose_name="Descrizione Breve")
    mattoni_proibiti = models.ManyToManyField(Mattone, blank=True, related_name="proibiti_in_modelli", verbose_name="Mattoni Proibiti")
    mattoni_obbligatori = models.ManyToManyField(Mattone, blank=True, related_name="obbligatori_in_modelli", verbose_name="Mattoni Obbligatori")
    usa_doppia_formula = models.BooleanField(default=False, verbose_name="Abilita Doppia Formula")
    elemento_secondario = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': ELEMENTO}, related_name="modelli_secondari")
    usa_condizione_doppia = models.BooleanField(default=False, verbose_name="Richiede Condizione per Doppia")
    requisiti_doppia = models.ManyToManyField(Punteggio, through=ModelloAuraRequisitoDoppia, blank=True, related_name="modelli_req_doppia")
    usa_formula_per_mattone = models.BooleanField(default=False, verbose_name="Abilita Formula per Mattone")
    usa_condizione_mattone = models.BooleanField(default=False, verbose_name="Richiede Condizione per F. Mattone")
    requisiti_mattone = models.ManyToManyField(Punteggio, through=ModelloAuraRequisitoMattone, blank=True, related_name="modelli_req_mattone")
    usa_formula_per_caratteristica = models.BooleanField(default=False, verbose_name="Abilita Formula per Caratteristica")
    usa_condizione_caratt = models.BooleanField(default=False, verbose_name="Richiede Condizione per F. Caratt.")
    requisiti_caratt = models.ManyToManyField(Punteggio, through=ModelloAuraRequisitoCaratt, blank=True, related_name="modelli_req_caratt")
    class Meta: verbose_name = "Modello di Aura"; verbose_name_plural = "Modelli di Aura"
    def __str__(self): return f"Modello {self.aura.nome} - {self.nome}"

class CaratteristicaModificatore(models.Model):
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, related_name="modificatori_dati")
    statistica_modificata = models.ForeignKey(Statistica, on_delete=models.CASCADE, related_name="modificatori_ricevuti")
    modificatore = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    ogni_x_punti = models.IntegerField(default=1)
    class Meta: unique_together = ('caratteristica', 'statistica_modificata')

class AbilitaStatistica(CondizioneStatisticaMixin):
    abilita = models.ForeignKey('Abilita', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    valore = models.IntegerField(default=0)
    class Meta: unique_together = ('abilita', 'statistica')
    def __str__(self): return f"{self.statistica.nome}: {self.valore}"

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
    class Meta: verbose_name = "Abilità"; verbose_name_plural = "Abilità"
    def __str__(self): return self.nome

class abilita_tier(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    tabella = models.ForeignKey(Tier, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=10)

class abilita_prerequisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti")
    prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati")

class abilita_requisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo__in': (CARATTERISTICA, CONDIZIONE, STATISTICA)})
    valore = models.IntegerField(default=1)

class abilita_sbloccata(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    sbloccata = models.ForeignKey(Tabella, on_delete=models.CASCADE)
    
class abilita_punteggio(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    punteggio = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

class Attivata(A_vista):
    elementi = models.ManyToManyField(Punteggio, blank=True, through='AttivataElemento')
    statistiche_base = models.ManyToManyField(Statistica, through='AttivataStatisticaBase', blank=True, related_name='attivata_statistiche_base')
    def __str__(self): return f"Attivata (LEGACY): {self.nome}"
    @property
    def livello(self): return self.elementi.count()
    @property
    def costo_crediti(self): return self.livello * COSTO_PER_MATTONE_TESSITURA
    @property
    def TestoFormattato(self): return formatta_testo_generico(self.testo, statistiche_base=self.attivatastatisticabase_set.select_related('statistica').all())

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
    aura_richiesta = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="%(class)s_associate")
    class Meta: abstract = True; ordering = ['nome']
    @property
    def livello(self): return self.componenti.aggregate(tot=models.Sum('valore'))['tot'] or 0
    
class InfusioneStatistica(CondizioneStatisticaMixin):
    """
    Collega una Statistica a un'Infusione con un valore specifico.
    (Es. +2 Forza, +10 HP)
    """
    infusione = models.ForeignKey('Infusione', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    
    class Meta: 
        unique_together = ('infusione', 'statistica')
        verbose_name = "Statistica Infusione"
        verbose_name_plural = "Statistiche Infusione"
        
    def __str__(self): return f"{self.statistica.nome}: {self.valore}"

class Infusione(Tecnica):
    aura_infusione = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': AURA, 'is_soprannaturale': True}, related_name="infusioni_secondarie")
    caratteristiche = models.ManyToManyField(Punteggio, through='InfusioneCaratteristica', related_name="infusioni_utilizzatrici", limit_choices_to={'tipo': CARATTERISTICA})
    formula_attacco = models.CharField("Formula Attacco", max_length=255, blank=True, null=True)
    statistiche_base = models.ManyToManyField(Statistica, through='InfusioneStatisticaBase', blank=True, related_name='infusione_statistiche_base')
    # Statistiche MODIFICATORI (Es. +1 Forza) - REINTRODOTTO
    statistiche = models.ManyToManyField(Statistica, through='InfusioneStatistica', blank=True, related_name='infusione_statistiche')
    proposta_creazione = models.OneToOneField('PropostaTecnica', on_delete=models.SET_NULL, null=True, blank=True, related_name='infusione_generata', verbose_name="Proposta Originale")
    statistica_cariche = models.ForeignKey(Statistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="infusioni_cariche", verbose_name="Statistica per Cariche Max")    
    metodo_ricarica = models.TextField("Metodo di Ricarica", blank=True, null=True)
    costo_ricarica_crediti = models.IntegerField("Costo Ricarica (Crediti)", default=0)
    durata_attivazione = models.IntegerField("Durata Attivazione (secondi)", default=0)
    slot_corpo_permessi = models.CharField(
        max_length=50, 
        blank=True, null=True, 
        verbose_name="Slot Corpo Consentiti"
    )

    class Meta: verbose_name = "Infusione"; verbose_name_plural = "Infusioni"
    
    @property
    def costo_crediti(self): 
        base = COSTO_PER_MATTONE_INFUSIONE
        if self.aura_richiesta and self.aura_richiesta.stat_costo_acquisto_infusione:
            val = self.aura_richiesta.stat_costo_acquisto_infusione.valore_base_predefinito
            if val > 0: base = val
        return self.livello * base
        
    @property
    def TestoFormattato(self): return formatta_testo_generico(self.testo, statistiche_base=self.infusionestatisticabase_set.select_related('statistica').all(), context={'livello': self.livello, 'aura': self.aura_richiesta}, formula=self.formula_attacco)

class Tessitura(Tecnica):
    formula = models.TextField("Formula", blank=True, null=True)
    elemento_principale = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': ELEMENTO})
    caratteristiche = models.ManyToManyField(Punteggio, through='TessituraCaratteristica', related_name="tessiture_utilizzatrici", limit_choices_to={'tipo': CARATTERISTICA})
    statistiche_base = models.ManyToManyField(Statistica, through='TessituraStatisticaBase', blank=True, related_name='tessitura_statistiche_base')
    proposta_creazione = models.OneToOneField('PropostaTecnica', on_delete=models.SET_NULL, null=True, blank=True, related_name='tessitura_generata', verbose_name="Proposta Originale")
    class Meta: verbose_name = "Tessitura"; verbose_name_plural = "Tessiture"
    
    @property
    def costo_crediti(self): 
        base = COSTO_PER_MATTONE_TESSITURA
        if self.aura_richiesta and self.aura_richiesta.stat_costo_acquisto_tessitura:
            val = self.aura_richiesta.stat_costo_acquisto_tessitura.valore_base_predefinito
            if val > 0: base = val
        return self.livello * base
        
    @property
    def TestoFormattato(self): return formatta_testo_generico(self.testo, formula=self.formula, statistiche_base=self.tessiturastatisticabase_set.select_related('statistica').all(), context={'elemento': self.elemento_principale, 'livello': self.livello, 'aura': self.aura_richiesta})

class InfusioneCaratteristica(models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    class Meta: unique_together = ('infusione', 'caratteristica')

class TessituraCaratteristica(models.Model):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    class Meta: unique_together = ('tessitura', 'caratteristica')

class InfusioneStatisticaBase(models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    def __str__(self): return f"{self.statistica.nome}: {self.valore_base}"

class TessituraStatisticaBase(models.Model):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    def __str__(self): return f"{self.statistica.nome}: {self.valore_base}"

class Manifesto(A_vista): 
    def __str__(self): return f"Manifesto: {self.nome}"

class Inventario(A_vista):
    class Meta: verbose_name = "Inventario"; verbose_name_plural = "Inventari"
    def __str__(self): return f"Inventario: {self.nome}"
    def get_oggetti(self, data=None):
        if data is None: data = timezone.now()
        return Oggetto.objects.filter(tracciamento_inventario__inventario=self, tracciamento_inventario__data_inizio__lte=data, tracciamento_inventario__data_fine__isnull=True)

class OggettoInInventario(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name="tracciamento_inventario")
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="tracciamento_oggetti")
    data_inizio = models.DateTimeField(default=timezone.now)
    data_fine = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['-data_inizio']

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

# class OggettoElemento(models.Model):
#     oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
#     elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': ELEMENTO})
    
class OggettoCaratteristica(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    
    class Meta:
        unique_together = ('oggetto', 'caratteristica')
        verbose_name = "Caratteristica Oggetto"
        verbose_name_plural = "Caratteristiche Oggetto"

class OggettoStatistica(CondizioneStatisticaMixin):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: unique_together = ('oggetto', 'statistica')
    def __str__(self): return f"{self.statistica.nome}: {self.valore}"

class OggettoStatisticaBase(models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    class Meta: unique_together = ('oggetto', 'statistica')
    def __str__(self): return f"{self.statistica.nome}: {self.valore_base}"

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
            
class ClasseOggetto(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    max_mod_totali = models.IntegerField(default=0, verbose_name="Max Mod Totali")
    limitazioni_mod = models.ManyToManyField(Punteggio, through='ClasseOggettoLimiteMod', related_name='classi_oggetti_regole_mod', verbose_name="Limiti Mod per Caratteristica")
    mattoni_materia_permessi = models.ManyToManyField(Punteggio, limit_choices_to={'tipo': CARATTERISTICA}, related_name='classi_oggetti_materia_permessa', blank=True, verbose_name="Caratt. Materia Permesse")
    class Meta: verbose_name = "Classe Oggetto (Regole)"; verbose_name_plural = "Classi Oggetto (Regole)"
    def __str__(self): return self.nome

class ClasseOggettoLimiteMod(models.Model):
    classe_oggetto = models.ForeignKey(ClasseOggetto, on_delete=models.CASCADE)
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    max_installabili = models.IntegerField(default=1, verbose_name="Max Mod di questo tipo")
    class Meta: unique_together = ('classe_oggetto', 'caratteristica'); verbose_name = "Limite Mod per Caratteristica"
        
class OggettoBase(models.Model):
    nome = models.CharField(max_length=100)
    descrizione = models.TextField(blank=True, null=True)
    tipo_oggetto = models.CharField(max_length=3, choices=TIPO_OGGETTO_CHOICES, default=TIPO_OGGETTO_FISICO)
    classe_oggetto = models.ForeignKey(ClasseOggetto, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Classe (es. Fucile, Spada)")
    is_tecnologico = models.BooleanField(default=False)
    costo = models.IntegerField(default=0, verbose_name="Costo in Crediti")
    attacco_base = models.CharField(max_length=50, blank=True, null=True, help_text="Es. 2d6")
    statistiche_base = models.ManyToManyField(Statistica, through='OggettoBaseStatisticaBase', blank=True, related_name='template_base')
    statistiche_modificatori = models.ManyToManyField(Statistica, through='OggettoBaseModificatore', blank=True, related_name='template_modificatori')
    in_vendita = models.BooleanField(default=True, verbose_name="Visibile in Negozio")
    class Meta: verbose_name = "Oggetto Base (Listino)"; verbose_name_plural = "Oggetti Base (Listino)"; ordering = ['tipo_oggetto', 'nome']
    def __str__(self): return f"{self.nome} ({self.costo} CR)"

class OggettoBaseStatisticaBase(models.Model):
    oggetto_base = models.ForeignKey(OggettoBase, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    class Meta: verbose_name = "Statistica Base Template"; verbose_name_plural = "Statistiche Base Template"

class OggettoBaseModificatore(models.Model):
    oggetto_base = models.ForeignKey(OggettoBase, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    class Meta: verbose_name = "Modificatore Template"; verbose_name_plural = "Modificatori Template"

class Oggetto(A_vista):
    # elementi = models.ManyToManyField(Punteggio, blank=True, through='OggettoElemento')
    caratteristiche = models.ManyToManyField(
        Punteggio, 
        blank=True, 
        through='OggettoCaratteristica', 
        related_name="oggetti_utilizzatori",
        limit_choices_to={'tipo': CARATTERISTICA}
    )
    statistiche = models.ManyToManyField(Statistica, through='OggettoStatistica', blank=True, related_name="oggetti_statistiche")
    statistiche_base = models.ManyToManyField(Statistica, through='OggettoStatisticaBase', blank=True, related_name='oggetti_statistiche_base')
    aura = models.ForeignKey(Punteggio, blank=True, null=True, on_delete=models.SET_NULL, limit_choices_to={'tipo' : AURA}, related_name="oggetti_aura")
    tipo_oggetto = models.CharField(max_length=3, choices=TIPO_OGGETTO_CHOICES, default=TIPO_OGGETTO_FISICO)
    classe_oggetto = models.ForeignKey(ClasseOggetto, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Classe (Slot/Regole)")
    is_tecnologico = models.BooleanField(default=False, verbose_name="È Tecnologico?")
    is_equipaggiato = models.BooleanField(default=False, verbose_name="Equipaggiato?")
    costo_acquisto = models.IntegerField(default=0, verbose_name="Costo (Crediti)")
    attacco_base = models.CharField(max_length=50, blank=True, null=True, help_text="Es. 2d6")
    in_vendita = models.BooleanField(default=False, verbose_name="In vendita al negozio?")
    infusione_generatrice = models.ForeignKey('Infusione', on_delete=models.SET_NULL, null=True, blank=True, related_name='oggetti_generati', help_text="L'infusione da cui deriva questa Materia/Mod/Innesto")
    ospitato_su = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='potenziamenti_installati', help_text="L'oggetto su cui questo potenziamento è montato.")
    slot_corpo = models.CharField(max_length=3, choices=SLOT_CORPO_CHOICES, blank=True, null=True, help_text="Solo per Innesti e Mutazioni")
    cariche_attuali = models.IntegerField(default=0)
    oggetto_base_generatore = models.ForeignKey(OggettoBase, on_delete=models.SET_NULL, null=True, blank=True, related_name='istanze_generate', help_text="Se creato dal negozio, punta al template originale.")

    @property
    def livello(self):
        # Aggiorna il calcolo del livello basandosi sui nuovi componenti
        return self.componenti.aggregate(tot=models.Sum('valore'))['tot'] or 0
    
    @property
    def TestoFormattato(self): return formatta_testo_generico(self.testo, statistiche_base=self.oggettostatisticabase_set.select_related('statistica').all(), context={'livello': self.livello, 'aura': self.aura, 'item_modifiers': self.oggettostatistica_set.select_related('statistica').all()})
    @property
    def inventario_corrente(self):
        t = self.tracciamento_inventario.filter(data_fine__isnull=True).first()
        return t.inventario if t else None
    def sposta_in_inventario(self, nuovo, data=None):
        if data is None: data = timezone.now()
        with transaction.atomic():
            if self.ospitato_su: self.ospitato_su = None; self.save()
            curr = self.tracciamento_inventario.filter(data_fine__isnull=True).first()
            if curr:
                if curr.inventario == nuovo: return
                curr.data_fine = data; curr.save()
            if nuovo: OggettoInInventario.objects.create(oggetto=self, inventario=nuovo, data_inizio=data)
    def clean(self):
        if self.ospitato_su == self: raise ValidationError("Un oggetto non può essere installato su se stesso.")

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
        if not t.aura_richiesta: return False, "Aura mancante."
        if t.livello > self.get_valore_aura_effettivo(t.aura_richiesta): return False, "Livello tecnica superiore al valore Aura."
        
        base = self.caratteristiche_base
        for comp in t.componenti.select_related('caratteristica').all():
            nome_car = comp.caratteristica.nome
            val_richiesto = comp.valore
            val_posseduto = base.get(nome_car, 0)
            if val_richiesto > val_posseduto: return False, f"Requisito {nome_car} non soddisfatto (Serve {val_richiesto}, hai {val_posseduto})."

        modello = self.modelli_aura.filter(aura=t.aura_richiesta).first()
        if modello:
            caratteristiche_usate_ids = set(t.componenti.values_list('caratteristica_id', flat=True))
            ids_proibiti = set(modello.mattoni_proibiti.values_list('id', flat=True))
            if ids_proibiti:
                mattoni_violati = Mattone.objects.filter(id__in=ids_proibiti, aura=t.aura_richiesta, caratteristica_associata__id__in=caratteristiche_usate_ids)
                if mattoni_violati.exists(): return False, f"Usa combinazioni proibite dal modello: {', '.join([m.nome for m in mattoni_violati])}."
            mattoni_obbligatori = modello.mattoni_obbligatori.all()
            if mattoni_obbligatori.exists():
                for m_obb in mattoni_obbligatori:
                    if m_obb.caratteristica_associata.id not in caratteristiche_usate_ids: return False, f"Manca componente obbligatorio: {m_obb.nome}."
        return True, "OK"
    
    # @property
    # def modificatori_calcolati(self):
    #     if hasattr(self, '_modificatori_calcolati_cache'): return self._modificatori_calcolati_cache
    #     mods = {}
    #     def _add(p, t, v):
    #         if not p: return
    #         if p not in mods: mods[p] = {'add': 0.0, 'mol': 1.0}
    #         valore = float(v)
    #         if t == MODIFICATORE_ADDITIVO: mods[p]['add'] += valore
    #         elif t == MODIFICATORE_MOLTIPLICATIVO: mods[p]['mol'] *= valore 

    #     for l in AbilitaStatistica.objects.filter(abilita__personaggioabilita__personaggio=self).select_related('statistica'): _add(l.statistica.parametro, l.tipo_modificatore, l.valore)
    #     oggetti_inventario = self.get_oggetti().prefetch_related('oggettostatistica_set__statistica', 'potenziamenti_installati__oggettostatistica_set__statistica')
    #     for oggetto in oggetti_inventario:
    #         is_oggetto_attivo = False
    #         if oggetto.tipo_oggetto == TIPO_OGGETTO_FISICO and oggetto.is_equipaggiato: is_oggetto_attivo = True
    #         elif oggetto.tipo_oggetto == TIPO_OGGETTO_MUTAZIONE: is_oggetto_attivo = True
    #         elif oggetto.tipo_oggetto == TIPO_OGGETTO_INNESTO and oggetto.slot_corpo and oggetto.cariche_attuali > 0: is_oggetto_attivo = True
            
    #         if is_oggetto_attivo:
    #             for stat_link in oggetto.oggettostatistica_set.all(): _add(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)
    #             for potenziamento in oggetto.potenziamenti_installati.all():
    #                 is_potenziamento_attivo = False
    #                 if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA: is_potenziamento_attivo = True
    #                 elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD and potenziamento.cariche_attuali > 0: is_potenziamento_attivo = True
    #                 if is_potenziamento_attivo:
    #                     for stat_link_pot in potenziamento.oggettostatistica_set.all(): _add(stat_link_pot.statistica.parametro, stat_link_pot.tipo_modificatore, stat_link_pot.valore)

    #     cb = self.caratteristiche_base
    #     if cb:
    #         for l in CaratteristicaModificatore.objects.filter(caratteristica__nome__in=cb.keys()).select_related('caratteristica', 'statistica_modificata'):
    #             pts = cb.get(l.caratteristica.nome, 0)
    #             if pts > 0 and l.ogni_x_punti > 0:
    #                 b = (pts // l.ogni_x_punti) * l.modificatore
    #                 if b > 0: _add(l.statistica_modificata.parametro, MODIFICATORE_ADDITIVO, b)
    #     self._modificatori_calcolati_cache = mods
    #     return mods

    @property
    def modificatori_calcolati(self):
        if hasattr(self, '_modificatori_calcolati_cache'): return self._modificatori_calcolati_cache
        mods = {}
        
        def _add(p, t, v):
            if not p: return
            if p not in mods: mods[p] = {'add': 0.0, 'mol': 1.0}
            valore = float(v)
            if t == MODIFICATORE_ADDITIVO: mods[p]['add'] += valore
            elif t == MODIFICATORE_MOLTIPLICATIVO: mods[p]['mol'] *= valore 

        # Funzione helper per verificare se un modificatore è "Globale" (senza condizioni)
        def _is_global(stat_link):
            # Se ha una qualsiasi limitazione attiva, NON è globale
            if stat_link.usa_limitazione_elemento: return False
            if stat_link.usa_limitazione_aura: return False
            if stat_link.usa_condizione_text: return False
            return True

        # 1. Abilità
        for l in AbilitaStatistica.objects.filter(abilita__personaggioabilita__personaggio=self).select_related('statistica'): 
            if _is_global(l):
                _add(l.statistica.parametro, l.tipo_modificatore, l.valore)
        
        # 2. Oggetti e Innesti
        oggetti_inventario = self.get_oggetti().prefetch_related('oggettostatistica_set__statistica', 'potenziamenti_installati__oggettostatistica_set__statistica')
        for oggetto in oggetti_inventario:
            is_oggetto_attivo = False
            if oggetto.tipo_oggetto == TIPO_OGGETTO_FISICO and oggetto.is_equipaggiato: is_oggetto_attivo = True
            elif oggetto.tipo_oggetto == TIPO_OGGETTO_MUTAZIONE: is_oggetto_attivo = True
            elif oggetto.tipo_oggetto == TIPO_OGGETTO_INNESTO and oggetto.slot_corpo and oggetto.cariche_attuali > 0: is_oggetto_attivo = True
            
            if is_oggetto_attivo:
                for stat_link in oggetto.oggettostatistica_set.all(): 
                    # FILTRO: Aggiungi solo se non ha limitazioni
                    if _is_global(stat_link):
                        _add(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)
                
                # Potenziamenti (Mod/Materia) dentro gli oggetti
                for potenziamento in oggetto.potenziamenti_installati.all():
                    is_potenziamento_attivo = False
                    if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA: is_potenziamento_attivo = True
                    elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD and potenziamento.cariche_attuali > 0: is_potenziamento_attivo = True
                    
                    if is_potenziamento_attivo:
                        for stat_link_pot in potenziamento.oggettostatistica_set.all(): 
                            if _is_global(stat_link_pot):
                                _add(stat_link_pot.statistica.parametro, stat_link_pot.tipo_modificatore, stat_link_pot.valore)

        # 3. Caratteristiche Base (Queste sono sempre globali)
        cb = self.caratteristiche_base
        if cb:
            for l in CaratteristicaModificatore.objects.filter(caratteristica__nome__in=cb.keys()).select_related('caratteristica', 'statistica_modificata'):
                pts = cb.get(l.caratteristica.nome, 0)
                if pts > 0 and l.ogni_x_punti > 0:
                    b = (pts // l.ogni_x_punti) * l.modificatore
                    if b > 0: _add(l.statistica_modificata.parametro, MODIFICATORE_ADDITIVO, b)
        
        self._modificatori_calcolati_cache = mods
        return mods
    
    

    def get_modificatori_extra_da_contesto(self, context=None):
        """
        Calcola e restituisce SOLO i modificatori che si attivano specificamente
        in questo contesto (es. "Solo Elemento Fuoco", "Solo Aura Guerriero").
        Ignora i modificatori globali (già calcolati in modificatori_calcolati).
        """
        mods = {}
        if not context: return mods
        
        # Estrazione dati dal contesto (passati da formatta_testo_generico)
        elemento_target = context.get('elemento') # Oggetto Punteggio (Elemento)
        aura_target = context.get('aura')         # Oggetto Punteggio (Aura)
        
        # Prepariamo il contesto per eventuali formule di testo (es. "caratt > 5")
        eval_context = self.caratteristiche_base.copy()
        eval_context.update(context)
        if 'caratteristica_associata_valore' in context:
             eval_context['caratt'] = context['caratteristica_associata_valore']

        # Funzione helper per sommare i valori
        def _add(p, t, v):
            if not p: return
            if p not in mods: mods[p] = {'add': 0.0, 'mol': 1.0}
            valore = float(v)
            if t == MODIFICATORE_ADDITIVO: mods[p]['add'] += valore
            elif t == MODIFICATORE_MOLTIPLICATIVO: mods[p]['mol'] *= valore 

        # Funzione helper CORE: decide se il modificatore si applica
        def _check_condition(stat_link):
            # 1. Se NON ha nessuna condizione, lo scartiamo (è globale, 
            #    quindi è già incluso in self.modificatori_calcolati).
            has_conditions = (
                stat_link.usa_limitazione_elemento or 
                stat_link.usa_limitazione_aura or 
                stat_link.usa_condizione_text
            )
            if not has_conditions:
                return False
            
            # 2. Verifica Elemento (se richiesto)
            if stat_link.usa_limitazione_elemento:
                if not elemento_target: return False
                # Controlla se l'elemento attuale è nella lista di quelli permessi
                if not stat_link.limit_a_elementi.filter(pk=elemento_target.pk).exists():
                    return False

            # 3. Verifica Aura (se richiesta)
            if stat_link.usa_limitazione_aura:
                if not aura_target: return False
                # Controlla se l'aura attuale è nella lista di quelle permesse
                if not stat_link.limit_a_aure.filter(pk=aura_target.pk).exists():
                    return False
            
            # 4. Verifica Condizione Testuale (es. script custom)
            if stat_link.usa_condizione_text and stat_link.condizione_text:
                # evaluate_expression è definita globalmente in models.py
                try:
                    if not evaluate_expression(stat_link.condizione_text, eval_context):
                        return False
                except Exception:
                    return False # Se la formula è errata, non applicare
            
            # Se passa tutti i controlli (o se i controlli non c'erano), è valido
            return True

        # --- FASE 1: ABILITÀ ---
        # Recuperiamo i modificatori dalle abilità possedute
        # (Usiamo select/prefetch per evitare query N+1 sulle condizioni)
        links_abilita = AbilitaStatistica.objects.filter(
            abilita__personaggioabilita__personaggio=self
        ).select_related('statistica').prefetch_related('limit_a_elementi', 'limit_a_aure')

        for link in links_abilita:
            if _check_condition(link):
                _add(link.statistica.parametro, link.tipo_modificatore, link.valore)

        # --- FASE 2: OGGETTI & INNESTI ---
        # Recuperiamo gli oggetti attivi. 
        # Nota: get_oggetti() filtra già per l'inventario corrente.
        oggetti = self.get_oggetti().prefetch_related(
            'oggettostatistica_set__statistica',
            'oggettostatistica_set__limit_a_elementi',
            'oggettostatistica_set__limit_a_aure',
            'potenziamenti_installati__oggettostatistica_set__statistica',
            'potenziamenti_installati__oggettostatistica_set__limit_a_elementi',
            'potenziamenti_installati__oggettostatistica_set__limit_a_aure'
        )
        
        for oggetto in oggetti:
            is_oggetto_attivo = False
            
            # Logica identica a 'modificatori_calcolati' per determinare se l'oggetto conta
            if oggetto.tipo_oggetto == TIPO_OGGETTO_FISICO and oggetto.is_equipaggiato: 
                is_oggetto_attivo = True
            elif oggetto.tipo_oggetto == TIPO_OGGETTO_MUTAZIONE: 
                # Le mutazioni sono sempre attive se possedute
                is_oggetto_attivo = True
            elif oggetto.tipo_oggetto == TIPO_OGGETTO_INNESTO and oggetto.slot_corpo and oggetto.cariche_attuali > 0: 
                # Innesti richiedono slot e carica (se previsto)
                is_oggetto_attivo = True
            
            if is_oggetto_attivo:
                # 2A. Modificatori diretti dell'oggetto
                for stat_link in oggetto.oggettostatistica_set.all():
                    if _check_condition(stat_link):
                        _add(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)
                
                # 2B. Modificatori dei Potenziamenti (Mod/Materia) installati sull'oggetto
                for potenziamento in oggetto.potenziamenti_installati.all():
                    is_potenziamento_attivo = False
                    
                    if potenziamento.tipo_oggetto == TIPO_OGGETTO_MATERIA:
                        is_potenziamento_attivo = True
                    elif potenziamento.tipo_oggetto == TIPO_OGGETTO_MOD and potenziamento.cariche_attuali > 0:
                        is_potenziamento_attivo = True
                    
                    if is_potenziamento_attivo:
                        for stat_link_pot in potenziamento.oggettostatistica_set.all():
                            if _check_condition(stat_link_pot):
                                _add(stat_link_pot.statistica.parametro, stat_link_pot.tipo_modificatore, stat_link_pot.valore)

        return mods
    

    def get_testo_formattato_per_item(self, item):
        if not item: return ""
        if isinstance(item, Oggetto):
            stats = item.oggettostatisticabase_set.select_related('statistica').all()
            item_mods = item.oggettostatistica_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura, 'item_modifiers': item_mods}
            return formatta_testo_generico(item.testo, formula=getattr(item, 'formula', None), statistiche_base=stats, personaggio=self, context=ctx)
        elif isinstance(item, Infusione):
            stats = item.infusionestatisticabase_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura_richiesta}
            return formatta_testo_generico(item.testo, statistiche_base=stats, personaggio=self, context=ctx, formula=item.formula_attacco)
        elif isinstance(item, Attivata):
            stats = item.attivatastatisticabase_set.select_related('statistica').all()
            return formatta_testo_generico(item.testo, statistiche_base=stats, personaggio=self)
        elif isinstance(item, Tessitura):
            stats = item.tessiturastatisticabase_set.select_related('statistica').all()
            formula_text = item.formula or ""
            if "{elem}" not in formula_text:
                ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': item.elemento_principale}
                return formatta_testo_generico(item.testo, formula=formula_text, statistiche_base=stats, personaggio=self, context=ctx)

            modello = self.modelli_aura.filter(aura=item.aura_richiesta).first()
            elementi_map = {} 
            if item.elemento_principale: elementi_map[item.elemento_principale.id] = item.elemento_principale
            
            if modello:
                punteggi_pg = self.punteggi_base 
                def verifica_requisiti(requisiti_queryset):
                    for req_link in requisiti_queryset:
                        if punteggi_pg.get(req_link.requisito.nome, 0) < req_link.valore: return False
                    return True

                if modello.usa_doppia_formula and modello.elemento_secondario:
                    attiva_doppia = True
                    if modello.usa_condizione_doppia: attiva_doppia = verifica_requisiti(modello.req_doppia_rel.select_related('requisito').all())
                    if attiva_doppia: elementi_map[modello.elemento_secondario.id] = modello.elemento_secondario

                if modello.usa_formula_per_caratteristica:
                    attiva_caratt = True
                    if modello.usa_condizione_caratt: attiva_caratt = verifica_requisiti(modello.req_caratt_rel.select_related('requisito').all())
                    if attiva_caratt:
                        for el in Punteggio.objects.filter(tipo=ELEMENTO, caratteristica_relativa__nome__in=punteggi_pg.keys()):
                            if punteggi_pg.get(el.caratteristica_relativa.nome, 0) > 0: elementi_map[el.id] = el
                
                # FIX: USO DI COMPONENTI INVECE DI MATTONI
                if modello.usa_formula_per_mattone:
                    attiva_mattone = True
                    if modello.usa_condizione_mattone: attiva_mattone = verifica_requisiti(modello.req_mattone_rel.select_related('requisito').all())
                    if attiva_mattone:
                        # Recupera gli ID delle caratteristiche usate nei componenti
                        caratt_ids = item.componenti.values_list('caratteristica', flat=True)
                        for el in Punteggio.objects.filter(tipo=ELEMENTO, caratteristica_relativa__id__in=caratt_ids):
                            elementi_map[el.id] = el

            elementi_da_calcolare = list(elementi_map.values())
            if not elementi_da_calcolare:
                ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': None}
                return formatta_testo_generico(item.testo, formula=item.formula, statistiche_base=stats, personaggio=self, context=ctx)

            ctx_base = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': item.elemento_principale}
            descrizione_html = formatta_testo_generico(item.testo, formula=None, statistiche_base=stats, personaggio=self, context=ctx_base)
            
            formule_html = []
            for elem in elementi_da_calcolare:
                val_caratt = 0
                if elem.caratteristica_relativa: val_caratt = self.caratteristiche_base.get(elem.caratteristica_relativa.nome, 0)
                ctx_loop = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': elem, 'caratteristica_associata_valore': val_caratt}
                risultato_formula = formatta_testo_generico(None, formula=item.formula, statistiche_base=stats, personaggio=self, context=ctx_loop, solo_formula=True)
                valore_pura_formula = risultato_formula.replace("<strong>Formula:</strong>", "").strip()
                if valore_pura_formula:
                    block = f"<div style='margin-top: 4px; padding: 4px 8px; border-left: 3px solid {elem.colore}; background-color: rgba(255,255,255,0.05); border-radius: 0 4px 4px 0;'><span style='color: {elem.colore}; font-weight: bold; margin-right: 6px;'>{elem.nome}:</span>{valore_pura_formula}</div>"
                    formule_html.append(block)

            if formule_html: return f"{descrizione_html}<hr style='margin: 10px 0; border: 0; border-top: 1px dashed #555;'/><div style='font-size: 0.95em;'><strong>Formule:</strong>{''.join(formule_html)}</div>"
            return descrizione_html
        return ""
    
    def get_valore_statistica(self, sigla):
        try:
            stat_obj = Statistica.objects.filter(sigla=sigla).first()
            if not stat_obj or not stat_obj.parametro: return 0
            mods = self.modificatori_calcolati.get(stat_obj.parametro, {'add': 0, 'mol': 1.0})
            return int(round((stat_obj.valore_base_predefinito + mods['add']) * mods['mol']))
        except Exception: return 0

    def get_costo_item_scontato(self, item):
        costo_base = 0
        if hasattr(item, 'costo_crediti'): costo_base = item.costo_crediti
        if costo_base <= 0: return 0
        sconto_perc = 0
        if isinstance(item, (Infusione, Tessitura, Attivata)): sconto_perc = self.get_valore_statistica('RCT')
        elif isinstance(item, Oggetto): sconto_perc = self.get_valore_statistica('RCO')
        elif isinstance(item, Abilita): sconto_perc = self.get_valore_statistica('RCA')
        if sconto_perc > 0:
            sconto_perc = min(sconto_perc, 50) 
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
    class Meta: ordering=['-data_invio']
    
class LetturaMessaggio(models.Model):
    messaggio = models.ForeignKey(Messaggio, on_delete=models.CASCADE, related_name="stati_lettura")
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="messaggi_stati")
    letto = models.BooleanField(default=False)
    data_lettura = models.DateTimeField(null=True, blank=True)
    cancellato = models.BooleanField(default=False)
    class Meta: unique_together = ('messaggio', 'personaggio'); verbose_name = "Stato Lettura Messaggio"; verbose_name_plural = "Stati Lettura Messaggi"
    def __str__(self): return f"{self.personaggio.nome} - {self.messaggio.titolo}"

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
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name='proposte_aura')
    aura_infusione = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': AURA}, related_name='proposte_infusione')
    caratteristiche = models.ManyToManyField(Punteggio, through='PropostaTecnicaCaratteristica', related_name='proposte_in_cui_usato', limit_choices_to={'tipo': CARATTERISTICA})
    costo_invio_pagato = models.IntegerField(default=0, help_text="Crediti spesi per l'invio")
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_invio = models.DateTimeField(null=True, blank=True)
    note_staff = models.TextField(blank=True, null=True)
    slot_corpo_permessi = models.CharField(
        max_length=50, 
        blank=True, null=True, 
        help_text="Lista slot separati da virgola (es. HD1,TR1)"
    )
    
    class Meta: 
        ordering = ['-data_creazione']
        verbose_name = "Proposta Tecnica"
        verbose_name_plural = "Proposte Tecniche"
    
    def __str__(self): 
        return f"{self.get_tipo_display()} - {self.nome} ({self.personaggio.nome})"
    
    @property
    def livello(self): 
        return self.componenti.aggregate(tot=models.Sum('valore'))['tot'] or 0

class PropostaTecnicaCaratteristica(models.Model):
    proposta = models.ForeignKey(PropostaTecnica, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)

    class Meta: 
        ordering = ['caratteristica__nome']
        unique_together = ('proposta', 'caratteristica')

class PropostaTecnicaMattone(models.Model):
    # LEGACY: Mantenuto per evitare errori di importazione se ci sono riferimenti, ma non usato
    proposta = models.ForeignKey(PropostaTecnica, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=0) 

class ForgiaturaInCorso(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name='forgiature_attive')
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    data_inizio = models.DateTimeField(default=timezone.now)
    data_fine_prevista = models.DateTimeField()
    slot_target = models.CharField(max_length=2, blank=True, null=True) 
    completata = models.BooleanField(default=False)
    
    # NUOVO: Se presente, l'oggetto creato andrà a questo personaggio (es. Committente)
    destinatario_finale = models.ForeignKey(
        Personaggio, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='forgiature_in_arrivo',
        verbose_name="Destinatario Finale (se conto terzi)"
    )

    class Meta:
        ordering = ['data_fine_prevista']
        verbose_name = "Forgiatura in Corso"
        verbose_name_plural = "Forgiature in Corso"

    @property
    def is_pronta(self):
        return timezone.now() >= self.data_fine_prevista


# --- TIPI OPERAZIONE ---
TIPO_OPERAZIONE_INSTALLAZIONE = 'INST'
TIPO_OPERAZIONE_RIMOZIONE = 'RIMO'
TIPO_OPERAZIONE_FORGIATURA = 'FORG'
TIPO_OPERAZIONE_INNESTO = 'GRAF' # Graft/Innesto

TIPO_OPERAZIONE_CHOICES = [
    (TIPO_OPERAZIONE_INSTALLAZIONE, 'Installazione Mod/Materia'),
    (TIPO_OPERAZIONE_RIMOZIONE, 'Rimozione'),
    (TIPO_OPERAZIONE_FORGIATURA, 'Forgiatura Conto Terzi'),
    (TIPO_OPERAZIONE_INNESTO, 'Operazione Chirurgica (Innesto/Mutazione)'),
]

# --- STATI RICHIESTA ---
STATO_RICHIESTA_PENDENTE = 'PEND'
STATO_RICHIESTA_COMPLETATA = 'COMP'
STATO_RICHIESTA_RIFIUTATA = 'RIFI'

STATO_RICHIESTA_CHOICES = [
    (STATO_RICHIESTA_PENDENTE, 'In Attesa'),
    (STATO_RICHIESTA_COMPLETATA, 'Completata'),
    (STATO_RICHIESTA_RIFIUTATA, 'Rifiutata'),
]

class RichiestaAssemblaggio(models.Model):
    committente = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name='richieste_assemblaggio_inviate')
    artigiano = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name='richieste_assemblaggio_ricevute')
    
    # Opzionali per supportare la forgiatura (dove non c'è ancora l'oggetto fisico)
    oggetto_host = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name='richieste_host', null=True, blank=True)
    componente = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name='richieste_componente', null=True, blank=True)
    
    # NUOVO: L'infusione da forgiare
    infusione = models.ForeignKey('Infusione', on_delete=models.CASCADE, related_name='richieste_forgiatura', null=True, blank=True)
    
    # Per l'installazione di Innesti, colleghiamo la richiesta a una forgiatura esistente
    # (L'oggetto non esiste ancora fisicamente, è nel limbo della forgia)
    forgiatura_target = models.ForeignKey('ForgiaturaInCorso', on_delete=models.SET_NULL, null=True, blank=True, related_name='richieste_installazione')
    
    # Slot dove montare l'innesto
    slot_destinazione = models.CharField(max_length=3, choices=SLOT_CORPO_CHOICES, blank=True, null=True)
    
    tipo_operazione = models.CharField(
        max_length=4, 
        choices=TIPO_OPERAZIONE_CHOICES, 
        default=TIPO_OPERAZIONE_INSTALLAZIONE,
        verbose_name="Tipo Operazione"
    )
    
    offerta_crediti = models.IntegerField(default=0, verbose_name="Offerta pagamento")
    data_creazione = models.DateTimeField(auto_now_add=True)
    stato = models.CharField(max_length=4, choices=STATO_RICHIESTA_CHOICES, default=STATO_RICHIESTA_PENDENTE)
    
    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Richiesta Lavoro"
        verbose_name_plural = "Richieste Lavoro"

    def clean(self):
        if self.committente == self.artigiano:
            raise ValidationError("Non puoi inviare una richiesta a te stesso.")
            
        if self.tipo_operazione == TIPO_OPERAZIONE_FORGIATURA and not self.infusione:
            raise ValidationError("Per la forgiatura è obbligatorio specificare l'infusione.")
            
        if self.tipo_operazione != TIPO_OPERAZIONE_FORGIATURA and (not self.oggetto_host or not self.componente):
             raise ValidationError("Installazione e Rimozione richiedono Host e Componente.")
    
    def __str__(self):
        return f"{self.get_tipo_operazione_display()} - {self.committente} -> {self.artigiano}"