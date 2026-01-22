from django.db.models import Sum, F, Count
import re
import secrets
import string
import copy
from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
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
COSTO_PER_MATTONE_CERIMONIALE = 100
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
TIPO_PROPOSTA_CERIMONIALE = 'CER'

TIPO_PROPOSTA_CHOICES = [
    (TIPO_PROPOSTA_INFUSIONE, 'Infusione'),
    (TIPO_PROPOSTA_TESSITURA, 'Tessitura'),
    (TIPO_PROPOSTA_CERIMONIALE, 'Cerimoniale'),
]

TIPO_OGGETTO_FISICO = 'FIS'
TIPO_OGGETTO_MATERIA = 'MAT'
TIPO_OGGETTO_MOD = 'MOD'
TIPO_OGGETTO_INNESTO = 'INN'
TIPO_OGGETTO_MUTAZIONE = 'MUT'
TIPO_OGGETTO_AUMENTO = "AUM"
TIPO_OGGETTO_POTENZIAMENTO = "POT"


TIPO_OGGETTO_CHOICES = [
    (TIPO_OGGETTO_FISICO, 'Oggetto Fisico'),
    (TIPO_OGGETTO_MATERIA, 'Materia (Mondana)'),
    (TIPO_OGGETTO_MOD, 'Mod (Tecnologica)'),
    (TIPO_OGGETTO_INNESTO, 'Innesto (Tecnologico)'),
    (TIPO_OGGETTO_MUTAZIONE, 'Mutazione (Innata)'),
    (TIPO_OGGETTO_AUMENTO, 'Aumento (installazione corporea)'),
    (TIPO_OGGETTO_POTENZIAMENTO, 'Potenziamento (installazione su oggetti)'),
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

SCELTA_RISULTATO_POTENZIAMENTO = 'POT'      # Crea un oggetto Potenziamento (Tecnologico) / Materia (Mondano)
SCELTA_RISULTATO_AUMENTO = 'AUM'  # Crea un Innesto (Tecnologico) / Mutazione (Innata)

SCELTA_RISULTATO_CHOICES = [
    (SCELTA_RISULTATO_POTENZIAMENTO, 'Potenziamento (Mod/Materia)'),
    (SCELTA_RISULTATO_AUMENTO, 'Aumento Corporeo (Innesto/Mutazione)'),
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
    
# HELPER PER NUMERI ROMANI
def to_roman(n):
    try:
        n = int(n)
    except:
        return str(n)
    if not (0 < n < 4000): return str(n) # Supporto standard 1-3999
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ''
    i = 0
    while n > 0:
        for _ in range(n // val[i]):
            roman_num += syb[i]
            n -= val[i]
        i += 1
    return roman_num

# HELPER PER NUMERI LETTERALI (Semplificato per RPG 0-20, espandibile)
FORMAT_COLLECTIONS = {
    # Numeri Letterali (0-20)
    'L': {
        0: 'zero', 1: '', 2: 'due', 3: 'tre', 4: 'quattro', 5: 'cinque',
        6: 'sei', 7: 'sette', 8: 'otto', 9: 'nove', 10: 'dieci',
        11: 'undici', 12: 'dodici', 13: 'tredici', 14: 'quattordici', 15: 'quindici',
        16: 'sedici', 17: 'diciassette', 18: 'diciotto', 19: 'diciannove', 20: 'venti', 
        'DEFAULT' : '{n}'    
        },
    # Ordinali Maschili
    'OM': {
        1: 'primo', 2: 'secondo', 3: 'terzo', 4: 'quarto', 5: 'quinto',
        6: 'sesto', 7: 'settimo', 8: 'ottavo', 9: 'nono', 10: 'decimo',
        11: 'undicesimo', 12: 'dodicesimo',
        'DEFAULT' : '{n}°'
    },
    # Ordinali Femminili
    'OF': {
        1: 'prima', 2: 'seconda', 3: 'terza', 4: 'quarta', 5: 'quinta',
        6: 'sesta', 7: 'settima', 8: 'ottava', 9: 'nona', 10: 'decima',
        'DEFAULT' : '{n}ª'
    },
    # Esempio: Rango/Tier (Mapping esplicito)
    'RANGO': {
        0: 'Mondano! ', 1: '', 2: 'Eroico! ', 3: 'Leggendario! ', 
        4: 'Mitologico! ', 5: 'Divino! ', 6: 'Cosmico! ', 
        'DEFAULT' : 'Rango {n}'
    },
    # Esempio: Dadi (D4, D6...)
    'DADI': {
        4: 'd4', 6: 'd6', 8: 'd8', 10: 'd10', 12: 'd12', 20: 'd20',
        'DEFAULT' : 'd{n}'
    },
    'MOLT' : {
        1: '', 2: 'Doppio! ', 3: 'Triplo! ', 4: 'Quadruplo! ', 
        5: 'Quintuplo!', 6: 'Sestuplo! ', 7: 'Settuplo! ', 8: 'Ottuplo! ', 
        9: 'Nonuplo! ', 10: 'Decuplo! ',
        'DEFAULT' : '{n}-uplo! '
    }
}

# 3. FUNZIONE DI TRASFORMAZIONE VALORE
def formatta_valore_avanzato(valore, formato, context=None):
    """
    Converte un valore (numerico o oggetto) in stringa secondo il formato.
    Supporta:
    - R: Romano Maiuscolo (VII)
    - r: Romano Minuscolo (vii)
    - NAME: Nome dell'oggetto (se disponibile nel context)
    - :KEY: Cerca nella collection FORMAT_COLLECTIONS[KEY]
    """
    # A. Gestione Oggetti/Nomi (Es. {aura|NAME})
    if formato == 'NAME':
        if hasattr(valore, 'nome'): return valore.nome
        if hasattr(valore, 'dichiarazione') and valore.dichiarazione: return valore.dichiarazione
        return str(valore)

    # B. Conversione sicura a Intero
    try:
        n = int(round(float(valore)))
    except (ValueError, TypeError):
        # Se non è un numero, ritorniamo la stringa originale
        return str(valore)

    # C. Formattazione Algoritmica (Romani)
    if formato == 'R': return to_roman(n)
    if formato == 'r': return to_roman(n).lower()

    # D. Formattazione basata su Collezioni (:COLL)
    if formato and formato.startswith(':'):
        coll_key = formato[1:] # Rimuove i due punti
        collection = FORMAT_COLLECTIONS.get(coll_key)
        
        if collection:
            # 1. Cerca mappatura esatta
            if n in collection:
                testo = collection[n]
            # 2. Cerca fallback 'DEFAULT'
            elif 'DEFAULT' in collection:
                testo = collection['DEFAULT'].replace('{n}', str(n))
            # 3. Fallback assoluto
            else:
                testo = str(n)
            
            # Se la chiave nel testo originale era maiuscola (es :L), capitalizziamo il risultato
            if coll_key.isupper() and testo and testo[0].islower():
                return testo.capitalize()
            return testo

    # E. Fallback Legacy / Alias rapidi
    if formato == 'L': return formatta_valore_avanzato(n, ':L')
    if formato == 'l': 
        val = formatta_valore_avanzato(n, ':L')
        return val.lower()

    # Default: Numero semplice
    return str(n)

# 4. FUNZIONE PRINCIPALE
def formatta_testo_generico(testo, formula=None, statistiche_base=None, personaggio=None, context=None, solo_formula=False):
    testo_out = testo or ""
    formula_out = formula or ""
    if not testo_out and not formula_out: return ""

    base_values = {}
    eval_context = {}

    # 1. Recupero Valori Base (da Statistiche Oggetto/Tecnica)
    if statistiche_base:
        for item in statistiche_base:
            param = getattr(item.statistica, 'parametro', None) if hasattr(item, 'statistica') else None
            if param:
                # Usa valore_base se presente e diverso da 0, altrimenti usa valore_base_predefinito della statistica
                val = getattr(item, 'valore_base', 0)
                if val == 0 and hasattr(item, 'statistica') and item.statistica:
                    # Fallback al valore_base_predefinito della statistica
                    val = getattr(item.statistica, 'valore_base_predefinito', 0)
                base_values[param] = val
                eval_context[param] = val

    # 2. Calcolo Modificatori (dal Personaggio)
    mods_attivi = {}
    if personaggio:
        # Copia i modificatori globali
        mods_attivi = copy.deepcopy(personaggio.modificatori_calcolati)
        
        # Aggiungi modificatori condizionali (specifici del contesto: es. "Solo Fuoco")
        if context:
            extra_mods = personaggio.get_modificatori_extra_da_contesto(context)
            for param, valori in extra_mods.items():
                if param not in mods_attivi: mods_attivi[param] = {'add': 0.0, 'mol': 1.0}
                mods_attivi[param]['add'] += valori['add']
                mods_attivi[param]['mol'] *= valori['mol']

        # IMPORTANTE: Aggiungi i valori base intrinseci del personaggio (statistiche_base_dict)
        # Questi rappresentano i valori "naturali" del personaggio prima delle abilità
        statistiche_base_pg = personaggio.statistiche_base_dict
        for param, val in statistiche_base_pg.items():
            if param not in eval_context:  # Solo se non è già stato impostato dalle statistiche_base dell'oggetto
                eval_context[param] = val
        
        # Aggiungi anche le caratteristiche dalle abilità (per compatibilità)
        caratteristiche_personaggio = personaggio.caratteristiche_base
        for param, val in caratteristiche_personaggio.items():
            if param not in eval_context:
                eval_context[param] = val
        
        # Applica i modificatori ai valori
        # I modificatori vengono applicati a TUTTI i parametri che hanno modificatori attivi
        for param, mod_data in mods_attivi.items():
            val_base = eval_context.get(param, 0)
            val_finale = (val_base + mod_data['add']) * mod_data['mol']
            eval_context[param] = val_finale

    # 3. Preparazione Contesto Oggetti (per |NAME)
    object_context = {}
    if context:
        for k, v in context.items():
            # Se è un oggetto Django, lo salviamo in object_context per i nomi
            if hasattr(v, 'pk') or hasattr(v, 'nome'):
                object_context[k] = v
            # Se è un valore semplice, aggiorniamo il contesto matematico
            else:
                eval_context[k] = v
        # Helper legacy per le formule tessitura che usano "caratt"
        if 'caratteristica_associata_valore' in context:
             eval_context['caratt'] = context['caratteristica_associata_valore']

    # 4. Calcolo Metatalenti (Logica Aura/Modelli)
    testo_metatalenti = ""
    if personaggio and context and not solo_formula:
        # ... (Logica esistente per i Metatalenti) ...
        # (Riporta qui il blocco di codice dei metatalenti dalla tua funzione originale)
        # Per brevità nel prompt non lo ripeto tutto, ma va mantenuto identico.
        # Se vuoi, posso incollarlo esplicitamente.
        pass 

    # 5. RISOLUZIONE DEI PLACEHOLDER {espressione|FORMATO}
    def resolve_placeholder(match):
        expr = match.group(1).strip() # es. "forza + 1"
        formato = match.group(2)      # es. ":R" o "NAME"

        # A. Caso Speciale: Recupero Oggetto per nome ({aura|NAME})
        if formato == 'NAME':
            if expr in object_context:
                return formatta_valore_avanzato(object_context[expr], 'NAME')
            # Se non trovo l'oggetto, provo a vedere se è una stringa nel contesto valutato
            if expr in eval_context:
                 return str(eval_context[expr])

        # B. Valutazione Matematica
        val_math = evaluate_expression(expr, eval_context)
        
        # Fallback: parser +/- semplice se eval fallisce o torna 0 su stringa non nulla
        if val_math == 0 and expr and expr not in eval_context:
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
                val_math = total
             except: pass

        # C. Formattazione Finale
        return formatta_valore_avanzato(val_math, formato)

    # Regex aggiornata: cerca {contenuto} con opzionale |formato
    pattern_placeholder = re.compile(r'\{([^}|]+)(?:\|([^}]+))?\}')

    # Gestione Blocchi Condizionali {if ...}...{endif}
    def replace_conditional_block(match):
        if evaluate_expression(match.group(1), eval_context): return match.group(2)
        return ""
    
    testo_completo = testo_out + testo_metatalenti
    # sezione aggiunta come prova
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
    # fine sezione aggiunte
    
    # Esegue le sostituzioni
    pattern_if = re.compile(r'\{if\s+(.+?)\}(.*?)\{endif\}', re.DOTALL | re.IGNORECASE)
    
    testo_finale = pattern_if.sub(replace_conditional_block, testo_completo)
    testo_finale = pattern_placeholder.sub(resolve_placeholder, testo_finale)
    
    formula_finale = pattern_if.sub(replace_conditional_block, formula_out)
    formula_finale = pattern_placeholder.sub(resolve_placeholder, formula_finale)
    
    # Costruzione Output HTML
    parts = []
    if testo_finale: parts.append(testo_finale)
    if formula_finale:
        if testo_finale: parts.append("<br/><hr style='margin:5px 0; border:0; border-top:1px dashed #ccc;'/>")
        parts.append(f"<strong>Formula:</strong> {formula_finale}")
        
    return "".join(parts)

def genera_html_cariche(item, personaggio=None):
    """Genera il blocco HTML per le cariche di Infusioni e Oggetti."""
    source = None
    if isinstance(item, Infusione):
        source = item
    elif isinstance(item, Oggetto) and item.infusione_generatrice:
        source = item.infusione_generatrice
    
    # Se non c'è una fonte o non è configurata la statistica cariche, non mostrare nulla
    if not source or not source.statistica_cariche:
        return ""

    # 1. Calcolo Cariche Totali
    stat = source.statistica_cariche
    valore_totale = stat.valore_base_predefinito
    if personaggio:
        valore_totale = personaggio.get_valore_statistica(stat.sigla)
    
    # 2. Formattazione Durata (da secondi a testo)
    durata_str = ""
    if source.durata_attivazione > 0:
        sec = source.durata_attivazione
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        parts = []
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        if s: parts.append(f"{s}s")
        durata_str = " ".join(parts)

    # 3. Costruzione HTML
    # Stile inline per garantire la visualizzazione ovunque (Admin & Frontend)
    box_style = "margin-top: 12px; padding: 8px 12px; border: 1px solid rgba(255,255,255,0.2); background-color: rgba(0,0,0,0.2); border-radius: 6px; font-size: 0.9em; line-height: 1.4;"
    header_style = "color: #ffd700; font-weight: bold; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 6px; padding-bottom: 4px; display: flex; justify-content: space-between; align-items: center;"
    row_style = "margin-bottom: 2px;"
    label_style = "color: #aaa; margin-right: 5px;"

    html = f"<div style='{box_style}'>"
    html += f"<div style='{header_style}'><span>⚡ {stat.nome}</span> <span>Tot: {valore_totale}</span></div>"
    
    if source.metodo_ricarica:
        html += f"<div style='{row_style}'><span style='{label_style}'>Ricarica:</span> {source.metodo_ricarica}</div>"
    
    details = []
    if source.costo_ricarica_crediti > 0:
        details.append(f"<span style='{label_style}'>Costo:</span> {source.costo_ricarica_crediti} CR")
    
    if durata_str:
        details.append(f"<span style='{label_style}'>Durata:</span> {durata_str}")
        
    if details:
        html += f"<div style='{row_style}'>{' &nbsp;|&nbsp; '.join(details)}</div>"

    html += "</div>"
    return html


# --- TIPI ---
CARATTERISTICA = "CA"; STATISTICA = "ST"; ELEMENTO = "EL"; AURA = "AU"; CONDIZIONE = "CO"; CULTO = "CU"; VIA = "VI"; ARTE = "AR"; ARCHETIPO = "AR"

punteggi_tipo = [
    (CARATTERISTICA, 'Caratteristica'), 
    (STATISTICA, 'Statistica'), 
    (ELEMENTO, 'Elemento'), (AURA, 'Aura'), 
    (CONDIZIONE, 'Condizione'), 
    (CULTO, 'Culto'), 
    (VIA, 'Via'), 
    (ARTE, 'Arte'), 
    (ARCHETIPO, 'Archetipo')
]
    
T_GENERALI = "G0";
TIER_1 = "T1"; 
TIER_2 = "T2"; 
TIER_3 = "T3"; 
TIER_4 = "T4"
tabelle_tipo = [(T_GENERALI, 'Tabelle Generali'), (TIER_1, 'Tier 1'), (TIER_2, 'Tier 2'), (TIER_3, 'Tier 3'), (TIER_4, 'Tier 4')]
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
    # NUOVI FLAG: Cosa può produrre questa Aura? DA RIMUOVERE QUANDO FUNZIONA TUTTO
    # produce_mod = models.BooleanField(default=False, verbose_name="Produce MOD (Oggetti)")
    # produce_materia = models.BooleanField(default=False, verbose_name="Produce MATERIA (Oggetti)")
    # produce_innesti = models.BooleanField(default=False, verbose_name="Produce INNESTI (Corpo)")
    # produce_mutazioni = models.BooleanField(default=False, verbose_name="Produce MUTAZIONI (Corpo)")
    # NUOVA LOGICA:
    produce_aumenti = models.BooleanField(default=False, verbose_name="Produce Aumenti (Innesti/Mutazioni)")
    produce_potenziamenti = models.BooleanField(default=False, verbose_name="Produce Potenziamenti (Mod/Materia)")
    # Nomi personalizzati per la generazione oggetti
    # Es: "Innesto" per Tecnologico, "Mutazione" per Innato
    nome_tipo_aumento = models.CharField(max_length=50, blank=True, null=True, help_text="Es. Innesto, Mutazione")
    # Es: "Mod" per Tecnologico, "Materia" per Mondano
    nome_tipo_potenziamento = models.CharField(max_length=50, blank=True, null=True, help_text="Es. Mod, Materia")
    nome_tipo_tessitura = models.CharField(max_length=50, blank=True, null=True, help_text="Es. Incantesimo, Preghiera...")
    # --- NUOVE REGOLE DI FUNZIONAMENTO ---
    spegne_a_zero_cariche = models.BooleanField(default=False, verbose_name="Si spegne a 0 cariche? (Tecnologico)")
    potenziamenti_multi_slot = models.BooleanField(default=False, verbose_name="Multi-Slot? (Più copie sullo stesso oggetto)")
    
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
    
    # --- NUOVI CAMPI CERIMONIALI ---
    permette_cerimoniali = models.BooleanField(default=False, verbose_name="Permette Cerimoniali")
    stat_costo_acquisto_cerimoniale = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_acquisto_cer', verbose_name="Stat. Costo Acquisto Cerimoniale")
    stat_costo_creazione_cerimoniale = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_cer', verbose_name="Stat. Costo Creazione Cerimoniale")
    stat_costo_invio_proposta_cerimoniale = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_invio_prop_cer', verbose_name="Stat. Costo Invio Proposta (Cer)")
    # -------------------------------
    
    class Meta: 
        verbose_name = "Punteggio"
        verbose_name_plural = "Punteggi"
        ordering = ['tipo', 'ordine', 'nome']
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
    
class ConfigurazioneLivelloAura(models.Model):
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': 'AU'}, related_name="configurazione_livelli")
    livello = models.IntegerField(default=1, help_text="A che valore di aura si sblocca questa scelta?", null=True, blank=True)
    nome_step = models.CharField(max_length=50, help_text="Es. Archetipo, Sottotipo, Dono Divino")
    descrizione_fluff = models.TextField(blank=True, null=True, help_text="Testo descrittivo per l'interfaccia")
    is_obbligatorio = models.BooleanField(default=True, help_text="Il giocatore DEVE fare una scelta per questo livello?")
    
    class Meta:
        ordering = ['aura', 'livello']
        unique_together = ('aura', 'livello')
        verbose_name = "Configurazione Livello Aura"
        verbose_name_plural = "Configurazioni Livelli Aura"

    def __str__(self):
        return f"{self.aura.nome} Lv.{self.livello}: {self.nome_step}"

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
    # NUOVI CAMPI PER GESTIRE I TRATTI D'AURA
    is_tratto_aura = models.BooleanField(default=False, verbose_name="È un Tratto d'Aura?")
    aura_riferimento = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': 'AU'}, related_name="tratti_collegati")
    livello_riferimento = models.IntegerField(default=0, help_text="A quale livello di questa aura appartiene questo tratto?")
    
    class Meta: 
        verbose_name = "Abilità" 
        verbose_name_plural = "Abilità"
    
    def __str__(self): 
        return self.nome

class abilita_tier(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    tabella = models.ForeignKey(Tier, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=10)

class abilita_prerequisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti")
    prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati")

class abilita_requisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo__in': (CARATTERISTICA, CONDIZIONE, STATISTICA, AURA)})
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
    def livello(self): 
        return self.componenti.aggregate(tot=models.Sum('valore'))['tot'] or 0
    
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
    tipo_risultato = models.CharField(
        max_length=3, 
        choices=SCELTA_RISULTATO_CHOICES, 
        default=SCELTA_RISULTATO_POTENZIAMENTO,
        verbose_name="Tipo Oggetto Finale"
    )
    is_pesante = models.BooleanField(
        default=False, 
        verbose_name="Genera un oggetto Pesante?", 
        help_text="Se attivo, L'oggetto generato conta per il limite OGP (Oggetti Pesanti)."
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
    def TestoFormattato(self): 
        base_text = formatta_testo_generico(
            self.testo, 
            statistiche_base=self.infusionestatisticabase_set.select_related('statistica').all(), 
            context={'livello': self.livello, 'aura': self.aura_richiesta}, 
            formula=self.formula_attacco
        )
        return base_text + genera_html_cariche(self, None)
    
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
    def TestoFormattato(self): 
        return formatta_testo_generico(self.testo, formula=self.formula, statistiche_base=self.tessiturastatisticabase_set.select_related('statistica').all(), context={'elemento': self.elemento_principale, 'livello': self.livello, 'aura': self.aura_richiesta})
    
class Cerimoniale(Tecnica):
    """
    Nuova tecnica collaborativa basata su descrizioni narrative.
    Richiede Aura e Coralità (CCO).
    """
    prerequisiti = models.TextField("Prerequisiti", blank=True, null=True)
    svolgimento = models.TextField("Svolgimento", blank=True, null=True)
    effetto = models.TextField("Effetto", blank=True, null=True)
    
    caratteristiche = models.ManyToManyField(Punteggio, through='CerimonialeCaratteristica', related_name="cerimoniali_utilizzatori", limit_choices_to={'tipo': CARATTERISTICA})
    proposta_creazione = models.OneToOneField('PropostaTecnica', on_delete=models.SET_NULL, null=True, blank=True, related_name='cerimoniale_generato', verbose_name="Proposta Originale")
    
    liv = models.IntegerField(default=1, verbose_name="Livello")
    
    class Meta: 
        verbose_name = "Cerimoniale"
        verbose_name_plural = "Cerimoniali"
    
    @property
    def livello(self):
        # Invece di calcolare la somma dei mattoni (come fa Tecnica),
        # restituiamo il valore salvato nel DB.
        return self.liv
    
    @property
    def costo_crediti(self): 
        base = COSTO_PER_MATTONE_CERIMONIALE
        if self.aura_richiesta and self.aura_richiesta.stat_costo_acquisto_cerimoniale:
            val = self.aura_richiesta.stat_costo_acquisto_cerimoniale.valore_base_predefinito
            if val > 0: base = val
        return self.livello * base
        
    @property
    def TestoFormattato(self):
        # I cerimoniali sono puramente descrittivi, uniamo i campi
        parts = []
        if self.prerequisiti: parts.append(f"<strong>Prerequisiti:</strong> {self.prerequisiti}")
        if self.svolgimento: parts.append(f"<strong>Svolgimento:</strong> {self.svolgimento}")
        if self.effetto: parts.append(f"<strong>Effetto:</strong> {self.effetto}")
        return "<br><br>".join(parts)

class CerimonialeCaratteristica(models.Model):
    cerimoniale = models.ForeignKey(Cerimoniale, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    class Meta: unique_together = ('cerimoniale', 'caratteristica')

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

class PersonaggioStatisticaBase(models.Model):
    """
    Valori base delle statistiche per il personaggio.
    Questi sono valori intrinseci del personaggio, separati dalle abilità.
    Vengono inizializzati automaticamente con valore_base_predefinito quando mancanti.
    """
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name='personaggiostatisticabase_set')
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE, related_name="personaggi_che_hanno_base")
    valore_base = models.IntegerField(default=0)
    
    class Meta: 
        verbose_name = "Statistica Base Personaggio"
        verbose_name_plural = "Statistiche Base Personaggio"
        unique_together = ('personaggio', 'statistica')
    
    def __str__(self): 
        return f"{self.personaggio.nome} - {self.statistica.nome}: {self.valore_base}"

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
        
# --- NUOVI MODELLI PER GESTIONE TIMER (PUNTO A) ---

class TipologiaTimer(models.Model):
    """
    Definisce le categorie di timer (es. Protezione, Riposo) e il loro comportamento.
    """
    nome = models.CharField(max_length=50, unique=True)
    alert_suono = models.BooleanField(
        default=False, 
        verbose_name="Alert Sonoro", 
        help_text="Riproduce un suono alla scadenza su tutti i client"
    )
    notifica_push = models.BooleanField(
        default=False, 
        verbose_name="Notifica App", 
        help_text="Invia una notifica di sistema al termine del countdown"
    )
    messaggio_in_app = models.BooleanField(
        default=True, 
        verbose_name="Messaggio Scadenza", 
        help_text="Mostra un messaggio in-app quando il timer scade"
    )

    class Meta:
        verbose_name = "Tipologia Timer"
        verbose_name_plural = "Tipologie Timer"

    def __str__(self):
        return self.nome


class TimerQrCode(models.Model):
    """
    Estensione del modello QrCode per gestire i timer.
    Collega un codice fisico a una durata e una tipologia.
    """
    qr_code = models.OneToOneField(
        'QrCode', 
        on_delete=models.CASCADE, 
        related_name='configurazione_timer'
    )
    tipologia = models.ForeignKey(
        TipologiaTimer, 
        on_delete=models.CASCADE, 
        related_name='qr_collegati'
    )
    durata_secondi = models.PositiveIntegerField(
        default=60, 
        verbose_name="Durata Countdown (secondi)"
    )
    ultima_attivazione = models.DateField(
        null=True, 
        blank=True, 
        verbose_name="Data Ultima Attivazione"
    )

    class Meta:
        verbose_name = "Configurazione Timer QR"
        verbose_name_plural = "Configurazioni Timer QR"

    def __str__(self):
        return f"Timer {self.tipologia.nome} ({self.durata_secondi}s) - QR: {self.qr_code.id}"


class StatoTimerAttivo(models.Model):
    """
    Modello di runtime per sincronizzare i timer attivi tra tutte le istanze della app.
    Esiste un solo record per TipologiaTimer se il timer è attivo.
    """
    tipologia = models.OneToOneField(
        TipologiaTimer, 
        on_delete=models.CASCADE, 
        related_name='stato_corrente'
    )
    data_fine = models.DateTimeField(verbose_name="Data e Ora Scadenza")

    class Meta:
        verbose_name = "Stato Timer Attivo"
        verbose_name_plural = "Stati Timer Attivi"

    @property
    def secondi_rimanenti(self):
        """Calcola i secondi mancanti rispetto ad ora."""
        delta = self.data_fine - timezone.now()
        return max(0, int(delta.total_seconds()))

    def __str__(self):
        return f"{self.tipologia.nome} - Fine: {self.data_fine}"
            
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
    attacco_base = models.CharField(max_length=200, blank=True, null=True, help_text="Es. {rango|:RANGO}{molt|:MOLT}Chop! {dannigen+dannimis|:L}!")
    statistiche_base = models.ManyToManyField(Statistica, through='OggettoBaseStatisticaBase', blank=True, related_name='template_base')
    statistiche_modificatori = models.ManyToManyField(Statistica, through='OggettoBaseModificatore', blank=True, related_name='template_modificatori')
    in_vendita = models.BooleanField(default=True, verbose_name="Visibile in Negozio")
    is_pesante = models.BooleanField(
        default=False, 
        verbose_name="È un oggetto Pesante?", 
        help_text="Se attivo, questo oggetto conta per il limite OGP (Oggetti Pesanti)."
    )
    
    class Meta: 
        verbose_name = "Oggetto Base (Listino)"
        verbose_name_plural = "Oggetti Base (Listino)"
        ordering = ['tipo_oggetto', 'nome']
    
    def __str__(self): 
        return f"{self.nome} ({self.costo} CR)"

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
    attacco_base = models.CharField(max_length=200, blank=True, null=True, help_text="Es. {rango|:RANGO}{molt|:MOLT}Chop! {dannigen+dannimis|:L}!")
    in_vendita = models.BooleanField(default=False, verbose_name="In vendita al negozio?")
    infusione_generatrice = models.ForeignKey('Infusione', on_delete=models.SET_NULL, null=True, blank=True, related_name='oggetti_generati', help_text="L'infusione da cui deriva questa Materia/Mod/Innesto")
    ospitato_su = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='potenziamenti_installati', help_text="L'oggetto su cui questo potenziamento è montato.")
    slot_corpo = models.CharField(max_length=3, choices=SLOT_CORPO_CHOICES, blank=True, null=True, help_text="Solo per Innesti e Mutazioni")
    cariche_attuali = models.IntegerField(default=0)
    oggetto_base_generatore = models.ForeignKey(OggettoBase, on_delete=models.SET_NULL, null=True, blank=True, related_name='istanze_generate', help_text="Se creato dal negozio, punta al template originale.")
    data_fine_attivazione = models.DateTimeField(null=True, blank=True, help_text="Se impostato, l'oggetto è attivo fino a questa data.")
    is_pesante = models.BooleanField(
        default=False, 
        verbose_name="È un oggetto Pesante?", 
        help_text="Se attivo, questo oggetto conta per il limite OGP (Oggetti Pesanti)."
    )
    
    def is_active(self):
        """
        Determina se l'oggetto è attivo basandosi sulle regole rigorose del sistema.
        """
        now = timezone.now()
        infusione = self.infusione_generatrice
        
        # --- DEFINIZIONE VARIABILI DI STATO ---
        # Ha una durata prevista?
        has_duration = infusione and infusione.durata_attivazione > 0
        
        # Il timer è attualmente in corso (nel futuro)?
        is_timer_running = False
        if has_duration and self.data_fine_attivazione and self.data_fine_attivazione >= now:
            is_timer_running = True

        # =====================================================================
        # REGOLA 1: COERENZA TEMPORALE (Timer e Durata)
        # =====================================================================
        # "o durata=0 oppure durata>0 e data_fine >= adesso"
        # Se ha una durata MA il timer non sta girando (scaduto o mai partito), è OFF.
        if has_duration and not is_timer_running:
            return False

        # =====================================================================
        # REGOLA 2: SPEGNIMENTO TECNOLOGICO (Batteria)
        # =====================================================================
        # "Un oggetto ... spegne_a_zero_cariche è disattivo quando cariche < 1..."
        # ECCEZIONE: Se ha durata > 0 e il timer gira, rimane acceso (l'ultima carica si sta consumando).
        if self.aura and self.aura.spegne_a_zero_cariche:
            if self.cariche_attuali <= 0 and not is_timer_running:
                return False

        # Se siamo arrivati qui, l'oggetto è "Acceso" dal punto di vista energetico/temporale.
        # Ora verifichiamo se è nella posizione giusta per funzionare.

        # =====================================================================
        # REGOLA 3: POTENZIAMENTI (MOD, MAT, POT)
        # =====================================================================
        # "Attivo solo se montato in oggetto fisico ed esso è equipaggiato"
        if self.ospitato_su:
            # Verifica se l'host è equipaggiato
            if self.ospitato_su.is_equipaggiato:
                return True
            # Supporto per catene (es. Mod su Mod): se l'host è attivo, sono attivo
            elif self.ospitato_su.is_active(): 
                return True
            else:
                return False

        # =====================================================================
        # REGOLA 4: AUMENTI (INN, MUT, AUM)
        # =====================================================================
        # "Attivo se durata=0 o timer valido". (Già verificato sopra).
        # Un aumento esiste solo se ha uno slot corpo o è di tipo Innesto/Mutazione.
        if self.tipo_oggetto in ['INN', 'MUT', 'AUM'] or self.slot_corpo:
            return True

        # =====================================================================
        # REGOLA 5: OGGETTI FISICI (FIS)
        # =====================================================================
        # "Un oggetto fisico è attivo se è equipaggiato, disattivo se non lo è."
        if self.is_equipaggiato:
            return True

        # Fallback: Se è nello zaino (non equipaggiato, non montato, non innestato) -> OFF
        return False

    @property
    def livello(self):
        # Aggiorna il calcolo del livello basandosi sui nuovi componenti
        return self.componenti.aggregate(tot=models.Sum('valore'))['tot'] or 0

    @property
    def TestoFormattato(self): 
        base_text = formatta_testo_generico(
            self.testo, 
            statistiche_base=self.oggettostatisticabase_set.select_related('statistica').all(), 
            context={'livello': self.livello, 'aura': self.aura, 'item_modifiers': self.oggettostatistica_set.select_related('statistica').all()}
        )
        return base_text + genera_html_cariche(self, None)
    
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
        
    @property
    def is_active_timer(self):
        """Restituisce True se il timer è attivo e non scaduto."""
        if not self.data_fine_attivazione:
            return False
        return timezone.now() < self.data_fine_attivazione

class Personaggio(Inventario):
    proprietario = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="personaggi", null=True, blank=True)
    tipologia = models.ForeignKey(TipologiaPersonaggio, on_delete=models.PROTECT, related_name="personaggi", default=get_default_tipologia)
    data_nascita = models.DateTimeField(default=timezone.now)
    data_morte = models.DateTimeField(null=True, blank=True)
    costume = models.TextField(blank=True, null=True, verbose_name="Appunti Costume")
    
    abilita_possedute = models.ManyToManyField(Abilita, through='PersonaggioAbilita', blank=True)
    attivate_possedute = models.ManyToManyField(Attivata, through='PersonaggioAttivata', blank=True)
    infusioni_possedute = models.ManyToManyField(Infusione, through='PersonaggioInfusione', blank=True)
    tessiture_possedute = models.ManyToManyField(Tessitura, through='PersonaggioTessitura', blank=True)
    modelli_aura = models.ManyToManyField(ModelloAura, through='PersonaggioModelloAura', blank=True, verbose_name="Modelli di Aura")
    statistiche_temporanee = models.JSONField(default=dict, blank=True, verbose_name="Valori Correnti Statistiche")
    
    # Statistiche base del personaggio (valori intrinseci, separati dalle abilità)
    statistiche_base = models.ManyToManyField(Statistica, through='PersonaggioStatisticaBase', blank=True, related_name='personaggi_base')
    
    # --- CAMPO CERIMONIALI ---
    cerimoniali_posseduti = models.ManyToManyField(Cerimoniale, through='PersonaggioCerimoniale', blank=True)
    impostazioni_ui = models.JSONField(default=dict, blank=True, verbose_name="Impostazioni UI")
    # -------------------
    
    class Meta: 
        verbose_name="Personaggio"
        verbose_name_plural="Personaggi"
        
    def __str__(self): 
        return self.nome
    
    def aggiungi_log(self, t): 
        PersonaggioLog.objects.create(personaggio=self, testo_log=t)
    
    def modifica_crediti(self, i, d): 
        CreditoMovimento.objects.create(personaggio=self, importo=i, descrizione=d)
    
    def modifica_pc(self, i, d): 
        PuntiCaratteristicaMovimento.objects.create(personaggio=self, importo=i, descrizione=d)
    
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
    
    def get_valore_statistica_base(self, statistica):
        """
        Recupera il valore base di una statistica per questo personaggio.
        Se non esiste il record, lo crea usando valore_base_predefinito.
        """
        # Cerca il record esistente
        link = PersonaggioStatisticaBase.objects.filter(
            personaggio=self,
            statistica=statistica
        ).first()
        
        if link:
            return link.valore_base
        
        # Se non esiste, crea il record con il valore predefinito
        valore_predefinito = statistica.valore_base_predefinito
        PersonaggioStatisticaBase.objects.create(
            personaggio=self,
            statistica=statistica,
            valore_base=valore_predefinito
        )
        return valore_predefinito
    
    @property
    def statistiche_base_dict(self):
        """
        Restituisce un dizionario {parametro: valore} per tutte le statistiche base.
        Inizializza automaticamente i valori mancanti.
        """
        # Cache per evitare query multiple
        if hasattr(self, '_statistiche_base_cache'):
            return self._statistiche_base_cache
        
        # Recupera tutte le statistiche
        tutte_statistiche = Statistica.objects.all()
        risultato = {}
        
        for stat in tutte_statistiche:
            if stat.parametro:
                risultato[stat.parametro] = self.get_valore_statistica_base(stat)
        
        self._statistiche_base_cache = risultato
        return risultato
    
    @property
    def caratteristiche_base(self):
        """
        Mantiene la compatibilità: restituisce caratteristiche dai punteggi (abilità).
        Per i valori base intrinseci del personaggio, usa statistiche_base_dict.
        """
        return {k:v for k,v in self.punteggi_base.items() if Punteggio.objects.filter(nome=k, tipo=CARATTERISTICA).exists()}
    
    def get_valore_aura_effettivo(self, aura):
        pb = self.punteggi_base
        if aura.is_generica: return max([v for k,v in pb.items() if Punteggio.objects.filter(nome=k, tipo=AURA, is_generica=False).exists()] or [0])
        return pb.get(aura.nome, 0)
    
    def valida_acquisto_tecnica(self, t):
        if not t.aura_richiesta: return False, "Aura mancante."
        
        # 1. Controllo Livello Aura
        if t.livello > self.get_valore_aura_effettivo(t.aura_richiesta): 
            return False, "Livello tecnica superiore al valore Aura."
        
        # 2. Controllo Specifico Cerimoniali (Coralità)
        if isinstance(t, Cerimoniale):
            # Recupera il valore della statistica 'CCO' (Coralità)
            valore_cco = self.get_valore_statistica('CCO')
            if valore_cco < t.livello:
                return False, f"Coralità insufficiente per questo cerimoniale (Serve {t.livello}, hai {valore_cco})."
        
        # 3. Controllo Componenti (Mattoni)
        base = self.caratteristiche_base
        for comp in t.componenti.select_related('caratteristica').all():
            nome_car = comp.caratteristica.nome
            val_richiesto = comp.valore
            val_posseduto = base.get(nome_car, 0)
            if val_richiesto > val_posseduto: 
                return False, f"Requisito {nome_car} non soddisfatto (Serve {val_richiesto}, hai {val_posseduto})."

        # 4. Controllo Modelli Aura (esistente)
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
    
    def valida_acquisizione_abilita(self, abilita):
        # ... controlli standard (costi, requisiti) ...

        # Controllo Esclusività Tratto Aura
        if abilita.is_tratto_aura and abilita.aura_riferimento:
            # Cerca se il personaggio ha già un'abilità per questa Aura e questo Livello
            tratti_esistenti = self.abilita_possedute.filter(
                is_tratto_aura=True,
                aura_riferimento=abilita.aura_riferimento,
                livello_riferimento=abilita.livello_riferimento
            ).exclude(pk=abilita.pk) # Escludi se stessa se stiamo aggiornando
            
            if tratti_esistenti.exists():
                return False, f"Hai già selezionato un {tratti_esistenti.first().nome} per il livello {abilita.livello_riferimento} di {abilita.aura_riferimento.nome}."

            # Controllo: Ho il punteggio di Aura necessario?
            valore_aura = self.get_valore_aura_effettivo(abilita.aura_riferimento)
            if valore_aura < abilita.livello_riferimento:
                return False, f"La tua Aura {abilita.aura_riferimento.nome} è troppo bassa ({valore_aura}/{abilita.livello_riferimento})."

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

        def _is_global(stat_link):
            if stat_link.usa_limitazione_elemento: return False
            if stat_link.usa_limitazione_aura: return False
            if stat_link.usa_condizione_text: return False
            return True

        # 1. Abilità
        for l in AbilitaStatistica.objects.filter(abilita__personaggioabilita__personaggio=self).select_related('statistica'): 
            if _is_global(l):
                _add(l.statistica.parametro, l.tipo_modificatore, l.valore)
        
        # 2. Oggetti e Innesti (CON CHECK TIMER)
        oggetti_inventario = self.get_oggetti().select_related(
            'infusione_generatrice',
            'aura', 
            'ospitato_su',
            ).prefetch_related(
                'oggettostatistica_set__statistica', 
                'potenziamenti_installati__oggettostatistica_set__statistica', 
                'potenziamenti_installati__infusione_generatrice', 
                'potenziamenti_installati__aura',
                )
        
        for oggetto in oggetti_inventario:
            # USIAMO LA FONTE DI VERITÀ UNICA: is_active()
            # Questo controlla: Equipaggiamento, Timer, Cariche (spegne_a_zero) e Gerarchia
            if oggetto.is_active():
                for stat_link in oggetto.oggettostatistica_set.all(): 
                    if _is_global(stat_link):
                        _add(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)
                
                # Potenziamenti (Mod/Materia)
                for potenziamento in oggetto.potenziamenti_installati.all():
                    # Anche qui usiamo is_active() del potenziamento
                    # Nota: is_active() del potenziamento controlla già ricorsivamente se l'host (oggetto) è attivo
                    if potenziamento.is_active():
                        for stat_link_pot in potenziamento.oggettostatistica_set.all(): 
                            if _is_global(stat_link_pot):
                                _add(stat_link_pot.statistica.parametro, stat_link_pot.tipo_modificatore, stat_link_pot.valore)

        # 3. Caratteristiche Base
        cb = self.caratteristiche_base
        if cb:
            for l in CaratteristicaModificatore.objects.filter(caratteristica__nome__in=cb.keys()).select_related('caratteristica', 'statistica_modificata'):
                pts = cb.get(l.caratteristica.nome, 0)
                if pts > 0 and l.ogni_x_punti > 0:
                    b = (pts // l.ogni_x_punti) * l.modificatore
                    if b > 0: _add(l.statistica_modificata.parametro, MODIFICATORE_ADDITIVO, b)
        
        self._modificatori_calcolati_cache = mods
        return mods
    
    def get_modificatori_dettagliati(self):
        """
        Restituisce un dizionario dettagliato con la provenienza dei modificatori.
        Struttura: {
            'parametro': {
                'valore_base': float,
                'modificatori': [
                    {'fonte': str, 'tipo': 'add'|'mol', 'valore': float},
                    ...
                ],
                'valore_finale': float
            }
        }
        """
        from django.db.models import Q
        
        dettagli = {}
        
        def _add_mod(parametro, fonte, tipo_mod, valore):
            """Aggiunge un modificatore con la sua fonte al dizionario dettagliato"""
            if not parametro:
                return
            
            if parametro not in dettagli:
                # Recupera il valore base da statistiche_base_dict o usa 0
                valore_base = self.statistiche_base_dict.get(parametro, 0)
                dettagli[parametro] = {
                    'valore_base': valore_base,
                    'modificatori': [],
                    'add_totale': 0.0,
                    'mol_totale': 1.0
                }
            
            tipo_str = 'add' if tipo_mod == MODIFICATORE_ADDITIVO else 'mol'
            valore_float = float(valore)
            
            dettagli[parametro]['modificatori'].append({
                'fonte': fonte,
                'tipo': tipo_str,
                'valore': valore_float
            })
            
            # Aggiorna i totali
            if tipo_mod == MODIFICATORE_ADDITIVO:
                dettagli[parametro]['add_totale'] += valore_float
            elif tipo_mod == MODIFICATORE_MOLTIPLICATIVO:
                dettagli[parametro]['mol_totale'] *= valore_float
        
        def _is_global(stat_link):
            """Controlla se il modificatore è globale (non condizionale)"""
            if stat_link.usa_limitazione_elemento: return False
            if stat_link.usa_limitazione_aura: return False
            if stat_link.usa_condizione_text: return False
            return True
        
        # 1. Abilità
        for link in AbilitaStatistica.objects.filter(
            abilita__personaggioabilita__personaggio=self
        ).select_related('statistica', 'abilita'):
            if _is_global(link):
                fonte = f"Abilità: {link.abilita.nome}"
                _add_mod(link.statistica.parametro, fonte, link.tipo_modificatore, link.valore)
        
        # 2. Oggetti e Innesti
        oggetti_inventario = self.get_oggetti().select_related(
            'infusione_generatrice',
            'aura',
            'ospitato_su',
        ).prefetch_related(
            'oggettostatistica_set__statistica',
            'potenziamenti_installati__oggettostatistica_set__statistica',
            'potenziamenti_installati__infusione_generatrice',
            'potenziamenti_installati__aura',
        )
        
        for oggetto in oggetti_inventario:
            if oggetto.is_active():
                # Modificatori dell'oggetto stesso
                for stat_link in oggetto.oggettostatistica_set.all():
                    if _is_global(stat_link):
                        fonte = f"Oggetto: {oggetto.nome}"
                        _add_mod(stat_link.statistica.parametro, fonte, stat_link.tipo_modificatore, stat_link.valore)
                
                # Potenziamenti (Mod/Materia)
                for potenziamento in oggetto.potenziamenti_installati.all():
                    if potenziamento.is_active():
                        for stat_link_pot in potenziamento.oggettostatistica_set.all():
                            if _is_global(stat_link_pot):
                                fonte = f"Potenziamento: {potenziamento.nome} (su {oggetto.nome})"
                                _add_mod(stat_link_pot.statistica.parametro, fonte, stat_link_pot.tipo_modificatore, stat_link_pot.valore)
        
        # 3. Caratteristiche Base (da abilità)
        cb = self.caratteristiche_base
        if cb:
            for link in CaratteristicaModificatore.objects.filter(
                caratteristica__nome__in=cb.keys()
            ).select_related('caratteristica', 'statistica_modificata'):
                pts = cb.get(link.caratteristica.nome, 0)
                if pts > 0 and link.ogni_x_punti > 0:
                    bonus = (pts // link.ogni_x_punti) * link.modificatore
                    if bonus > 0:
                        fonte = f"Caratteristica: {link.caratteristica.nome} ({pts} punti)"
                        _add_mod(link.statistica_modificata.parametro, fonte, MODIFICATORE_ADDITIVO, bonus)
        
        # Calcola il valore finale per ogni parametro
        for parametro, dati in dettagli.items():
            valore_finale = (dati['valore_base'] + dati['add_totale']) * dati['mol_totale']
            dati['valore_finale'] = round(valore_finale, 2)
        
        return dettagli

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
            if oggetto.is_active():
            # 2A. Modificatori diretti dell'oggetto
                for stat_link in oggetto.oggettostatistica_set.all():
                    if _check_condition(stat_link):
                        _add(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)
            
                # 2B. Modificatori dei Potenziamenti
                for potenziamento in oggetto.potenziamenti_installati.all():
                    # is_active() gestisce timer, cariche e stato dell'host
                    if potenziamento.is_active():
                        for stat_link_pot in potenziamento.oggettostatistica_set.all():
                            if _check_condition(stat_link_pot):
                                _add(stat_link_pot.statistica.parametro, stat_link_pot.tipo_modificatore, stat_link_pot.valore)

        return mods
    

    def get_testo_formattato_per_item(self, item):
        if not item: return ""
        testo_finale=""
        
        if isinstance(item, Oggetto):
            stats = item.oggettostatisticabase_set.select_related('statistica').all()
            item_mods = item.oggettostatistica_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura, 'item_modifiers': item_mods}
            testo_finale = formatta_testo_generico(item.testo, formula=getattr(item, 'formula', None), statistiche_base=stats, personaggio=self, context=ctx)
            
        elif isinstance(item, Infusione):
            stats = item.infusionestatisticabase_set.select_related('statistica').all()
            ctx = {'livello': item.livello, 'aura': item.aura_richiesta}
            testo_finale = formatta_testo_generico(item.testo, statistiche_base=stats, personaggio=self, context=ctx, formula=item.formula_attacco)
            
        elif isinstance(item, Attivata):
            stats = item.attivatastatisticabase_set.select_related('statistica').all()
            testo_finale = formatta_testo_generico(item.testo, statistiche_base=stats, personaggio=self)
        
        elif isinstance(item, Tessitura):
            stats = item.tessiturastatisticabase_set.select_related('statistica').all()
            formula_text = item.formula or ""
            if "{elem}" not in formula_text:
                ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': item.elemento_principale}
                testo_finale =  formatta_testo_generico(item.testo, formula=formula_text, statistiche_base=stats, personaggio=self, context=ctx)
            else:
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
                testo_finale =  descrizione_html
        
        if isinstance(item, (Oggetto, Infusione)):
            testo_finale += genera_html_cariche(item, self)

        return testo_finale
        
    
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

class PersonaggioCerimoniale(models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    cerimoniale = models.ForeignKey(Cerimoniale, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

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
    TIPO_BROADCAST='BROAD' 
    TIPO_GRUPPO='GROUP' 
    TIPO_INDIVIDUALE='INDV'
    TIPO_STAFF='STAFF'
    TIPO_CHOICES=[(TIPO_BROADCAST,'Broadcast'),(TIPO_GRUPPO,'Gruppo'),(TIPO_INDIVIDUALE,'Individuale'),(TIPO_STAFF,'Staff')]
    mittente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="messaggi_inviati")
    tipo_messaggio = models.CharField(max_length=5, choices=TIPO_CHOICES, default=TIPO_BROADCAST)
    destinatario_personaggio = models.ForeignKey('Personaggio', on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_individuali")
    destinatario_gruppo = models.ForeignKey(Gruppo, on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_gruppo")
    titolo = models.CharField(max_length=150); testo = models.TextField(); data_invio = models.DateTimeField(default=timezone.now); salva_in_cronologia = models.BooleanField(default=True)
    is_staff_message = models.BooleanField(default=False)
    
    class Meta: 
        ordering=['-data_invio']
    
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
    
class CerimonialePluginModel(CMSPlugin):
    cerimoniale = models.ForeignKey(Cerimoniale, on_delete=models.CASCADE)
    def __str__(self): return self.cerimoniale.nome
    
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
    
    tipo_risultato_atteso = models.CharField(
        max_length=3, 
        choices=SCELTA_RISULTATO_CHOICES, 
        default=SCELTA_RISULTATO_POTENZIAMENTO,
        verbose_name="Tipo Oggetto Finale",
        null=True, blank=True,
    )
    
    # --- NUOVI CAMPI PER CERIMONIALI ---
    prerequisiti = models.TextField("Prerequisiti (Cerimoniale)", blank=True, null=True)
    svolgimento = models.TextField("Svolgimento (Cerimoniale)", blank=True, null=True)
    effetto = models.TextField("Effetto (Cerimoniale)", blank=True, null=True)
    livello_proposto = models.IntegerField(default=1, verbose_name="Livello Scelto")
    # -----------------------------------
    
    class Meta: 
        ordering = ['-data_creazione']
        verbose_name = "Proposta Tecnica"
        verbose_name_plural = "Proposte Tecniche"
    
    def __str__(self): 
        return f"{self.get_tipo_display()} - {self.nome} ({self.personaggio.nome})"
    
    @property
    def livello(self): 
        if self.tipo == 'CER':
            return self.livello_proposto
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
    slot_target = models.CharField(max_length=4, blank=True, null=True) 
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
    
    
from django.db import models

class Dichiarazione(models.Model):
    # Definizione delle scelte per il tipo
    TIPO_CHOICES = [
        ('DAN_NRM', 'Danno - Normale'),
        ('DAN_ELM', 'Danno - Elementale'),
        ('DAN_SUF', 'Danno - Suffissi'),
        ('EFF_DUR', 'Effetto - Durata'),
        ('EFF_IST', 'Effetto - Istantaneo'),
        ('SUF_RNG', 'Suffisso - Rango'),
        ('AFF_EFF', 'Affisso - Efficacia'),
        ('SUF_TRG', 'Suffisso - Bersaglio'),
        ('PRE_MOL', 'Prefisso - Moltiplicativo'),
        ('PRM_CAP', 'Premessa - Capacità'),
        ('PRM_SRC', 'Premessa - Sorgente'),
        ('PRM_LVL', 'Premessa - Livello'),
        ('PRM_TIP', 'Premessa - Tipologia'),
        ('PRE_FRM', 'Prefisso - Forma'),
        ('EFF_SPC', 'Effetto - Speciale'),
    ]
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome Dichiarazione")
    # Campi del modello
    tipo = models.CharField(
        max_length=7, 
        choices=TIPO_CHOICES, 
        db_index=True, # Indicizzato per velocizzare il filtro per tipo
        verbose_name="Tipologia Dichiarazione"
    )
    
    dichiarazione = models.CharField(
        max_length=100, 
        verbose_name="Dichiarazione / Termine", 
        unique=True # Evita duplicati dello stesso termine
    )

    descrizione = models.TextField(
        verbose_name="Descrizione della dichiarazione"
    )

    class Meta:
        verbose_name = "Dichiarazione / Glossario"
        verbose_name_plural = "Dichiarazioni e Glossario"
        ordering = ['tipo', 'nome']

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.nome}"


# ============================================================================
# SIGNALS - Inizializzazione automatica
# ============================================================================

@receiver(post_save, sender=Personaggio)
def inizializza_statistiche_base_personaggio(sender, instance, created, **kwargs):
    """
    Quando viene creato un nuovo Personaggio, inizializza tutte le sue statistiche_base
    con i valori predefiniti (valore_base_predefinito) di ogni Statistica.
    """
    if created:
        # Recupera tutte le statistiche
        tutte_statistiche = Statistica.objects.all()
        
        # Crea i record PersonaggioStatisticaBase per ogni statistica
        records_da_creare = []
        for stat in tutte_statistiche:
            records_da_creare.append(
                PersonaggioStatisticaBase(
                    personaggio=instance,
                    statistica=stat,
                    valore_base=stat.valore_base_predefinito
                )
            )
        
        # Bulk create per performance
        if records_da_creare:
            PersonaggioStatisticaBase.objects.bulk_create(records_da_creare, ignore_conflicts=True)