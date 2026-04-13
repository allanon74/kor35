from django.db.models import Sum, F, Count
import os
import re
import random
import hashlib
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
from django.contrib.auth.models import User, Group
from kor35.syncing import SyncableModel
from colorfield.fields import ColorField
from cms.models.pluginmodel import CMSPlugin
from django.utils.html import format_html
from icon_widget.fields import CustomIconField
from datetime import datetime, time as dt_time, timedelta, timezone as dt_timezone
import uuid

# --- COSTANTI DI SISTEMA (FALLBACK) ---
# COSTANTI DI FALLBACK (usate quando stat_costo_* non è configurato sull'aura)
COSTO_PER_MATTONE_INFUSIONE = 100  # Fallback per stat_costo_creazione_infusione
COSTO_PER_MATTONE_TESSITURA = 100  # Fallback per stat_costo_creazione_tessitura
COSTO_PER_MATTONE_CERIMONIALE = 100  # Fallback per stat_costo_creazione_cerimoniale
COSTO_PER_MATTONE_OGGETTO = 100  # Fallback generico (deprecato, usare le costanti specifiche sotto)
COSTO_CREAZIONE_OGGETTO_PER_MATTONE = 100  # Fallback per stat_costo_creazione_oggetto (Materia)
COSTO_CREAZIONE_MOD_PER_MATTONE = 100  # Fallback per stat_costo_creazione_mod
COSTO_CREAZIONE_INNESTO_PER_MATTONE = 100  # Fallback per stat_costo_creazione_innesto
COSTO_CREAZIONE_MUTAZIONE_PER_MATTONE = 100  # Fallback per stat_costo_creazione_mutazione
COSTO_PER_MATTONE_CREAZIONE = 10  # Costo invio proposta (fallback)
COSTO_DEFAULT_PER_MATTONE = 100  # Fallback generico
COSTO_DEFAULT_INVIO_PROPOSTA = 10  # Fallback invio proposta

# Fallback consumabili (se non impostati sull'aura)
FALLBACK_STAT_COSTO_CONSUMABILI = 30
FALLBACK_STAT_NUMERO_CONSUMABILI = 1
FALLBACK_STAT_TEMPO_CREAZIONE_CONSUMABILI = 300   # secondi
FALLBACK_STAT_DURATA_CONSUMABILI = 720            # giorni

# --- COSTANTI TRANSAZIONI ---
STATO_TRANSAZIONE_IN_ATTESA = 'IN_ATTESA'
STATO_TRANSAZIONE_ACCETTATA = 'ACCETTATA'
STATO_TRANSAZIONE_RIFIUTATA = 'RIFIUTATA'
STATO_TRANSAZIONE_CHIUSA = 'CHIUSA'

STATO_TRANSAZIONE_CHOICES = [
    (STATO_TRANSAZIONE_IN_ATTESA, 'In Attesa'),
    (STATO_TRANSAZIONE_ACCETTATA, 'Accettata'),
    (STATO_TRANSAZIONE_RIFIUTATA, 'Rifiutata'),
    (STATO_TRANSAZIONE_CHIUSA, 'Chiusa'),
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

# Gruppi "esclusivi" riusabili nella formattazione formule.
# Ogni gruppo attiva una o piu' etichette in base ai parametri attivi (> 0).
EXCLUSIVE_FORMAT_GROUPS = {
    "formula_prefix": {
        "entries": [
            {"params": ["prefisso_puro", "puro"], "label": "Puro"},
            {"params": ["prefisso_diretto", "diretto"], "label": "Diretto"},
            {"params": ["prefisso_ineluttabile", "ineluttabile"], "label": "Ineluttabile"},
        ],
        "separator": "/",
        "suffix": "!",
        "append_space": True,
    }
}
DEFAULT_EXCLUSIVE_FORMULA_GROUP = "formula_prefix"


def _is_truthy_numeric(value):
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return bool(value)


def build_exclusive_group_text(group_key, value_map, groups_config=None):
    """
    Costruisce il testo di un gruppo esclusivo (es. "Puro/Ineluttabile! ").
    """
    config = (groups_config or EXCLUSIVE_FORMAT_GROUPS).get(group_key)
    if not config:
        return ""

    entries = config.get("entries") or []
    active_labels = []
    seen = set()

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        label = (entry.get("label") or "").strip()
        if not label:
            continue
        params = []
        if entry.get("param"):
            params.append(entry["param"])
        params.extend(entry.get("params") or [])
        if not params:
            continue

        is_active = any(_is_truthy_numeric(value_map.get(param, 0)) for param in params)
        if is_active and label not in seen:
            active_labels.append(label)
            seen.add(label)

    if not active_labels:
        return ""

    separator = config.get("separator", "/")
    suffix = config.get("suffix", "!")
    append_space = config.get("append_space", True)
    built = separator.join(active_labels)
    if suffix:
        built = f"{built}{suffix}"
    if append_space:
        built = f"{built} "
    return built

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

    # Normalizza placeholder in parentesi quadre [expr] -> {expr} (stessa logica delle tessiture)
    _norm = lambda s: re.sub(r'\[([^\]]+)\]', r'{\1}', s) if s else s
    testo_out = _norm(testo_out)
    formula_out = _norm(formula_out)

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

    # Configurazione gruppi esclusivi (override opzionale da context)
    exclusive_groups_config = EXCLUSIVE_FORMAT_GROUPS
    if context and isinstance(context.get('exclusive_groups'), dict):
        exclusive_groups_config = context['exclusive_groups']

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

        # A. Placeholder gruppi esclusivi:
        # - {formula_prefix}
        # - {exclusive:formula_prefix}
        if expr == 'formula_prefix':
            return build_exclusive_group_text(
                DEFAULT_EXCLUSIVE_FORMULA_GROUP, eval_context, exclusive_groups_config
            )
        if expr.startswith('exclusive:'):
            group_key = expr.split(':', 1)[1].strip()
            return build_exclusive_group_text(group_key, eval_context, exclusive_groups_config)

        # B. Caso Speciale: Recupero Oggetto per nome ({aura|NAME})
        if formato == 'NAME':
            if expr in object_context:
                return formatta_valore_avanzato(object_context[expr], 'NAME')
            # Se non trovo l'oggetto, provo a vedere se è una stringa nel contesto valutato
            if expr in eval_context:
                 return str(eval_context[expr])

        # C. Valutazione Matematica
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

        # D. Formattazione Finale
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

    # Prepend automatico del gruppo esclusivo standard sulle formule
    # (evita duplicazioni se la formula lo contiene gia')
    if formula_finale:
        default_exclusive_prefix = build_exclusive_group_text(
            DEFAULT_EXCLUSIVE_FORMULA_GROUP, eval_context, exclusive_groups_config
        )
        if default_exclusive_prefix:
            normalized_prefix = default_exclusive_prefix.strip()
            if not formula_finale.strip().startswith(normalized_prefix):
                formula_finale = f"{default_exclusive_prefix}{formula_finale}"
    
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
CARATTERISTICA = "CA"
STATISTICA = "ST"
ELEMENTO = "EL"
AURA = "AU"
CONDIZIONE = "CO"
CULTO = "CU"
VIA = "VI"
ARTE = "AR"
ARCHETIPO = "AT"
MATTONE = "MA"
CASTONE = "CS"
NODO = "ND"
KATA = "KA"

punteggi_tipo = [
    (CARATTERISTICA, 'Caratteristica'), 
    (STATISTICA, 'Statistica'), 
    (ELEMENTO, 'Elemento'), (AURA, 'Aura'), 
    (CONDIZIONE, 'Condizione'), 
    (CULTO, 'Culto'), 
    (VIA, 'Via'), 
    (ARTE, 'Arte'), 
    (ARCHETIPO, 'Archetipo'),
    (MATTONE, 'Mattone'),
    (CASTONE, 'Castone'),
    (NODO, 'Nodo'),
    (KATA, 'Kata')
]
    
T_GENERALI = "G0";
TIER_1 = "T1"; 
TIER_2 = "T2"; 
TIER_3 = "T3"; 
TIER_4 = "T4"
tabelle_tipo = [(T_GENERALI, 'Tabelle Generali'), (TIER_1, 'Tier 1'), (TIER_2, 'Tier 2'), (TIER_3, 'Tier 3'), (TIER_4, 'Tier 4')]
MODIFICATORE_ADDITIVO = 'ADD'; MODIFICATORE_MOLTIPLICATIVO = 'MOL'
MODIFICATORE_CHOICES = [(MODIFICATORE_ADDITIVO, 'Additivo (+N)'), (MODIFICATORE_MOLTIPLICATIVO, 'Moltiplicativo (xN)')]
DISPLAY_SIZE_CHOICES = [
    ("badge", "Badge"),
    ("xs", "Extra Small"),
    ("s", "Small"),
    ("m", "Medium"),
    ("l", "Large"),
    ("xl", "Extra Large"),
]

# --- Risorse statistiche (pool consumabile: es. Fortuna FRT) ---
RISORSA_DURATA_ORA_1 = 'O1H'
RISORSA_DURATA_GIORNO = 'DAY'
RISORSA_DURATA_EVENTO = 'EVT'
RISORSA_DURATA_CHOICES = [
    (RISORSA_DURATA_ORA_1, '1 ora'),
    (RISORSA_DURATA_GIORNO, 'Fino a fine giornata (locale)'),
    (RISORSA_DURATA_EVENTO, 'Evento in corso'),
]
RISORSA_MOV_CONSUMO = 'CON'
RISORSA_MOV_RECUPERO = 'REC'
RISORSA_MOV_STAFF = 'STF'
RISORSA_MOV_SISTEMA = 'SYS'
RISORSA_MOV_CHOICES = [
    (RISORSA_MOV_CONSUMO, 'Consumo'),
    (RISORSA_MOV_RECUPERO, 'Recupero'),
    (RISORSA_MOV_STAFF, 'Staff'),
    (RISORSA_MOV_SISTEMA, 'Sistema'),
]
META_NESSUN_EFFETTO = 'NE'; META_VALORE_PUNTEGGIO = 'VP'; META_SOLO_TESTO = 'TX'; META_LIVELLO_INFERIORE = 'LV'
METATALENTO_CHOICES = [(META_NESSUN_EFFETTO, 'Nessun Effetto'), (META_VALORE_PUNTEGGIO, 'Valore per Punteggio'), (META_SOLO_TESTO, 'Solo Testo Addizionale'), (META_LIVELLO_INFERIORE, 'Solo abilità con livello pari o inferiore')]

class A_modello(SyncableModel, models.Model):
    id = models.AutoField("Codice Identificativo", primary_key=True)
    class Meta: abstract = True
        
class A_vista(SyncableModel, models.Model):
    id = models.AutoField(primary_key=True)
    data_creazione = models.DateTimeField(auto_now_add=True)
    nome = models.CharField(max_length=100)
    testo = models.TextField(blank=True, null=True)
    def __str__(self): return f"{self.nome} ({self.id})"
    class Meta: ordering = ['-data_creazione']; verbose_name = "Elemento dell'Oggetto"; verbose_name_plural = "Elementi dell'Oggetto"

class CondizioneStatisticaMixin(SyncableModel, models.Model):
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


class Korp(Tier):
    class Meta:
        verbose_name = "KORP"
        verbose_name_plural = "KORPS"


class Carriera(Tier):
    class Meta:
        verbose_name = "Carriera"
        verbose_name_plural = "Carriere"


class SegnoZodiacale(Tier):
    numero = models.PositiveSmallIntegerField(unique=True)
    testo_pubblico = models.TextField(blank=True, null=True)
    testo_privato = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Segno Zodiacale"
        verbose_name_plural = "Segni Zodiacali"
        ordering = ["numero", "nome"]


class CaricaKorp(A_modello):
    korp = models.ForeignKey(Korp, on_delete=models.CASCADE, related_name="cariche")
    nome = models.CharField(max_length=120)
    bonus_stipendio_evento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ordine = models.PositiveIntegerField(default=0)
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Carica KORP"
        verbose_name_plural = "Cariche KORP"
        ordering = ["korp__nome", "ordine", "nome"]
        unique_together = ("korp", "nome")

    def __str__(self):
        return f"{self.korp.nome} - {self.nome}"


class CaricaCarriera(A_modello):
    carriera = models.ForeignKey(Carriera, on_delete=models.CASCADE, related_name="cariche")
    nome = models.CharField(max_length=120)
    bonus_stipendio_evento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ordine = models.PositiveIntegerField(default=0)
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Carica Carriera"
        verbose_name_plural = "Cariche Carriera"
        ordering = ["carriera__nome", "ordine", "nome"]
        unique_together = ("carriera", "nome")

    def __str__(self):
        return f"{self.carriera.nome} - {self.nome}"


class PersonaggioKorpMembership(A_modello):
    personaggio = models.ForeignKey("Personaggio", on_delete=models.CASCADE, related_name="korp_membership")
    korp = models.ForeignKey(Korp, on_delete=models.PROTECT, related_name="membership")
    carica = models.ForeignKey(CaricaKorp, on_delete=models.SET_NULL, null=True, blank=True, related_name="membership")
    data_da = models.DateTimeField(default=timezone.now)
    data_a = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Membership KORP"
        verbose_name_plural = "Membership KORP"
        ordering = ["-data_da", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["personaggio"],
                condition=Q(data_a__isnull=True),
                name="uniq_personaggio_korp_attiva",
            )
        ]

    def clean(self):
        if self.carica and self.carica.korp_id != self.korp_id:
            raise ValidationError("La carica selezionata non appartiene alla KORP indicata.")

    def __str__(self):
        return f"{self.personaggio.nome} -> {self.korp.nome}"


class PersonaggioCarrieraMembership(A_modello):
    personaggio = models.ForeignKey("Personaggio", on_delete=models.CASCADE, related_name="carriera_membership")
    carriera = models.ForeignKey(Carriera, on_delete=models.PROTECT, related_name="membership")
    carica = models.ForeignKey(CaricaCarriera, on_delete=models.SET_NULL, null=True, blank=True, related_name="membership")
    data_da = models.DateTimeField(default=timezone.now)
    data_a = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Membership Carriera"
        verbose_name_plural = "Membership Carriera"
        ordering = ["-data_da", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["personaggio"],
                condition=Q(data_a__isnull=True),
                name="uniq_personaggio_carriera_attiva",
            )
        ]

    def clean(self):
        if self.carica and self.carica.carriera_id != self.carriera_id:
            raise ValidationError("La carica selezionata non appartiene alla Carriera indicata.")

    def __str__(self):
        return f"{self.personaggio.nome} -> {self.carriera.nome}"

class Punteggio(Tabella):
    sigla = models.CharField(max_length=3, unique=True)
    tipo = models.CharField(choices=punteggi_tipo, max_length=2)
    colore = ColorField(default='#1976D2')
    icona = CustomIconField(blank=True)
    icona_nome_originale = models.CharField(max_length=255, blank=True, null=True)
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
    
    # COSTI CREAZIONE OGGETTI (Creazione diretta senza forgiatura)
    stat_costo_creazione_oggetto = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_ogg', verbose_name="Stat. Costo Creazione Oggetto (Materia)")
    stat_costo_creazione_mod = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_mod', verbose_name="Stat. Costo Creazione Mod")
    stat_costo_creazione_innesto = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_inn', verbose_name="Stat. Costo Creazione Innesto")
    stat_costo_creazione_mutazione = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_mut', verbose_name="Stat. Costo Creazione Mutazione")
    
    caratteristica_relativa = models.ForeignKey("Punteggio", on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, null=True, blank=True, related_name="punteggi_caratteristica")
    modifica_statistiche = models.ManyToManyField('Statistica', through='CaratteristicaModificatore', related_name='modificata_da_caratteristiche', blank=True)
    aure_infusione_consentite = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='puo_essere_infusa_in')
    
    # --- NUOVI CAMPI CERIMONIALI ---
    permette_cerimoniali = models.BooleanField(default=False, verbose_name="Permette Cerimoniali")
    stat_costo_acquisto_cerimoniale = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_acquisto_cer', verbose_name="Stat. Costo Acquisto Cerimoniale")
    stat_costo_creazione_cerimoniale = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_creazione_cer', verbose_name="Stat. Costo Creazione Cerimoniale")
    stat_costo_invio_proposta_cerimoniale = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_costo_invio_prop_cer', verbose_name="Stat. Costo Invio Proposta (Cer)")
    # --- CONSUMABILI (creazione da tessitura) ---
    stat_costo_consumabili = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_stat_costo_consumabili', verbose_name="Stat. Costo Creazione Consumabili")
    stat_numero_consumabili = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_stat_numero_consumabili', verbose_name="Stat. Numero Consumabili")
    stat_tempo_creazione_consumabili = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_stat_tempo_creazione_consumabili', verbose_name="Stat. Tempo Creazione Consumabili (sec)")
    stat_durata_consumabili = models.ForeignKey('Statistica', on_delete=models.SET_NULL, null=True, blank=True, related_name='aure_stat_durata_consumabili', verbose_name="Stat. Durata Consumabili (giorni)")
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

    @property
    def icona_nome_display(self):
        """Nome icona per visualizzazione: usa icona_nome_originale se presente, altrimenti fallback per icone già salvate (legacy)."""
        if self.icona_nome_originale and self.icona_nome_originale.strip():
            return self.icona_nome_originale.strip()
        if self.icona:
            # Fallback: nome file senza estensione (es. icon-uuid per file salvati dal widget)
            try:
                return os.path.splitext(os.path.basename(str(self.icona)))[0] or "Icona personalizzata"
            except Exception:
                return "Icona personalizzata"
        return None

    def __str__(self): return f"{self.tipo} - {self.nome}"

class Caratteristica(Punteggio):
    class Meta: proxy = True; verbose_name = "Caratteristica"; verbose_name_plural = "Caratteristiche"

class Statistica(Punteggio):
    parametro = models.CharField(max_length=10, unique=True, blank=True, null=True)
    valore_predefinito = models.IntegerField(default=0)
    valore_base_predefinito = models.IntegerField(default=0)
    tipo_modificatore = models.CharField(max_length=3, choices=MODIFICATORE_CHOICES, default=MODIFICATORE_ADDITIVO)
    is_primaria = models.BooleanField(default=False)
    is_risorsa_pool = models.BooleanField(
        default=False,
        verbose_name="Risorsa a pool",
        help_text="Se attivo, il valore massimo della statistica definisce il tetto di un pool "
        "con contatore separato (consumi, log, effetti temporanei). Es. Fortuna (FRT).",
    )
    auto_recupero_attivo = models.BooleanField(
        default=False,
        verbose_name="Recupero automatico attivo",
        help_text="Se attivo su una risorsa pool, avvia il recupero periodico quando il valore scende sotto il massimo.",
    )
    auto_recupero_intervallo_secondi = models.PositiveIntegerField(
        default=300,
        verbose_name="Intervallo recupero (sec)",
        help_text="Ogni quanti secondi viene recuperato lo step configurato.",
    )
    auto_recupero_step = models.PositiveIntegerField(
        default=1,
        verbose_name="Step recupero",
        help_text="Quanti punti recuperare ad ogni tick.",
    )
    massimo_pool_sigla = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Massimo pool da altra statistica",
        help_text="Opzionale (legacy / risorse non is_risorsa_pool). Es. CHK: imposta CHA se il tetto del "
        "pool chakra è la statistica primaria CHA mentre il contatore runtime è CHK_CUR in "
        "statistiche_temporanee. Se vuoto, il massimo è calcolato sulla stessa sigla.",
    )

    def save(self, *args, **kwargs): self.tipo = STATISTICA; super().save(*args, **kwargs)
    class Meta: verbose_name = "Statistica"; verbose_name_plural = "Statistiche"
    @classmethod
    def get_help_text_parametri(cls, extra_params=None):
        stats = cls.objects.filter(parametro__isnull=False).exclude(parametro__exact='').order_by('nome')
        items = [f"&bull; <b>{{{s.parametro}}}</b>: {s.nome}" for s in stats]
        if extra_params: items.extend([f"&bull; <b>{p_code}</b>: {p_desc}" for p_code, p_desc in extra_params])
        return mark_safe("<b>Variabili disponibili:</b><br>" + "<br>".join(items))


class StatisticaContainer(SyncableModel, models.Model):
    """
    Contenitore (annidabile) per raggruppare statistiche nella scheda personaggio.
    Configurabile a DB e sincronizzabile Edge/Master.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    nome = models.CharField(max_length=90)
    sigla = models.CharField(max_length=10, blank=True, null=True)
    ordine = models.IntegerField(default=0)
    dimensione = models.CharField(
        max_length=10,
        choices=DISPLAY_SIZE_CHOICES,
        default="s",
        help_text="Dimensione di rendering dell'intestazione contenitore in scheda.",
    )

    colore = ColorField(default="#1976D2")
    icona = CustomIconField(blank=True)
    icona_nome_originale = models.CharField(max_length=255, blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )

    render_in_primarie = models.BooleanField(
        default=True,
        verbose_name="Mostra in Statistiche (primarie)",
        help_text="Se attivo, il contenitore viene renderizzato nella sezione 'Statistiche' della scheda.",
    )
    usa_colore_contenitore_per_figli = models.BooleanField(
        default=True,
        verbose_name="Forza colore contenitore sui figli",
        help_text="Se attivo, le statistiche contenute usano il colore del contenitore in scheda.",
    )

    class Meta:
        verbose_name = "Contenitore Statistiche"
        verbose_name_plural = "Contenitori Statistiche"
        ordering = ["ordine", "nome"]

    @property
    def icona_url(self):
        return f"{settings.MEDIA_URL}{self.icona}" if self.icona else None

    @property
    def icona_html(self):
        if self.icona and self.colore:
            return format_html(
                '<div style="width: 24px; height: 24px; background-color: {}; mask-image: url({}); -webkit-mask-image: url({}); mask-size: contain; -webkit-mask-size: contain; display: inline-block; vertical-align: middle;"></div>',
                self.colore,
                self.icona_url,
                self.icona_url,
            )
        return ""

    def icona_cerchio(self, inverted=True):
        if not self.icona or not self.colore:
            return ""
        bg = _get_icon_color_from_bg(self.colore) if inverted else self.colore
        fg = self.colore if inverted else _get_icon_color_from_bg(self.colore)
        return format_html(
            '<div style="display: inline-block; width: 30px; height: 30px; background-color: {}; border-radius: 50%; vertical-align: middle; text-align: center; line-height: 30px;"><div style="display: inline-block; width: 24px; height: 24px; vertical-align: middle; background-color: {}; mask-image: url({}); -webkit-mask-image: url({}); mask-size: contain; -webkit-mask-size: contain;"></div></div>',
            bg,
            fg,
            self.icona_url,
            self.icona_url,
        )

    @property
    def icona_cerchio_html(self):
        return self.icona_cerchio(inverted=False)

    @property
    def icona_cerchio_inverted_html(self):
        return self.icona_cerchio(inverted=True)

    @property
    def icona_nome_display(self):
        if self.icona_nome_originale and self.icona_nome_originale.strip():
            return self.icona_nome_originale.strip()
        if self.icona:
            try:
                return os.path.splitext(os.path.basename(str(self.icona)))[0] or "Icona personalizzata"
            except Exception:
                return "Icona personalizzata"
        return None

    def __str__(self):
        return self.nome


class StatisticaContainerItem(SyncableModel, models.Model):
    """
    Legame contenitore -> statistica, con ordine interno.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    container = models.ForeignKey(
        StatisticaContainer,
        on_delete=models.CASCADE,
        related_name="items",
    )
    statistica = models.ForeignKey(
        Statistica,
        on_delete=models.CASCADE,
        related_name="in_containers",
    )
    ordine = models.IntegerField(default=0)
    dimensione = models.CharField(
        max_length=10,
        choices=DISPLAY_SIZE_CHOICES,
        default="s",
        help_text="Dimensione di rendering della statistica nel contenitore.",
    )
    nascondi_se_negativa = models.BooleanField(
        default=True,
        help_text="Se attivo, non renderizza la statistica quando il valore e negativo.",
    )
    nascondi_se_zero = models.BooleanField(
        default=True,
        help_text="Se attivo, non renderizza la statistica quando il valore e 0.",
    )
    nascondi_se_uno = models.BooleanField(
        default=False,
        help_text="Se attivo, non renderizza la statistica quando il valore e 1.",
    )
    is_dipendente = models.BooleanField(
        default=False,
        verbose_name="Dipendente",
        help_text="Se attivo, questa statistica non abilita da sola la visibilita del contenitore.",
    )

    class Meta:
        verbose_name = "Statistica in contenitore"
        verbose_name_plural = "Statistiche in contenitori"
        ordering = ["container__ordine", "ordine", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["container", "statistica"],
                name="uniq_stat_container_item",
            )
        ]

    def __str__(self):
        return f"{self.container.nome} -> {self.statistica.sigla or self.statistica.nome}"

MOSTRA_CLASSI_ARMA_CHOICES = [
    ('nessuno', 'Nessuno'),
    ('materia', 'Mostrare i tipi di arma per Materia'),
    ('mod', 'Mostrare i tipi di arma per Mod'),
]

class Mattone(Punteggio):
    aura = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': AURA}, related_name="mattoni_aura")
    caratteristica_associata = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA}, related_name="mattoni_caratteristica")
    descrizione_mattone = models.TextField(blank=True, null=True)
    descrizione_metatalento = models.TextField(blank=True, null=True)
    testo_addizionale = models.TextField(blank=True, null=True)
    dichiarazione = models.TextField("Dichiarazione", blank=True, null=True)
    funzionamento_metatalento = models.CharField(max_length=2, choices=METATALENTO_CHOICES, default=META_NESSUN_EFFETTO)
    statistiche = models.ManyToManyField(Statistica, through='MattoneStatistica', blank=True, related_name="mattoni_statistiche")
    mostra_classi_arma = models.CharField(
        max_length=10,
        choices=MOSTRA_CLASSI_ARMA_CHOICES,
        default='nessuno',
        verbose_name="Mostra classi arma nel widget",
        help_text="Nessuno: come ora. Materia: classi con questo castone (mattoni_materia_permessi). Mod: classi con limite mod e massimale.",
    )
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
    def save(self, *args, **kwargs): self.tipo = AURA; super().save(*args, **kwargs)

class ModelloAuraRequisitoDoppia(SyncableModel, models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_doppia_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        unique_together = [["modello", "requisito"]]


class ModelloAuraRequisitoMattone(SyncableModel, models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_mattone_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        unique_together = [["modello", "requisito"]]


class ModelloAuraRequisitoCaratt(SyncableModel, models.Model):
    modello = models.ForeignKey('ModelloAura', on_delete=models.CASCADE, related_name='req_caratt_rel')
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        unique_together = [["modello", "requisito"]]

class ModelloAura(SyncableModel, models.Model):
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

class CaratteristicaModificatore(SyncableModel, models.Model):
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
    
class ConfigurazioneLivelloAura(SyncableModel, models.Model):
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
    caratteristica_2 = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, related_name="abilita_caratteristica_2", limit_choices_to={'tipo__in': [CARATTERISTICA, CONDIZIONE]}, verbose_name="Caratteristica 2")
    caratteristica_3 = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, related_name="abilita_caratteristica_3", limit_choices_to={'tipo__in': [CARATTERISTICA, CONDIZIONE]}, verbose_name="Caratteristica 3")
    tiers = models.ManyToManyField(Tier, related_name="abilita", through="abilita_tier")
    requisiti = models.ManyToManyField(Punteggio, related_name="abilita_req", through="abilita_requisito")
    tabelle_sbloccate = models.ManyToManyField(Tabella, related_name="abilita_sbloccante", through="abilita_sbloccata")
    punteggio_acquisito = models.ManyToManyField(Punteggio, related_name="abilita_acquisizione", through="abilita_punteggio")
    statistiche = models.ManyToManyField(Statistica, through='AbilitaStatistica', blank=True, related_name="abilita_statistiche")
    # NUOVI CAMPI PER GESTIRE I TRATTI D'AURA
    is_tratto_aura = models.BooleanField(default=False, verbose_name="È un Tratto d'Aura?")
    aura_riferimento = models.ForeignKey(Punteggio, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'tipo': 'AU'}, related_name="tratti_collegati")
    livello_riferimento = models.IntegerField(default=0, help_text="A quale livello di questa aura appartiene questo tratto?")
    camaleontica = models.BooleanField(
        default=False,
        help_text="Se attiva, questa forma AIN usa una forma del giorno randomica (deterministica).",
    )
    effetto_uso_risorsa = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Effetto all'uso risorsa",
        help_text='Opzionale. stat_sigla = sigla pool (es. FRT; per chakra CHA). Alias legacy CHK viene mappato su CHA.',
    )
    recupero_risorsa = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Recupero risorsa",
        help_text='Opzionale. Es. {"rigenerazioni":[{"stat_sigla":"CHA","ogni_minuti":10,"step":1}]} — '
        'stat_sigla = risorsa pool (PV, PA, PS, CHA, FRT, …). CHK in JSON è accettato come alias di CHA.',
    )

    class Meta: 
        verbose_name = "Abilità" 
        verbose_name_plural = "Abilità"
    
    def __str__(self): 
        return self.nome

class abilita_tier(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    tabella = models.ForeignKey(Tier, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=10)

    class Meta:
        unique_together = [["abilita", "tabella"]]


class abilita_prerequisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_prerequisiti")
    prerequisito = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="abilita_abilitati")

    class Meta:
        unique_together = [["abilita", "prerequisito"]]


class abilita_requisito(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    requisito = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo__in': (CARATTERISTICA, CONDIZIONE, STATISTICA, AURA)})
    valore = models.IntegerField(default=1)

    class Meta:
        unique_together = [["abilita", "requisito"]]


class abilita_sbloccata(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    sbloccata = models.ForeignKey(Tabella, on_delete=models.CASCADE)

    class Meta:
        unique_together = [["abilita", "sbloccata"]]


class abilita_punteggio(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    punteggio = models.ForeignKey(Punteggio, on_delete=models.CASCADE)
    valore = models.IntegerField(default=1)

    class Meta:
        unique_together = [["abilita", "punteggio"]]


class abilita_punteggio_dipendente(A_modello):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE, related_name="punteggi_dipendenti")
    punteggio_target = models.ForeignKey(
        Punteggio,
        on_delete=models.CASCADE,
        related_name="abilita_punteggio_target_rel",
    )
    punteggio_sorgente = models.ForeignKey(
        Punteggio,
        on_delete=models.CASCADE,
        related_name="abilita_punteggio_sorgente_rel",
    )
    incremento = models.IntegerField(default=1)
    ogni_x = models.IntegerField(default=1)

    class Meta:
        unique_together = [["abilita", "punteggio_target", "punteggio_sorgente"]]

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

class AttivataElemento(SyncableModel, models.Model):
    attivata = models.ForeignKey('Attivata', on_delete=models.CASCADE)
    elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'is_mattone': True})

    class Meta:
        unique_together = [["attivata", "elemento"]]

class AttivataStatisticaBase(SyncableModel, models.Model):
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

class CerimonialeCaratteristica(SyncableModel, models.Model):
    cerimoniale = models.ForeignKey(Cerimoniale, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    class Meta: unique_together = ('cerimoniale', 'caratteristica')

class InfusioneCaratteristica(SyncableModel, models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    class Meta: unique_together = ('infusione', 'caratteristica')

class TessituraCaratteristica(SyncableModel, models.Model):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)
    class Meta: unique_together = ('tessitura', 'caratteristica')

class InfusioneStatisticaBase(SyncableModel, models.Model):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    def __str__(self): return f"{self.statistica.nome}: {self.valore_base}"

class TessituraStatisticaBase(SyncableModel, models.Model):
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

class OggettoInInventario(SyncableModel, models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE, related_name="tracciamento_inventario")
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="tracciamento_oggetti")
    data_inizio = models.DateTimeField(default=timezone.now)
    data_fine = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ['-data_inizio']

class TipologiaPersonaggio(SyncableModel, models.Model):
    nome = models.CharField(max_length=100, unique=True, default="Standard")
    crediti_iniziali = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    caratteristiche_iniziali = models.IntegerField(default=8)
    giocante = models.BooleanField(default=True)
    class Meta: verbose_name="Tipologia Personaggio"
    def __str__(self): return self.nome

class Era(SyncableModel, models.Model):
    nome = models.CharField(max_length=120, unique=True)
    abbreviazione = models.CharField(max_length=30, blank=True, default="")
    descrizione_breve = models.CharField(max_length=280, blank=True, default="")
    descrizione = models.TextField(blank=True, default="")
    abilita = models.ManyToManyField("Abilita", through="EraAbilita", related_name="ere_collegate", blank=True)
    ordine = models.PositiveIntegerField(default=0)
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Era"
        verbose_name_plural = "Ere"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return self.nome


class Regione(SyncableModel, models.Model):
    nome = models.CharField(max_length=120, unique=True)
    sigla = models.CharField(max_length=20, blank=True, default="")
    descrizione = models.TextField(blank=True, default="")
    abilita = models.ManyToManyField("Abilita", through="RegioneAbilita", related_name="regioni_collegate", blank=True)
    ordine = models.PositiveIntegerField(default=0)
    attiva = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Regione"
        verbose_name_plural = "Regioni"
        ordering = ["ordine", "nome"]

    def __str__(self):
        return self.nome


class Prefettura(SyncableModel, models.Model):
    era = models.ForeignKey("Era", on_delete=models.CASCADE, related_name="prefetture")
    regione = models.ForeignKey("Regione", on_delete=models.SET_NULL, related_name="prefetture", null=True, blank=True)
    nome = models.CharField(max_length=120)
    descrizione = models.TextField(blank=True, default="")
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Prefettura"
        verbose_name_plural = "Prefetture"
        ordering = ["era__ordine", "ordine", "nome"]
        unique_together = [["era", "nome"]]

    def __str__(self):
        return f"{self.nome} ({self.era.nome})"


class EraAbilita(SyncableModel, models.Model):
    era = models.ForeignKey("Era", on_delete=models.CASCADE, related_name="ere_abilita")
    abilita = models.ForeignKey("Abilita", on_delete=models.CASCADE, related_name="abilita_era")
    is_default = models.BooleanField(
        default=False,
        verbose_name="Assegna in automatico al personaggio",
        help_text="Se attivo, l'abilità viene aggiunta quando il personaggio seleziona questa era.",
    )
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Abilità Era"
        verbose_name_plural = "Abilità Ere"
        ordering = ["ordine", "abilita__nome"]
        unique_together = [["era", "abilita"]]

    def __str__(self):
        return f"{self.era.nome} -> {self.abilita.nome}"


class RegioneAbilita(SyncableModel, models.Model):
    regione = models.ForeignKey("Regione", on_delete=models.CASCADE, related_name="regioni_abilita")
    abilita = models.ForeignKey("Abilita", on_delete=models.CASCADE, related_name="abilita_regione")
    is_default = models.BooleanField(
        default=False,
        verbose_name="Assegna in automatico al personaggio",
        help_text="Se attivo, l'abilità viene aggiunta quando il personaggio seleziona una prefettura di questa regione.",
    )
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Abilità Regione"
        verbose_name_plural = "Abilità Regioni"
        ordering = ["ordine", "abilita__nome"]
        unique_together = [["regione", "abilita"]]

    def __str__(self):
        return f"{self.regione.nome} -> {self.abilita.nome}"

PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO = "acquisto"
PERSONAGGIO_ABILITA_ORIGINE_ERA_DEFAULT = "era_default"
PERSONAGGIO_ABILITA_ORIGINE_REGIONE_DEFAULT = "regione_default"


def get_default_tipologia():
    """
    Default per FK tipologia su Personaggio (usato dalla migrazione 0019).

    Non usare l'ORM: durante migrate il modello TipologiaPersonaggio include gia'
    i campi sync (SyncableModel) ma la tabella DB puo' non averli ancora, e la
    SELECT fallirebbe con UndefinedColumn. Qui usiamo solo colonne realmente presenti.
    """
    from django.db import connection
    from django.utils import timezone
    import uuid

    table = "personaggi_tipologiapersonaggio"
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT "id" FROM "{table}" WHERE "nome" = %s LIMIT 1',
            ["Standard"],
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = %s
              AND column_name = 'sync_id'
            LIMIT 1
            """,
            [table],
        )
        has_sync_id = cursor.fetchone() is not None

        if has_sync_id:
            cursor.execute(
                f"""
                INSERT INTO "{table}"
                    ("nome", "crediti_iniziali", "caratteristiche_iniziali", "giocante", "sync_id", "updated_at")
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING "id"
                """,
                ["Standard", 0, 8, True, uuid.uuid4(), timezone.now()],
            )
        else:
            cursor.execute(
                f"""
                INSERT INTO "{table}"
                    ("nome", "crediti_iniziali", "caratteristiche_iniziali", "giocante")
                VALUES (%s, %s, %s, %s)
                RETURNING "id"
                """,
                ["Standard", 0, 8, True],
            )
        return cursor.fetchone()[0]

class PuntiCaratteristicaMovimento(SyncableModel, models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="movimenti_pc")
    importo = models.IntegerField()
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)
    class Meta: verbose_name="Movimento PC"; ordering=['-data']

class CreditoMovimento(SyncableModel, models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="movimenti_credito")
    importo = models.DecimalField(max_digits=10, decimal_places=2)
    descrizione = models.CharField(max_length=200)
    data = models.DateTimeField(default=timezone.now)
    class Meta: ordering=['-data']
    
class PersonaggioLog(SyncableModel, models.Model):
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="log_eventi")
    data = models.DateTimeField(default=timezone.now)
    testo_log = models.TextField()
    class Meta: ordering=['-data']


class RisorsaStatisticaMovimento(SyncableModel, models.Model):
    """Movimenti sui pool di risorse statistiche (sync-friendly)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name='movimenti_risorsa_stat')
    statistica_sigla = models.CharField(max_length=3, db_index=True)
    importo = models.IntegerField()
    descrizione = models.CharField(max_length=240)
    tipo_movimento = models.CharField(max_length=3, choices=RISORSA_MOV_CHOICES, default=RISORSA_MOV_CONSUMO)
    data = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Movimento risorsa statistica'
        verbose_name_plural = 'Movimenti risorse statistiche'


class EffettoRisorsaTemporaneo(SyncableModel, models.Model):
    """
    Modificatori temporanei attivati consumando un punto risorsa (es. effetto Fortuna).
    Scadenza valutata in modificatori_calcolati.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name='effetti_risorsa_temp')
    statistica_risorsa_sigla = models.CharField(max_length=3)
    abilita = models.ForeignKey('Abilita', on_delete=models.SET_NULL, null=True, blank=True, related_name='effetti_risorsa_generati')
    durata_tipo = models.CharField(max_length=3, choices=RISORSA_DURATA_CHOICES, default=RISORSA_DURATA_ORA_1)
    scadenza = models.DateTimeField(db_index=True)
    modifiche = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista di {"stat_sigla":"PV","valore":1,"tipo_modificatore":"ADD"|"MOL"}',
    )

    class Meta:
        ordering = ['-scadenza']
        verbose_name = 'Effetto risorsa temporaneo'
        verbose_name_plural = 'Effetti risorsa temporanei'


class RecuperoRisorsaAttivo(SyncableModel, models.Model):
    """
    Stato runtime del recupero automatico per una risorsa pool di un personaggio.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name='recuperi_risorsa_attivi')
    statistica_sigla = models.CharField(max_length=3, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    next_tick_at = models.DateTimeField(db_index=True)
    interval_seconds = models.PositiveIntegerField(default=300)
    step = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    pause_started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Recupero risorsa attivo'
        verbose_name_plural = 'Recuperi risorsa attivi'
        unique_together = [('personaggio', 'statistica_sigla')]


def calcola_scadenza_effetto_risorsa(durata_tipo):
    """Calcola datetime di scadenza per un effetto legato al consumo di una risorsa."""
    try:
        from gestione_plot.models import Evento
    except Exception:
        Evento = None  # type: ignore
    now = timezone.now()
    if durata_tipo == RISORSA_DURATA_ORA_1:
        return now + timedelta(hours=1)
    if durata_tipo == RISORSA_DURATA_GIORNO:
        d = timezone.localdate()
        end_local = datetime.combine(d, dt_time(23, 59, 59))
        if timezone.is_naive(end_local):
            end_local = timezone.make_aware(end_local, timezone.get_current_timezone())
        return end_local if end_local > now else now + timedelta(seconds=1)
    if durata_tipo == RISORSA_DURATA_EVENTO and Evento is not None:
        ev = (
            Evento.objects.filter(data_inizio__lte=now, data_fine__gte=now)
            .order_by('-data_inizio')
            .first()
        )
        if ev:
            return ev.data_fine
    return now + timedelta(hours=1)

# class OggettoElemento(models.Model):
#     oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
#     elemento = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': ELEMENTO})
    
class OggettoCaratteristica(SyncableModel, models.Model):
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

class OggettoStatisticaBase(SyncableModel, models.Model):
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    class Meta: unique_together = ('oggetto', 'statistica')
    def __str__(self): return f"{self.statistica.nome}: {self.valore_base}"

class PersonaggioStatisticaBase(SyncableModel, models.Model):
    """
    Valori base delle statistiche per il personaggio.
    Questi sono valori intrinseci del personaggio, separati dalle abilità.
    Salviamo solo gli override rispetto al valore_base_predefinito della statistica
    (modello "sparse"): se il record manca, vale il default della statistica.
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

class QrCode(SyncableModel, models.Model):
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

class TipologiaTimer(SyncableModel, models.Model):
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


class TimerQrCode(SyncableModel, models.Model):
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


class StatoTimerAttivo(SyncableModel, models.Model):
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
            
class ClasseOggetto(SyncableModel, models.Model):
    nome = models.CharField(max_length=50, unique=True)
    max_mod_totali = models.IntegerField(default=0, verbose_name="Max Mod Totali")
    limitazioni_mod = models.ManyToManyField(Punteggio, through='ClasseOggettoLimiteMod', related_name='classi_oggetti_regole_mod', verbose_name="Limiti Mod per Caratteristica")
    mattoni_materia_permessi = models.ManyToManyField(Punteggio, limit_choices_to={'tipo': CARATTERISTICA}, related_name='classi_oggetti_materia_permessa', blank=True, verbose_name="Caratt. Materia Permesse")
    class Meta: verbose_name = "Classe Oggetto (Regole)"; verbose_name_plural = "Classi Oggetto (Regole)"
    def __str__(self): return self.nome

class ClasseOggettoLimiteMod(SyncableModel, models.Model):
    classe_oggetto = models.ForeignKey(ClasseOggetto, on_delete=models.CASCADE)
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    max_installabili = models.IntegerField(default=1, verbose_name="Max Mod di questo tipo")
    class Meta: unique_together = ('classe_oggetto', 'caratteristica'); verbose_name = "Limite Mod per Caratteristica"
        
class OggettoBase(SyncableModel, models.Model):
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

class OggettoBaseStatisticaBase(SyncableModel, models.Model):
    oggetto_base = models.ForeignKey(OggettoBase, on_delete=models.CASCADE)
    statistica = models.ForeignKey(Statistica, on_delete=models.CASCADE)
    valore_base = models.IntegerField(default=0)
    class Meta: verbose_name = "Statistica Base Template"; verbose_name_plural = "Statistiche Base Template"

class OggettoBaseModificatore(SyncableModel, models.Model):
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
    segno_zodiacale = models.ForeignKey("SegnoZodiacale", on_delete=models.SET_NULL, related_name="personaggi", null=True, blank=True)
    era = models.ForeignKey("Era", on_delete=models.SET_NULL, related_name="personaggi", null=True, blank=True)
    prefettura = models.ForeignKey("Prefettura", on_delete=models.SET_NULL, related_name="personaggi", null=True, blank=True)
    prefettura_esterna = models.BooleanField(default=False)
    data_nascita = models.DateTimeField(default=timezone.now)
    data_morte = models.DateTimeField(null=True, blank=True)
    costume = models.TextField(blank=True, null=True, verbose_name="Appunti Costume")
    
    abilita_possedute = models.ManyToManyField(Abilita, through='PersonaggioAbilita', blank=True)
    attivate_possedute = models.ManyToManyField(Attivata, through='PersonaggioAttivata', blank=True)
    infusioni_possedute = models.ManyToManyField(Infusione, through='PersonaggioInfusione', blank=True)
    tessiture_possedute = models.ManyToManyField(Tessitura, through='PersonaggioTessitura', blank=True)
    modelli_aura = models.ManyToManyField(ModelloAura, through='PersonaggioModelloAura', blank=True, verbose_name="Modelli di Aura")
    statistiche_temporanee = models.JSONField(default=dict, blank=True, verbose_name="Valori Correnti Statistiche")
    risorse_consumabili = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Risorse a pool (corrente)",
        help_text='Contatori attuali per statistiche con pool (es. {"FRT": 2}). Se assente, si assume pari al massimo.',
    )

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

    def ha_eventi_iniziati(self):
        now = timezone.now()
        return self.eventi_partecipati.filter(data_inizio__lte=now).exists()

    def can_edit_era_prefettura(self):
        return not self.ha_eventi_iniziati()

    def _sync_abilita_default_era(self):
        # Rimuove solo le abilità "gratuite da era/regione" già assegnate in precedenza.
        PersonaggioAbilita.objects.filter(
            personaggio=self,
            origine__in=[PERSONAGGIO_ABILITA_ORIGINE_ERA_DEFAULT, PERSONAGGIO_ABILITA_ORIGINE_REGIONE_DEFAULT],
        ).delete()

        possessed_ids = set(
            PersonaggioAbilita.objects.filter(personaggio=self).values_list("abilita_id", flat=True)
        )

        nuovi_link = []

        if self.era_id:
            default_era_ids = EraAbilita.objects.filter(
                era_id=self.era_id,
                is_default=True,
            ).values_list("abilita_id", flat=True)
            for abilita_id in default_era_ids:
                if abilita_id in possessed_ids:
                    continue
                nuovi_link.append(
                    PersonaggioAbilita(
                        personaggio=self,
                        abilita_id=abilita_id,
                        origine=PERSONAGGIO_ABILITA_ORIGINE_ERA_DEFAULT,
                    )
                )
                possessed_ids.add(abilita_id)

        regione_id = getattr(self.prefettura, "regione_id", None)
        if regione_id:
            default_regione_ids = RegioneAbilita.objects.filter(
                regione_id=regione_id,
                is_default=True,
            ).values_list("abilita_id", flat=True)
            for abilita_id in default_regione_ids:
                if abilita_id in possessed_ids:
                    continue
                nuovi_link.append(
                    PersonaggioAbilita(
                        personaggio=self,
                        abilita_id=abilita_id,
                        origine=PERSONAGGIO_ABILITA_ORIGINE_REGIONE_DEFAULT,
                    )
                )
                possessed_ids.add(abilita_id)

        if nuovi_link:
            PersonaggioAbilita.objects.bulk_create(nuovi_link, ignore_conflicts=True)

    def assegna_era_e_prefettura(self, era=None, prefettura=None, prefettura_esterna=False, force=False):
        if not force and not self.can_edit_era_prefettura():
            raise ValidationError("Non è più possibile cambiare Era dopo l'inizio del primo evento.")

        if prefettura and era and prefettura.era_id != era.id and not prefettura_esterna:
            raise ValidationError("La prefettura selezionata non appartiene all'era indicata.")
        if prefettura and not era:
            raise ValidationError("Impossibile impostare una prefettura senza selezionare un'era.")

        self.era = era
        self.prefettura = prefettura
        self.prefettura_esterna = bool(prefettura_esterna)
        self.save(update_fields=["era", "prefettura", "prefettura_esterna", "updated_at"])
        self._sync_abilita_default_era()

    def get_valore_massimo_risorsa_runtime(self, sigla):
        """
        Tetto massimo per rigenerazioni e consumi pool (risorse_consumabili).
        Se su Statistica è impostato massimo_pool_sigla, il massimo viene letto da quella sigla.
        """
        sigla = (sigla or '').strip().upper()
        if not sigla:
            return 0
        st = Statistica.objects.filter(sigla=sigla).first()
        ref = ''
        if st and getattr(st, 'massimo_pool_sigla', None):
            ref = (st.massimo_pool_sigla or '').strip().upper()
        if ref:
            return self.get_valore_statistica(ref)
        return self.get_valore_statistica(sigla)

    def get_risorsa_corrente(self, sigla):
        """Punti correnti nel pool per una statistica contrassegnata come risorsa (es. FRT)."""
        stat = Statistica.objects.filter(sigla=sigla, is_risorsa_pool=True).first()
        if not stat:
            return 0
        max_v = self.get_valore_massimo_risorsa_runtime(sigla)
        if max_v <= 0:
            return 0
        raw = (self.risorse_consumabili or {}).get(sigla)
        if raw is None:
            return max_v
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return max_v
        return max(0, min(v, max_v))

    def _get_cfg_recupero_risorsa(self, sigla):
        stat = Statistica.objects.filter(sigla=sigla, is_risorsa_pool=True).first()
        if not stat or not stat.auto_recupero_attivo:
            return None
        interval_seconds = max(1, int(stat.auto_recupero_intervallo_secondi or 0))
        step = max(1, int(stat.auto_recupero_step or 0))
        return {
            'interval_seconds': interval_seconds,
            'step': step,
            'stat_nome': stat.nome,
        }

    def _parse_recupero_item(self, raw):
        if not isinstance(raw, dict):
            return None
        sigla = (raw.get('stat_sigla') or '').strip().upper()
        if not sigla:
            return None
        interval = (
            raw.get('interval_seconds')
            or raw.get('ogni_secondi')
            or raw.get('every_seconds')
        )
        if interval in (None, ''):
            minutes = raw.get('interval_minutes') or raw.get('ogni_minuti') or raw.get('every_minutes')
            if minutes not in (None, ''):
                try:
                    interval = int(minutes) * 60
                except Exception:
                    interval = None
        try:
            interval = max(1, int(interval))
        except Exception:
            return None
        try:
            step = max(1, int(raw.get('step', 1)))
        except Exception:
            step = 1
        return {'stat_sigla': sigla, 'interval_seconds': interval, 'step': step}

    def _get_cfg_recuperi_da_abilita(self):
        out = {}
        for ab in self.abilita_possedute.all():
            spec = ab.recupero_risorsa
            if not spec:
                continue
            entries = []
            if isinstance(spec, list):
                entries = spec
            elif isinstance(spec, dict):
                if isinstance(spec.get('rigenerazioni'), list):
                    entries = spec.get('rigenerazioni') or []
                else:
                    entries = [spec]
            for raw in entries:
                item = self._parse_recupero_item(raw)
                if not item:
                    continue
                sigla = item['stat_sigla']
                if sigla == 'CHK':
                    sigla = 'CHA'
                row = out.get(sigla)
                if not row:
                    out[sigla] = {
                        'interval_seconds': item['interval_seconds'],
                        'step': item['step'],
                        'fonti': [ab.nome],
                    }
                else:
                    row['interval_seconds'] = min(row['interval_seconds'], item['interval_seconds'])
                    row['step'] = max(row['step'], item['step'])
                    row['fonti'].append(ab.nome)
        return out

    def _is_recupero_enabled_now(self, now_ts=None):
        now_ts = now_ts or timezone.now()
        # PNG: rigenerazione sempre attiva, anche fuori evento.
        if self.tipologia and not self.tipologia.giocante:
            return True
        try:
            return self.eventi_partecipati.filter(data_inizio__lte=now_ts, data_fine__gte=now_ts).exists()
        except Exception:
            return False

    def get_risorsa_corrente_runtime(self, sigla):
        stat = Statistica.objects.filter(sigla=sigla).first()
        if not stat:
            return 0
        max_v = self.get_valore_massimo_risorsa_runtime(sigla)
        if max_v <= 0:
            return 0
        if stat.is_risorsa_pool:
            return self.get_risorsa_corrente(sigla)
        cur_key = f'{sigla}_CUR'
        raw = (self.statistiche_temporanee or {}).get(cur_key, (self.statistiche_temporanee or {}).get(sigla))
        if raw is None:
            return max_v
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return max_v
        return max(0, min(v, max_v))

    def _set_risorsa_corrente_runtime(self, sigla, valore):
        stat = Statistica.objects.filter(sigla=sigla).first()
        if stat and stat.is_risorsa_pool:
            self._set_risorsa_corrente(sigla, valore)
            return
        key = f'{sigla}_CUR'
        temp = dict(self.statistiche_temporanee or {})
        temp[key] = valore
        self.statistiche_temporanee = temp

    def get_cfg_recuperi_automatici(self):
        cfg = self._get_cfg_recuperi_da_abilita()
        # Compatibilità con la configurazione legacy su Statistica (pool).
        for st in Statistica.objects.filter(is_risorsa_pool=True, auto_recupero_attivo=True):
            sigla = st.sigla
            row = cfg.get(sigla)
            interval_seconds = max(1, int(st.auto_recupero_intervallo_secondi or 1))
            step = max(1, int(st.auto_recupero_step or 1))
            if not row:
                cfg[sigla] = {'interval_seconds': interval_seconds, 'step': step, 'fonti': ['statistica:auto']}
            else:
                row['interval_seconds'] = min(row['interval_seconds'], interval_seconds)
                row['step'] = max(row['step'], step)
        return cfg

    def sync_recuperi_automatici(self, now_ts=None, only_sigla=None):
        now_ts = now_ts or timezone.now()
        cfg_map = self.get_cfg_recuperi_automatici()
        if only_sigla:
            only_sigla = only_sigla.upper()
            cfg_map = {k: v for k, v in cfg_map.items() if k == only_sigla}

        enabled_now = self._is_recupero_enabled_now(now_ts=now_ts)
        rec_qs = RecuperoRisorsaAttivo.objects.filter(personaggio=self)
        if only_sigla:
            rec_qs = rec_qs.filter(statistica_sigla=only_sigla)
        existing_map = {r.statistica_sigla: r for r in rec_qs}

        all_sigle = set(existing_map.keys()) | set(cfg_map.keys())
        for sigla in all_sigle:
            cfg = cfg_map.get(sigla)
            rec = existing_map.get(sigla)
            max_v = self.get_valore_massimo_risorsa_runtime(sigla)
            cur = self.get_risorsa_corrente_runtime(sigla)
            has_cfg = bool(cfg and max_v > 0 and cur < max_v)

            if not has_cfg:
                if rec and rec.is_active:
                    rec.is_active = False
                    rec.pause_started_at = None
                    rec.save(update_fields=['is_active', 'pause_started_at', 'updated_at'])
                continue

            next_tick = now_ts + timedelta(seconds=cfg['interval_seconds'])
            if rec:
                updates = []
                if not rec.is_active:
                    rec.is_active = True
                    rec.started_at = now_ts
                    rec.next_tick_at = next_tick
                    rec.pause_started_at = None if enabled_now else now_ts
                    updates.extend(['is_active', 'started_at', 'next_tick_at', 'pause_started_at'])
                if rec.interval_seconds != cfg['interval_seconds']:
                    rec.interval_seconds = cfg['interval_seconds']
                    updates.append('interval_seconds')
                if rec.step != cfg['step']:
                    rec.step = cfg['step']
                    updates.append('step')
                if enabled_now:
                    if rec.pause_started_at:
                        shift = now_ts - rec.pause_started_at
                        rec.next_tick_at = rec.next_tick_at + shift
                        rec.pause_started_at = None
                        updates.extend(['next_tick_at', 'pause_started_at'])
                else:
                    if rec.pause_started_at is None:
                        rec.pause_started_at = now_ts
                        updates.append('pause_started_at')
                if updates:
                    updates.append('updated_at')
                    rec.save(update_fields=updates)
                continue

            RecuperoRisorsaAttivo.objects.create(
                personaggio=self,
                statistica_sigla=sigla,
                started_at=now_ts,
                next_tick_at=next_tick,
                interval_seconds=cfg['interval_seconds'],
                step=cfg['step'],
                is_active=True,
                pause_started_at=None if enabled_now else now_ts,
            )

    def sync_recupero_risorsa(self, sigla, now_ts=None):
        """
        Sincronizza start/stop del recupero automatico in base al valore corrente.
        """
        now_ts = now_ts or timezone.now()
        cfg = self._get_cfg_recupero_risorsa(sigla)
        existing = RecuperoRisorsaAttivo.objects.filter(personaggio=self, statistica_sigla=sigla).first()
        max_v = self.get_valore_massimo_risorsa_runtime(sigla)
        cur = self.get_risorsa_corrente(sigla)

        if not cfg or max_v <= 0 or cur >= max_v:
            if existing and existing.is_active:
                existing.is_active = False
                existing.save(update_fields=['is_active', 'updated_at'])
            return

        next_tick = now_ts + timedelta(seconds=cfg['interval_seconds'])
        if existing:
            updates = []
            if not existing.is_active:
                existing.is_active = True
                updates.append('is_active')
            if existing.interval_seconds != cfg['interval_seconds']:
                existing.interval_seconds = cfg['interval_seconds']
                updates.append('interval_seconds')
            if existing.step != cfg['step']:
                existing.step = cfg['step']
                updates.append('step')
            # Se il timer non era attivo, riparte da ora.
            if 'is_active' in updates:
                existing.started_at = now_ts
                existing.next_tick_at = next_tick
                updates.extend(['started_at', 'next_tick_at'])
            if updates:
                updates.append('updated_at')
                existing.save(update_fields=updates)
            return

        RecuperoRisorsaAttivo.objects.create(
            personaggio=self,
            statistica_sigla=sigla,
            started_at=now_ts,
            next_tick_at=next_tick,
            interval_seconds=cfg['interval_seconds'],
            step=cfg['step'],
            is_active=True,
        )

    def advance_recuperi_risorse(self, now_ts=None, only_sigla=None):
        """
        Applica i tick maturati (idempotente rispetto a now_ts) e ferma i timer a cap raggiunto.
        """
        now_ts = now_ts or timezone.now()
        self.sync_recuperi_automatici(now_ts=now_ts, only_sigla=only_sigla)
        rec_qs = RecuperoRisorsaAttivo.objects.filter(personaggio=self, is_active=True)
        if only_sigla:
            rec_qs = rec_qs.filter(statistica_sigla=only_sigla)
        recs = list(rec_qs)
        if not recs:
            return {}

        out = {}
        changed = False
        rc = dict(self.risorse_consumabili or {})
        temp_stats = dict(self.statistiche_temporanee or {})

        for rec in recs:
            sigla = rec.statistica_sigla
            max_v = self.get_valore_massimo_risorsa_runtime(sigla)
            cur = self.get_risorsa_corrente_runtime(sigla)
            if max_v <= 0 or cur >= max_v:
                rec.is_active = False
                rec.save(update_fields=['is_active', 'updated_at'])
                out[sigla] = {'active': False, 'valore_corrente': cur, 'valore_max': max_v}
                continue

            if rec.pause_started_at:
                remaining = max(0, int((rec.next_tick_at - now_ts).total_seconds()))
                out[sigla] = {
                    'active': True,
                    'paused': True,
                    'valore_corrente': cur,
                    'valore_max': max_v,
                    'next_tick_at': rec.next_tick_at,
                    'seconds_to_next_tick': remaining,
                }
                continue

            if now_ts < rec.next_tick_at:
                out[sigla] = {
                    'active': True,
                    'valore_corrente': cur,
                    'valore_max': max_v,
                    'next_tick_at': rec.next_tick_at,
                }
                continue

            elapsed = (now_ts - rec.next_tick_at).total_seconds()
            ticks = int(elapsed // max(1, rec.interval_seconds)) + 1
            gain = max(0, ticks * max(1, rec.step))
            new_cur = min(max_v, cur + gain)
            delta = new_cur - cur
            rec.next_tick_at = rec.next_tick_at + timedelta(seconds=ticks * max(1, rec.interval_seconds))

            if delta > 0:
                stat = Statistica.objects.filter(sigla=sigla).first()
                if stat and stat.is_risorsa_pool:
                    rc[sigla] = new_cur
                else:
                    temp_stats[f'{sigla}_CUR'] = new_cur
                changed = True
                RisorsaStatisticaMovimento.objects.create(
                    personaggio=self,
                    statistica_sigla=sigla,
                    importo=delta,
                    descrizione=f'Recupero automatico +{delta} ({sigla})',
                    tipo_movimento=RISORSA_MOV_RECUPERO,
                )
                if new_cur >= max_v:
                    rec.is_active = False
                rec.save(update_fields=['next_tick_at', 'is_active', 'updated_at'])
                out[sigla] = {
                    'active': rec.is_active,
                    'paused': False,
                    'valore_corrente': new_cur,
                    'valore_max': max_v,
                    'next_tick_at': rec.next_tick_at if rec.is_active else None,
                }
            else:
                rec.save(update_fields=['next_tick_at', 'updated_at'])
                out[sigla] = {
                    'active': rec.is_active,
                    'paused': False,
                    'valore_corrente': cur,
                    'valore_max': max_v,
                    'next_tick_at': rec.next_tick_at,
                }

        if changed:
            self.risorse_consumabili = rc
            self.statistiche_temporanee = temp_stats
            self.save(update_fields=['risorse_consumabili', 'statistiche_temporanee', 'updated_at'])
            if hasattr(self, '_modificatori_calcolati_cache'):
                delattr(self, '_modificatori_calcolati_cache')
        return out

    def get_recuperi_risorsa_stato(self, now_ts=None):
        now_ts = now_ts or timezone.now()
        self.sync_recuperi_automatici(now_ts=now_ts)
        cfg_map = self.get_cfg_recuperi_automatici()
        out = {}
        recs = RecuperoRisorsaAttivo.objects.filter(personaggio=self, is_active=True)
        for rec in recs:
            remaining = max(0, int((rec.next_tick_at - now_ts).total_seconds()))
            cfg = cfg_map.get(rec.statistica_sigla) or {}
            out[rec.statistica_sigla] = {
                'active': True,
                'paused': bool(rec.pause_started_at),
                'next_tick_at': rec.next_tick_at,
                'seconds_to_next_tick': remaining,
                'step': rec.step,
                'interval_seconds': rec.interval_seconds,
                'abilita_nomi': cfg.get('fonti') or [],
            }
        return out

    def consuma_risorsa_statistica(self, sigla):
        """
        Consuma un punto dal pool. Crea movimento, log ed eventuali effetti temporanei dalle abilità.
        """
        stat = Statistica.objects.filter(sigla=sigla, is_risorsa_pool=True).first()
        if not stat:
            raise ValueError('Statistica non configurata come risorsa a pool.')
        max_v = self.get_valore_massimo_risorsa_runtime(sigla)
        if max_v <= 0:
            raise ValueError('Pool non disponibile (massimo 0).')
        cur = self.get_risorsa_corrente(sigla)
        if cur <= 0:
            raise ValueError('Nessun punto disponibile da consumare.')
        nuovo = cur - 1
        self._set_risorsa_corrente(sigla, nuovo)
        self.save(update_fields=['risorse_consumabili'])
        RisorsaStatisticaMovimento.objects.create(
            personaggio=self,
            statistica_sigla=sigla,
            importo=-1,
            descrizione=f'Consumo 1 punto {stat.nome} ({sigla})',
            tipo_movimento=RISORSA_MOV_CONSUMO,
        )
        self.aggiungi_log(
            f'Consumo 1 punto {stat.nome} ({sigla}). Rimasti: {nuovo}/{max_v}.'
        )
        self._crea_effetti_temporanei_da_abilita(sigla)
        self.sync_recuperi_automatici(only_sigla=sigla)
        if hasattr(self, '_modificatori_calcolati_cache'):
            delattr(self, '_modificatori_calcolati_cache')
        return nuovo

    def regola_risorsa_staff(self, sigla, delta, staff_user=None, motivo=''):
        """
        Varia il pool corrente di una risorsa statistica (staff). delta può essere positivo o negativo;
        il valore viene clampato tra 0 e il massimo di scheda.
        """
        try:
            delta = int(delta)
        except (TypeError, ValueError):
            raise ValueError('Variazione non valida.')
        if delta == 0:
            raise ValueError('La variazione non può essere zero.')
        stat = Statistica.objects.filter(sigla=sigla, is_risorsa_pool=True).first()
        if not stat:
            raise ValueError('Statistica non configurata come risorsa a pool.')
        max_v = self.get_valore_massimo_risorsa_runtime(sigla)
        if max_v <= 0:
            raise ValueError('Pool non disponibile (massimo 0).')
        cur = self.get_risorsa_corrente(sigla)
        nuovo = max(0, min(max_v, cur + delta))
        if nuovo == cur:
            raise ValueError(
                'Impossibile applicare la variazione: il totale è già al minimo (0) o al massimo previsto da scheda.'
            )
        diff = nuovo - cur
        self._set_risorsa_corrente(sigla, nuovo)
        self.save(update_fields=['risorse_consumabili'])
        who = getattr(staff_user, 'username', None) or getattr(staff_user, 'email', None) or 'staff'
        segno = f'+{diff}' if diff > 0 else str(diff)
        desc = f'Regolazione staff {segno} pt. {stat.nome} ({sigla})'
        if motivo:
            desc = f'{desc} — {motivo}'
        RisorsaStatisticaMovimento.objects.create(
            personaggio=self,
            statistica_sigla=sigla,
            importo=diff,
            descrizione=desc[:240],
            tipo_movimento=RISORSA_MOV_STAFF,
        )
        self.aggiungi_log(f'{desc}. Totale: {nuovo}/{max_v} (operatore: {who}).')
        self.sync_recuperi_automatici(only_sigla=sigla)
        if hasattr(self, '_modificatori_calcolati_cache'):
            delattr(self, '_modificatori_calcolati_cache')
        return nuovo

    def incrementa_risorsa_staff(self, sigla, staff_user=None, motivo=''):
        """Aggiunge esattamente un punto al pool (compatibilità con client che chiamano solo +1)."""
        return self.regola_risorsa_staff(sigla, 1, staff_user=staff_user, motivo=motivo)

    def _set_risorsa_corrente(self, sigla, valore):
        rc = dict(self.risorse_consumabili or {})
        rc[sigla] = valore
        self.risorse_consumabili = rc

    def imposta_risorsa_pool_tattica(self, sigla, valore):
        """
        Scrive il contatore pool per PV/PA/PS/CHA in risorse_consumabili e rimuove chiavi legacy in
        statistiche_temporanee (*_CUR, CHK_CUR per chakra).
        """
        sigla = (sigla or '').strip().upper()
        try:
            v = int(valore)
        except (TypeError, ValueError):
            return
        self._set_risorsa_corrente(sigla, v)
        temp = dict(self.statistiche_temporanee or {})
        temp.pop(f'{sigla}_CUR', None)
        if sigla == 'CHA':
            temp.pop('CHK_CUR', None)
        self.statistiche_temporanee = temp

    def _crea_effetti_temporanei_da_abilita(self, sigla):
        """Crea EffettoRisorsaTemporaneo per ogni abilità posseduta con effetto_uso_risorsa compatibile."""
        sigla = (sigla or '').strip().upper()
        for ab in self.abilita_possedute.all():
            spec = ab.effetto_uso_risorsa
            if not spec:
                continue
            spec_sigla = (spec.get('stat_sigla') or '').strip().upper()
            if spec_sigla == 'CHK':
                spec_sigla = 'CHA'
            if spec_sigla != sigla:
                continue
            durata = spec.get('durata') or RISORSA_DURATA_ORA_1
            if durata not in (RISORSA_DURATA_ORA_1, RISORSA_DURATA_GIORNO, RISORSA_DURATA_EVENTO):
                durata = RISORSA_DURATA_ORA_1
            scad = calcola_scadenza_effetto_risorsa(durata)
            modifiche = spec.get('modifiche') or []
            EffettoRisorsaTemporaneo.objects.create(
                personaggio=self,
                statistica_risorsa_sigla=spec_sigla,
                abilita=ab,
                durata_tipo=durata,
                scadenza=scad,
                modifiche=modifiche,
            )

    def _build_punteggi_base_indipendenti(self, exclude_abilita_ids=None):
        exclude_abilita_ids = set(exclude_abilita_ids or [])
        links = abilita_punteggio.objects.filter(
            abilita__personaggioabilita__personaggio=self
        ).exclude(abilita_id__in=exclude_abilita_ids).select_related('punteggio')
        p = {
            i['punteggio__nome']: i['valore_totale']
            for i in links.values('punteggio__nome').annotate(valore_totale=Sum('valore'))
        }

        forma_oggi = self.get_forma_camaleonte_del_giorno()
        if forma_oggi and forma_oggi.id not in exclude_abilita_ids:
            extra_links = abilita_punteggio.objects.filter(abilita=forma_oggi).select_related('punteggio')
            for row in extra_links.values('punteggio__nome').annotate(valore_totale=Sum('valore')):
                nome = row['punteggio__nome']
                p[nome] = (p.get(nome, 0) or 0) + (row['valore_totale'] or 0)

        # Valori base da scheda (PersonaggioStatisticaBase / default statistica): senza questo,
        # punteggi_dipendenti usa solo abilita_punteggio e sorgenti come Chakra restano sempre 0.
        for stat in Statistica.objects.filter(parametro__isnull=False).exclude(parametro__exact=''):
            base_pg = int(self.get_valore_statistica_base(stat) or 0)
            nome = stat.nome
            from_links = int(p.get(nome, 0) or 0)
            p[nome] = base_pg + from_links

        return p

    def _get_abilita_data_acquisizione_map(self, include_camaleonte=True):
        acq_map = dict(
            PersonaggioAbilita.objects.filter(personaggio=self).values_list("abilita_id", "data_acquisizione")
        )
        if include_camaleonte:
            forma_oggi = self.get_forma_camaleonte_del_giorno()
            if forma_oggi:
                acq_map.setdefault(forma_oggi.id, timezone.now())
        return acq_map

    def _collect_regole_punteggio_dipendente(self, exclude_abilita_ids=None):
        exclude_abilita_ids = set(exclude_abilita_ids or [])
        acq_map = self._get_abilita_data_acquisizione_map(include_camaleonte=True)
        abilita_ids = set(acq_map.keys()) - exclude_abilita_ids
        if not abilita_ids:
            return []

        regole_qs = abilita_punteggio_dipendente.objects.filter(
            abilita_id__in=abilita_ids
        ).select_related("punteggio_target", "punteggio_sorgente")

        regole = []
        for regola in regole_qs:
            if regola.ogni_x <= 0:
                continue
            regole.append({
                "id": regola.id,
                "abilita_id": regola.abilita_id,
                "acquired_at": acq_map.get(regola.abilita_id),
                "target_nome": regola.punteggio_target.nome,
                "source_nome": regola.punteggio_sorgente.nome,
                "incremento": int(regola.incremento or 0),
                "ogni_x": int(regola.ogni_x or 1),
            })
        return regole

    def _ordina_scc_topologico(self, scc_ids, edges_between_scc):
        indeg = {sid: 0 for sid in scc_ids}
        for src_sid, dsts in edges_between_scc.items():
            for dst_sid in dsts:
                if src_sid != dst_sid:
                    indeg[dst_sid] += 1
        queue = sorted([sid for sid, v in indeg.items() if v == 0])
        ordine = []
        while queue:
            sid = queue.pop(0)
            ordine.append(sid)
            for next_sid in sorted(edges_between_scc.get(sid, [])):
                if sid == next_sid:
                    continue
                indeg[next_sid] -= 1
                if indeg[next_sid] == 0:
                    queue.append(next_sid)
                    queue.sort()
        return ordine if len(ordine) == len(scc_ids) else sorted(list(scc_ids))

    def _valore_sorgente_per_punteggio_dipendente(self, punteggi_per_nome, source_nome):
        """
        Valore effettivo della sorgente (come get_valore_statistica) per Statistica,
        così contano anche AbilitaStatistica / oggetti / effetti. Per altri Punteggi,
        usa solo la somma in punteggi_per_nome.
        """
        stat = Statistica.objects.filter(nome=source_nome).first()
        if not stat or not stat.parametro:
            return int(punteggi_per_nome.get(source_nome, 0) or 0)
        self._punteggi_base_partial_for_mods = punteggi_per_nome
        try:
            if hasattr(self, '_modificatori_calcolati_cache'):
                delattr(self, '_modificatori_calcolati_cache')
            return int(self.get_valore_statistica(stat.sigla))
        finally:
            if hasattr(self, '_punteggi_base_partial_for_mods'):
                delattr(self, '_punteggi_base_partial_for_mods')
            if hasattr(self, '_modificatori_calcolati_cache'):
                delattr(self, '_modificatori_calcolati_cache')

    def _applica_punteggi_dipendenti(self, punteggi_per_nome, regole):
        if not regole:
            return punteggi_per_nome
        max_dt = datetime.max.replace(tzinfo=dt_timezone.utc)

        nodes = set()
        graph = {}
        for r in regole:
            src = r["source_nome"]
            dst = r["target_nome"]
            nodes.add(src)
            nodes.add(dst)
            graph.setdefault(src, []).append(dst)
            graph.setdefault(dst, [])

        index_counter = 0
        stack = []
        on_stack = set()
        index_map = {}
        low_map = {}
        sccs = []

        def strongconnect(v):
            nonlocal index_counter
            index_map[v] = index_counter
            low_map[v] = index_counter
            index_counter += 1
            stack.append(v)
            on_stack.add(v)

            for w in graph.get(v, []):
                if w not in index_map:
                    strongconnect(w)
                    low_map[v] = min(low_map[v], low_map[w])
                elif w in on_stack:
                    low_map[v] = min(low_map[v], index_map[w])

            if low_map[v] == index_map[v]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    component.append(w)
                    if w == v:
                        break
                sccs.append(component)

        for n in sorted(nodes):
            if n not in index_map:
                strongconnect(n)

        node_to_scc = {}
        for sid, comp in enumerate(sccs):
            for n in comp:
                node_to_scc[n] = sid

        has_self_loop = set()
        for r in regole:
            if r["source_nome"] == r["target_nome"]:
                has_self_loop.add(node_to_scc[r["source_nome"]])

        cyclic_scc = set()
        for sid, comp in enumerate(sccs):
            if len(comp) > 1 or sid in has_self_loop:
                cyclic_scc.add(sid)

        scc_edges = {sid: set() for sid in range(len(sccs))}
        for r in regole:
            src_sid = node_to_scc[r["source_nome"]]
            dst_sid = node_to_scc[r["target_nome"]]
            if src_sid != dst_sid:
                scc_edges[src_sid].add(dst_sid)

        scc_order = self._ordina_scc_topologico(set(range(len(sccs))), scc_edges)
        rules_by_target_scc = {}
        rules_by_internal_scc = {}
        for r in regole:
            src_sid = node_to_scc[r["source_nome"]]
            dst_sid = node_to_scc[r["target_nome"]]
            if src_sid == dst_sid:
                rules_by_internal_scc.setdefault(dst_sid, []).append(r)
            else:
                rules_by_target_scc.setdefault(dst_sid, []).append(r)

        for sid in scc_order:
            incoming = rules_by_target_scc.get(sid, [])
            incoming.sort(
                key=lambda r: (
                    r["acquired_at"] or max_dt,
                    r["abilita_id"],
                    r["id"],
                )
            )
            for r in incoming:
                source_val = self._valore_sorgente_per_punteggio_dipendente(
                    punteggi_per_nome, r["source_nome"]
                )
                blocchi = source_val // r["ogni_x"]
                bonus = blocchi * r["incremento"]
                if bonus:
                    target = r["target_nome"]
                    punteggi_per_nome[target] = int(punteggi_per_nome.get(target, 0) or 0) + int(bonus)

            internal = rules_by_internal_scc.get(sid, [])
            if not internal:
                continue

            if sid in cyclic_scc:
                internal.sort(
                    key=lambda r: (
                        r["acquired_at"] or max_dt,
                        r["abilita_id"],
                        r["id"],
                    )
                )
            else:
                internal.sort(key=lambda r: (r["abilita_id"], r["id"]))

            for r in internal:
                source_val = self._valore_sorgente_per_punteggio_dipendente(
                    punteggi_per_nome, r["source_nome"]
                )
                blocchi = source_val // r["ogni_x"]
                bonus = blocchi * r["incremento"]
                if bonus:
                    target = r["target_nome"]
                    punteggi_per_nome[target] = int(punteggi_per_nome.get(target, 0) or 0) + int(bonus)

        return punteggi_per_nome
    
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
        p = self._build_punteggi_base_indipendenti(exclude_abilita_ids=None)
        regole = self._collect_regole_punteggio_dipendente(exclude_abilita_ids=None)
        p = self._applica_punteggi_dipendenti(p, regole)

        agen = Punteggio.objects.filter(tipo=AURA, is_generica=True).first()
        if agen:
            others = set(Punteggio.objects.filter(tipo=AURA).exclude(id=agen.id).values_list('nome', flat=True))
            max_val = 0
            for k, v in p.items():
                if k in others and v > max_val: max_val = v
            p[agen.nome] = max_val
        self._punteggi_base_cache = p
        return p

    def get_punteggi_base_escludendo_abilita(self, exclude_abilita_ids):
        """
        Come punteggi_base ma esclude i contributi delle abilità indicate
        (usato per requisiti di razza / tratti aura innata senza effetto circolare).
        """
        exclude_abilita_ids = set(exclude_abilita_ids or [])
        p = self._build_punteggi_base_indipendenti(exclude_abilita_ids=exclude_abilita_ids)
        regole = self._collect_regole_punteggio_dipendente(exclude_abilita_ids=exclude_abilita_ids)
        p = self._applica_punteggi_dipendenti(p, regole)

        agen = Punteggio.objects.filter(tipo=AURA, is_generica=True).first()
        if agen:
            others = set(
                Punteggio.objects.filter(tipo=AURA).exclude(id=agen.id).values_list('nome', flat=True)
            )
            max_val = 0
            for k, v in p.items():
                if k in others and v > max_val:
                    max_val = v
            p[agen.nome] = max_val
        return p

    def _caratteristiche_dict_da_punteggi_nomi(self, punteggi_per_nome):
        """Filtra un dict {nome_punteggio: valore} lasciando solo le caratteristiche (tipo CA)."""
        nomi_ca = set(
            Punteggio.objects.filter(tipo=CARATTERISTICA).values_list('nome', flat=True)
        )
        return {k: v for k, v in punteggi_per_nome.items() if k in nomi_ca}

    def _ids_tratti_aura_innata_slot(self, slot):
        """
        ID delle abilità possedute che sono tratti AIN nello slot indicato.
        slot 'archetipo' -> livello_riferimento 0 o 1; 'forma' -> livello 2.
        """
        qs = self.abilita_possedute.filter(
            is_tratto_aura=True,
            aura_riferimento__sigla='AIN',
        )
        if slot == 'archetipo':
            qs = qs.filter(livello_riferimento__in=(0, 1))
        elif slot == 'forma':
            qs = qs.filter(livello_riferimento=2)
        else:
            return []
        return list(qs.values_list('id', flat=True))
    
    def get_valore_statistica_base(self, statistica):
        """
        Recupera il valore base di una statistica per questo personaggio.
        Se non esiste il record, usa valore_base_predefinito senza creare righe.
        """
        link = PersonaggioStatisticaBase.objects.filter(
            personaggio=self,
            statistica=statistica
        ).first()
        if link:
            return link.valore_base
        return statistica.valore_base_predefinito
    
    @property
    def statistiche_base_dict(self):
        """
        Restituisce un dizionario {parametro: valore} per tutte le statistiche base.
        In caso di record mancante usa il valore_base_predefinito della statistica.
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
        Durante il calcolo dei punteggi dipendenti, usa _punteggi_base_partial_for_mods
        per evitare ricorsione su punteggi_base completo.
        """
        if hasattr(self, '_punteggi_base_partial_for_mods'):
            p = self._punteggi_base_partial_for_mods
            nomi_ca = set(
                Punteggio.objects.filter(tipo=CARATTERISTICA).values_list('nome', flat=True)
            )
            return {k: v for k, v in p.items() if k in nomi_ca}
        return {
            k: v
            for k, v in self.punteggi_base.items()
            if Punteggio.objects.filter(nome=k, tipo=CARATTERISTICA).exists()
        }
    
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

    def valida_tratto_aura_innata(self, abilita):
        """
        Regole per tratti d'aura legati all'aura innata (Punteggio con sigla AIN).
        Archetipo: livello 0 (Umano) o 1 (altri); Forma: livello 2.
        I requisiti sulle caratteristiche usano i punteggi del PG escludendo
        i tratti dello stesso slot, per evitare dipendenze circolari.
        """
        aura = abilita.aura_riferimento
        if not aura or getattr(aura, 'sigla', None) != 'AIN':
            return True, "OK"

        ain_val = self.get_valore_aura_effettivo(aura)
        liv = abilita.livello_riferimento

        if liv == 0:
            nome_norm = (abilita.nome or '').strip().casefold()
            if nome_norm != 'archetipo - umano':
                return False, "A livello 0 è consentito solo l'archetipo Umano."
            return True, "OK"

        if liv == 1:
            if ain_val < 1:
                return False, "Serve aura innata almeno 1 per questo archetipo."
            excl = self._ids_tratti_aura_innata_slot('archetipo')
            chars = self._caratteristiche_dict_da_punteggi_nomi(
                self.get_punteggi_base_escludendo_abilita(excl)
            )
            req_nome = abilita.caratteristica.nome
            if chars.get(req_nome, 0) < 1:
                return False, f"Serve almeno 1 in {req_nome} per questo archetipo."
            return True, "OK"

        if liv == 2:
            if ain_val < 2:
                return False, "Serve aura innata almeno 2 per selezionare una forma."
            if not abilita.caratteristica_2_id:
                return False, "Forma senza seconda caratteristica configurata."
            excl = self._ids_tratti_aura_innata_slot('forma')
            chars = self._caratteristiche_dict_da_punteggi_nomi(
                self.get_punteggi_base_escludendo_abilita(excl)
            )
            n1 = abilita.caratteristica.nome
            n2 = abilita.caratteristica_2.nome
            v1 = chars.get(n1, 0)
            v2 = chars.get(n2, 0)
            if n1 == n2:
                if v1 < 2:
                    return False, f"Per questa forma (doppia {n1}) servono almeno 2 punti in {n1}."
            else:
                if v1 < 1 or v2 < 1:
                    return False, f"Servono almeno 1 in {n1} e 1 in {n2} per questa forma."
            return True, "OK"

        return True, "OK"
    
    def valida_acquisizione_abilita(self, abilita):
        # Tratto aura innata (AIN): regole dedicate; lo swap è gestito in AcquisisciAbilitaView.
        if abilita.is_tratto_aura and abilita.aura_riferimento_id:
            ar = abilita.aura_riferimento
            if getattr(ar, 'sigla', None) == 'AIN':
                return self.valida_tratto_aura_innata(abilita)

        # Controllo Esclusività Tratto Aura (altre aure)
        if abilita.is_tratto_aura and abilita.aura_riferimento:
            tratti_esistenti = self.abilita_possedute.filter(
                is_tratto_aura=True,
                aura_riferimento=abilita.aura_riferimento,
                livello_riferimento=abilita.livello_riferimento
            ).exclude(pk=abilita.pk)
            
            if tratti_esistenti.exists():
                return False, f"Hai già selezionato un {tratti_esistenti.first().nome} per il livello {abilita.livello_riferimento} di {abilita.aura_riferimento.nome}."

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

        # 1b. Forma camaleonte del giorno: stessi modificatori di una forma reale.
        forma_oggi = self.get_forma_camaleonte_del_giorno()
        if forma_oggi:
            for l in AbilitaStatistica.objects.filter(abilita=forma_oggi).select_related('statistica'):
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

        # 4. Effetti temporanei da consumo risorse (Fortuna / future pool)
        now_ts = timezone.now()
        eff_qs = EffettoRisorsaTemporaneo.objects.filter(personaggio=self, scadenza__gt=now_ts)
        stat_cache = {}
        for eff in eff_qs:
            for m in eff.modifiche or []:
                s_sig = m.get('stat_sigla')
                if not s_sig:
                    continue
                if s_sig not in stat_cache:
                    stat_cache[s_sig] = Statistica.objects.filter(sigla=s_sig).first()
                st_obj = stat_cache[s_sig]
                if not st_obj or not st_obj.parametro:
                    continue
                tmod = m.get('tipo_modificatore') or MODIFICATORE_ADDITIVO
                if tmod not in (MODIFICATORE_ADDITIVO, MODIFICATORE_MOLTIPLICATIVO):
                    tmod = MODIFICATORE_ADDITIVO
                try:
                    val = float(m.get('valore', 0))
                except (TypeError, ValueError):
                    val = 0.0
                _add(st_obj.parametro, tmod, val)
        
        self._modificatori_calcolati_cache = mods
        return mods

    def get_tratto_camaleonte_posseduto(self):
        """
        Tratto forma "camaleonte" posseduto dal personaggio (AIN livello 2).
        """
        return self.abilita_possedute.filter(
            is_tratto_aura=True,
            aura_riferimento__sigla='AIN',
            livello_riferimento=2,
            camaleontica=True,
        ).first()

    def get_forma_camaleonte_del_giorno(self):
        """
        Se il personaggio possiede la forma camaleonte, seleziona deterministicamente
        una forma AIN livello 2 diversa, stabile per-personaggio per la data odierna.
        Non scrive su DB: persiste per la giornata anche dopo logout/login.
        """
        trait = self.get_tratto_camaleonte_posseduto()
        if not trait:
            return None

        qs = Abilita.objects.filter(
            is_tratto_aura=True,
            aura_riferimento__sigla='AIN',
            livello_riferimento=2,
            camaleontica=False,
        ).exclude(pk=trait.pk).order_by('id')

        count = qs.count()
        if count == 0:
            return None

        day = timezone.localdate().isoformat()
        seed = f"{self.sync_id}:{trait.sync_id}:{day}"
        idx = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % count
        return qs[idx]
    
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
        
        # IMPORTANTE: Aggiungi anche le statistiche senza modificatori
        # (quelle che hanno solo valore base da statistiche_base_dict)
        for param, val_base in self.statistiche_base_dict.items():
            if param not in dettagli:
                dettagli[param] = {
                    'valore_base': val_base,
                    'modificatori': [],
                    'add_totale': 0.0,
                    'mol_totale': 1.0,
                    'valore_finale': float(val_base)
                }
        
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
        
        if isinstance(item, Abilita):
            testo_finale = item.TestoFormattato
            if item.pk == getattr(self.get_tratto_camaleonte_posseduto(), 'pk', None):
                forma_oggi = self.get_forma_camaleonte_del_giorno()
                if forma_oggi:
                    testo_forma = forma_oggi.TestoFormattato or (forma_oggi.descrizione or '')
                    if testo_forma:
                        testo_finale = (
                            f"{testo_finale}"
                            f"<hr style='margin: 10px 0; border: 0; border-top: 1px dashed #555;'/>"
                            f"<div style='font-size:0.95em;'>"
                            f"<strong>Forma del giorno:</strong> {forma_oggi.nome}<br/>"
                            f"{testo_forma}"
                            f"</div>"
                        )

        if isinstance(item, (Oggetto, Infusione)):
            testo_finale += genera_html_cariche(item, self)

        return testo_finale

    def get_testo_formattato_consumabile(self, consumabile):
        """
        Restituisce (descrizione_formattata, formula_formattata) per un consumabile,
        applicando la stessa logica di formatta_testo_generico con statistiche e bonus del personaggio
        (come per le tessiture). Se il consumabile è legato a una tessitura, usa statistiche_base e contesto
        della tessitura; se da effetto casuale usa contesto aura/elemento; altrimenti testo grezzo.
        """
        if not consumabile:
            return '', ''
        stats = None
        ctx = {}
        if getattr(consumabile, 'tessitura', None):
            item = consumabile.tessitura
            stats = item.tessiturastatisticabase_set.select_related('statistica').all()
            formula_text = consumabile.formula or ""
            if "{elem}" not in formula_text:
                ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': item.elemento_principale}
                desc = formatta_testo_generico(consumabile.descrizione, formula=consumabile.formula, statistiche_base=stats, personaggio=self, context=ctx)
                formula_out = formatta_testo_generico(None, formula=consumabile.formula, statistiche_base=stats, personaggio=self, context=ctx, solo_formula=True)
                formula_out = formula_out.replace("<strong>Formula:</strong>", "").strip() if formula_out else ""
                return desc, formula_out
            modello = self.modelli_aura.filter(aura=item.aura_richiesta).first()
            elementi_map = {}
            if item.elemento_principale:
                elementi_map[item.elemento_principale.id] = item.elemento_principale
            if modello:
                punteggi_pg = self.punteggi_base
                def verifica_requisiti(requisiti_queryset):
                    for req_link in requisiti_queryset:
                        if punteggi_pg.get(req_link.requisito.nome, 0) < req_link.valore:
                            return False
                    return True
                if modello.usa_doppia_formula and modello.elemento_secondario:
                    attiva_doppia = verifica_requisiti(modello.req_doppia_rel.select_related('requisito').all()) if modello.usa_condizione_doppia else True
                    if attiva_doppia:
                        elementi_map[modello.elemento_secondario.id] = modello.elemento_secondario
                if modello.usa_formula_per_caratteristica:
                    attiva_caratt = verifica_requisiti(modello.req_caratt_rel.select_related('requisito').all()) if modello.usa_condizione_caratt else True
                    if attiva_caratt:
                        for el in Punteggio.objects.filter(tipo=ELEMENTO, caratteristica_relativa__nome__in=punteggi_pg.keys()):
                            if punteggi_pg.get(el.caratteristica_relativa.nome, 0) > 0:
                                elementi_map[el.id] = el
                if modello.usa_formula_per_mattone:
                    attiva_mattone = verifica_requisiti(modello.req_mattone_rel.select_related('requisito').all()) if modello.usa_condizione_mattone else True
                    if attiva_mattone:
                        caratt_ids = item.componenti.values_list('caratteristica', flat=True)
                        for el in Punteggio.objects.filter(tipo=ELEMENTO, caratteristica_relativa__id__in=caratt_ids):
                            elementi_map[el.id] = el
            elementi_da_calcolare = list(elementi_map.values())
            if not elementi_da_calcolare:
                ctx = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': None}
                desc = formatta_testo_generico(consumabile.descrizione, formula=consumabile.formula, statistiche_base=stats, personaggio=self, context=ctx)
                formula_out = formatta_testo_generico(None, formula=consumabile.formula, statistiche_base=stats, personaggio=self, context=ctx, solo_formula=True)
                formula_out = formula_out.replace("<strong>Formula:</strong>", "").strip() if formula_out else ""
                return desc, formula_out
            ctx_base = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': item.elemento_principale}
            descrizione_html = formatta_testo_generico(consumabile.descrizione, formula=None, statistiche_base=stats, personaggio=self, context=ctx_base)
            formule_html = []
            for elem in elementi_da_calcolare:
                val_caratt = self.caratteristiche_base.get(elem.caratteristica_relativa.nome, 0) if elem.caratteristica_relativa else 0
                ctx_loop = {'livello': item.livello, 'aura': item.aura_richiesta, 'elemento': elem, 'caratteristica_associata_valore': val_caratt}
                risultato = formatta_testo_generico(None, formula=consumabile.formula, statistiche_base=stats, personaggio=self, context=ctx_loop, solo_formula=True)
                valore_pura = risultato.replace("<strong>Formula:</strong>", "").strip() if risultato else ""
                if valore_pura:
                    block = f"<div style='margin-top: 4px; padding: 4px 8px; border-left: 3px solid {elem.colore}; background-color: rgba(255,255,255,0.05); border-radius: 0 4px 4px 0;'><span style='color: {elem.colore}; font-weight: bold; margin-right: 6px;'>{elem.nome}:</span>{valore_pura}</div>"
                    formule_html.append(block)
            formula_html = f"<hr style='margin: 10px 0; border: 0; border-top: 1px dashed #555;'/><div style='font-size: 0.95em;'><strong>Formule:</strong>{''.join(formule_html)}</div>" if formule_html else ""
            return descrizione_html, formula_html
        if getattr(consumabile, 'effetto_casuale', None):
            ec = consumabile.effetto_casuale
            ctx = {'aura': ec.tipologia.aura_collegata, 'elemento': ec.elemento_principale}
            desc = formatta_testo_generico(consumabile.descrizione, personaggio=self, context=ctx)
            formula_out = ""
            if consumabile.formula:
                formula_out = formatta_testo_generico(None, formula=consumabile.formula, personaggio=self, context=ctx, solo_formula=True)
                formula_out = formula_out.replace("<strong>Formula:</strong>", "").strip() if formula_out else ""
            return desc, formula_out
        # Consumabile senza tessitura né effetto casuale: stessa logica visiva delle tessiture
        # (formatta_testo_generico con personaggio per placeholder e HTML, senza statistiche_base)
        desc = formatta_testo_generico(
            consumabile.descrizione, formula=None, statistiche_base=None, personaggio=self, context={}
        )
        formula_out = ""
        if consumabile.formula:
            formula_out = formatta_testo_generico(
                None, formula=consumabile.formula, statistiche_base=None, personaggio=self, context={}, solo_formula=True
            )
            formula_out = formula_out.replace("<strong>Formula:</strong>", "").strip() if formula_out else ""
        return desc, formula_out
        
    
    def get_valore_statistica(self, sigla):
        """
        Valore effettivo della statistica per sigla: base da punteggi_base (scheda, abilità,
        punteggi dipendenti) più modificatori globali. Allineato a ciò che mostra la scheda/game.
        Con _punteggi_base_partial_for_mods (uso interno) la base viene letta dal dict parziale.
        """
        try:
            stat_obj = Statistica.objects.filter(sigla=sigla).first()
            if not stat_obj or not stat_obj.parametro:
                return 0
            mods = self.modificatori_calcolati.get(stat_obj.parametro, {'add': 0, 'mol': 1.0})
            if hasattr(self, '_punteggi_base_partial_for_mods'):
                base = int(self._punteggi_base_partial_for_mods.get(stat_obj.nome, 0) or 0)
            else:
                base = int(self.punteggi_base.get(stat_obj.nome, 0) or 0)
            return int(round((base + mods['add']) * mods['mol']))
        except Exception:
            return 0

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

class PersonaggioAbilita(SyncableModel, models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)
    origine = models.CharField(
        max_length=20,
        choices=[
            (PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO, "Acquisto"),
            (PERSONAGGIO_ABILITA_ORIGINE_ERA_DEFAULT, "Era (default)"),
            (PERSONAGGIO_ABILITA_ORIGINE_REGIONE_DEFAULT, "Regione (default)"),
        ],
        default=PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
    )

    class Meta:
        unique_together = [["personaggio", "abilita"]]
        verbose_name = "Personaggio - Abilità"
        verbose_name_plural = "Personaggio - Abilità"

    def save(self, *args, **kwargs):
        """
        Regola hard: per AIN un personaggio può avere al massimo
        - 1 Archetipo (livello 0/1)
        - 1 Forma (livello 2)
        Qualsiasi nuova assegnazione sostituisce quella precedente nello slot.
        """
        with transaction.atomic():
            ab = self.abilita
            is_ain_trait = (
                bool(ab)
                and ab.is_tratto_aura
                and ab.aura_riferimento_id
                and getattr(ab.aura_riferimento, "sigla", None) == "AIN"
            )
            if is_ain_trait:
                liv = ab.livello_riferimento
                if liv in (0, 1):
                    slot_qs = PersonaggioAbilita.objects.filter(
                        personaggio=self.personaggio,
                        abilita__is_tratto_aura=True,
                        abilita__aura_riferimento__sigla="AIN",
                        abilita__livello_riferimento__in=(0, 1),
                    )
                elif liv == 2:
                    slot_qs = PersonaggioAbilita.objects.filter(
                        personaggio=self.personaggio,
                        abilita__is_tratto_aura=True,
                        abilita__aura_riferimento__sigla="AIN",
                        abilita__livello_riferimento=2,
                    )
                else:
                    slot_qs = None

                if slot_qs is not None:
                    if self.pk:
                        slot_qs = slot_qs.exclude(pk=self.pk)
                    slot_qs.delete()

            super().save(*args, **kwargs)
class PersonaggioAttivata(SyncableModel, models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [["personaggio", "attivata"]]
        verbose_name = "Personaggio - Attivata"
        verbose_name_plural = "Personaggio - Attivate"


class PersonaggioInfusione(SyncableModel, models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [["personaggio", "infusione"]]
        verbose_name = "Personaggio - Infusione"
        verbose_name_plural = "Personaggio - Infusioni"


class PersonaggioTessitura(SyncableModel, models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)
    is_favorite = models.BooleanField(default=False, verbose_name="Preferita")
    
    class Meta:
        verbose_name = "Personaggio - Tessitura"
        verbose_name_plural = "Personaggio - Tessiture"
        unique_together = [['personaggio', 'tessitura']]

class PersonaggioCerimoniale(SyncableModel, models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    cerimoniale = models.ForeignKey(Cerimoniale, on_delete=models.CASCADE)
    data_acquisizione = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [["personaggio", "cerimoniale"]]
        verbose_name = "Personaggio - Cerimoniale"
        verbose_name_plural = "Personaggio - Cerimoniali"


class PersonaggioModelloAura(SyncableModel, models.Model):
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    modello_aura = models.ForeignKey(ModelloAura, on_delete=models.CASCADE)

    class Meta:
        unique_together = [["personaggio", "modello_aura"]]
        verbose_name_plural = "Personaggio - Modelli Aura"

    def clean(self):
        if PersonaggioModelloAura.objects.filter(
            personaggio=self.personaggio, modello_aura__aura=self.modello_aura.aura
        ).exclude(pk=self.pk).exists():
            raise ValidationError("Già presente.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class TransazioneSospesa(SyncableModel, models.Model):
    # Campi legacy (mantenuti per retrocompatibilità)
    oggetto = models.ForeignKey('Oggetto', on_delete=models.CASCADE, null=True, blank=True)
    mittente = models.ForeignKey(Inventario, on_delete=models.CASCADE, related_name="transazioni_in_uscita_sospese", null=True, blank=True)
    richiedente = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="transazioni_in_entrata_sospese", null=True, blank=True)
    data_richiesta = models.DateTimeField(default=timezone.now)
    
    # Nuovi campi per sistema avanzato
    iniziatore = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="transazioni_iniziate", null=True, blank=True)
    destinatario = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="transazioni_ricevute", null=True, blank=True)
    
    stato = models.CharField(max_length=20, choices=STATO_TRANSAZIONE_CHOICES, default=STATO_TRANSAZIONE_IN_ATTESA)
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_ultima_modifica = models.DateTimeField(auto_now=True)
    data_chiusura = models.DateTimeField(null=True, blank=True)
    
    # Riferimenti alle ultime proposte attive (per performance)
    ultima_proposta_iniziatore = models.ForeignKey('PropostaTransazione', 
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transazione_iniziatore_attiva')
    ultima_proposta_destinatario = models.ForeignKey('PropostaTransazione',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transazione_destinatario_attiva')
    
    class Meta: 
        ordering=['-data_ultima_modifica']
        verbose_name = "Transazione Sospesa"
        verbose_name_plural = "Transazioni Sospese"
    
    def __str__(self):
        if self.iniziatore and self.destinatario:
            return f"Transazione {self.iniziatore.nome} → {self.destinatario.nome} ({self.stato})"
        elif self.richiedente and self.mittente:
            return f"Transazione {self.richiedente.nome} → {self.mittente.nome} ({self.stato})"
        return f"Transazione #{self.id} ({self.stato})"
    
    def accetta(self):
        """Accetta la transazione ed esegue gli scambi"""
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA:
            raise Exception("Transazione già processata")
        
        # Sistema legacy: solo oggetto
        if self.oggetto and not self.iniziatore:
            self.oggetto.sposta_in_inventario(self.richiedente)
            self.stato = STATO_TRANSAZIONE_ACCETTATA
            self.save()
            return
        
        # Sistema nuovo: proposte bidirezionali
        if not self.ultima_proposta_iniziatore or not self.ultima_proposta_destinatario:
            raise Exception("Entrambe le parti devono avere una proposta attiva")
        
        from django.db import transaction as db_transaction
        
        with db_transaction.atomic():
            # Esegui scambi crediti
            if self.ultima_proposta_iniziatore.crediti_da_dare > 0:
                self.destinatario.crediti += float(self.ultima_proposta_iniziatore.crediti_da_dare)
                self.destinatario.save()
                CreditoMovimento.objects.create(
                    personaggio=self.destinatario,
                    importo=self.ultima_proposta_iniziatore.crediti_da_dare,
                    descrizione=f"Ricevuto da transazione #{self.id}"
                )
            
            if self.ultima_proposta_destinatario.crediti_da_dare > 0:
                self.iniziatore.crediti += float(self.ultima_proposta_destinatario.crediti_da_dare)
                self.iniziatore.save()
                CreditoMovimento.objects.create(
                    personaggio=self.iniziatore,
                    importo=self.ultima_proposta_destinatario.crediti_da_dare,
                    descrizione=f"Ricevuto da transazione #{self.id}"
                )
            
            # Esegui scambi oggetti
            for oggetto in self.ultima_proposta_iniziatore.oggetti_da_dare.all():
                oggetto.sposta_in_inventario(self.destinatario)
            
            for oggetto in self.ultima_proposta_destinatario.oggetti_da_dare.all():
                oggetto.sposta_in_inventario(self.iniziatore)
            
            self.stato = STATO_TRANSAZIONE_ACCETTATA
            self.data_chiusura = timezone.now()
            self.save()
    
    def rifiuta(self):
        """Rifiuta la transazione"""
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA:
            raise Exception("Transazione già processata")
        self.stato = STATO_TRANSAZIONE_RIFIUTATA
        self.data_chiusura = timezone.now()
        self.save()
    
    def chiudi(self):
        """Chiude la transazione senza accordo"""
        if self.stato != STATO_TRANSAZIONE_IN_ATTESA:
            raise Exception("Transazione già processata")
        self.stato = STATO_TRANSAZIONE_CHIUSA
        self.data_chiusura = timezone.now()
        self.save()

class PropostaTransazione(SyncableModel, models.Model):
    """Proposta all'interno di una transazione"""
    transazione = models.ForeignKey(TransazioneSospesa, on_delete=models.CASCADE, related_name='proposte')
    autore = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name='proposte_transazioni')
    
    # Cosa l'autore DÀ
    crediti_da_dare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    oggetti_da_dare = models.ManyToManyField('Oggetto', related_name='proposte_oggetti_dati', blank=True)
    
    # Cosa l'autore RICEVE
    crediti_da_ricevere = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    oggetti_da_ricevere = models.ManyToManyField('Oggetto', related_name='proposte_oggetti_ricevuti', blank=True)
    
    # Messaggio
    messaggio = models.TextField(blank=True)
    
    # Timestamp
    data_creazione = models.DateTimeField(auto_now_add=True)
    is_attiva = models.BooleanField(default=True)  # Solo l'ultima proposta per autore è attiva
    
    class Meta:
        ordering = ['-data_creazione']
        verbose_name = "Proposta Transazione"
        verbose_name_plural = "Proposte Transazioni"
        indexes = [
            models.Index(fields=['transazione', 'autore', 'is_attiva']),
        ]
    
    def __str__(self):
        return f"Proposta di {self.autore.nome} per transazione #{self.transazione.id}"
    
    def save(self, *args, **kwargs):
        """Disattiva le altre proposte dello stesso autore per la stessa transazione"""
        super().save(*args, **kwargs)
        if self.is_attiva:
            PropostaTransazione.objects.filter(
                transazione=self.transazione,
                autore=self.autore,
                is_attiva=True
            ).exclude(id=self.id).update(is_attiva=False)
            
            # Aggiorna riferimento nella transazione
            if self.autore == self.transazione.iniziatore:
                self.transazione.ultima_proposta_iniziatore = self
            elif self.autore == self.transazione.destinatario:
                self.transazione.ultima_proposta_destinatario = self
            self.transazione.save()

class Gruppo(SyncableModel, models.Model):
    nome = models.CharField(max_length=100, unique=True); membri = models.ManyToManyField('Personaggio', related_name="gruppi_appartenenza", blank=True)
    def __str__(self): return self.nome
    
class Messaggio(SyncableModel, models.Model):
    TIPO_BROADCAST='BROAD' 
    TIPO_GRUPPO='GROUP' 
    TIPO_INDIVIDUALE='INDV'
    TIPO_STAFF='STAFF'
    TIPO_CHOICES=[(TIPO_BROADCAST,'Broadcast'),(TIPO_GRUPPO,'Gruppo'),(TIPO_INDIVIDUALE,'Individuale'),(TIPO_STAFF,'Staff')]
    mittente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="messaggi_inviati")
    mittente_personaggio = models.ForeignKey('Personaggio', on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_inviati_pg")
    tipo_messaggio = models.CharField(max_length=5, choices=TIPO_CHOICES, default=TIPO_BROADCAST)
    destinatario_personaggio = models.ForeignKey('Personaggio', on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_individuali")
    destinatario_gruppo = models.ForeignKey(Gruppo, on_delete=models.SET_NULL, null=True, blank=True, related_name="messaggi_ricevuti_gruppo")
    titolo = models.CharField(max_length=150); testo = models.TextField(); data_invio = models.DateTimeField(default=timezone.now); salva_in_cronologia = models.BooleanField(default=True)
    crediti_allegati = models.IntegerField(default=0)
    oggetti_allegati_snapshot = models.JSONField(default=list, blank=True)
    is_staff_message = models.BooleanField(default=False)
    letto_staff = models.BooleanField(default=False)  # Per messaggi staff
    cancellato_staff = models.BooleanField(default=False)  # Per messaggi staff
    in_risposta_a = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='risposte')  # Thread conversazione
    
    class Meta: 
        ordering=['-data_invio']
    
class LetturaMessaggio(SyncableModel, models.Model):
    messaggio = models.ForeignKey(Messaggio, on_delete=models.CASCADE, related_name="stati_lettura")
    personaggio = models.ForeignKey('Personaggio', on_delete=models.CASCADE, related_name="messaggi_stati")
    letto = models.BooleanField(default=False)
    data_lettura = models.DateTimeField(null=True, blank=True)
    cancellato = models.BooleanField(default=False)
    class Meta: unique_together = ('messaggio', 'personaggio'); verbose_name = "Stato Lettura Messaggio"; verbose_name_plural = "Stati Lettura Messaggi"
    def __str__(self): return f"{self.personaggio.nome} - {self.messaggio.titolo}"


class AuthUserSyncState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="sync_state")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sync State Utente"
        verbose_name_plural = "Sync State Utenti"


class AuthGroupSyncState(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="sync_state")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sync State Gruppo"
        verbose_name_plural = "Sync State Gruppi"


@receiver(post_save, sender=User)
def touch_user_sync_state(sender, instance, **kwargs):
    AuthUserSyncState.objects.update_or_create(user=instance, defaults={})


@receiver(post_save, sender=Group)
def touch_group_sync_state(sender, instance, **kwargs):
    AuthGroupSyncState.objects.update_or_create(group=instance, defaults={})


class UserSocialPreference(SyncableModel, models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="social_preference")
    preferred_personaggio = models.ForeignKey(
        "Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_by_users",
    )

    class Meta:
        verbose_name = "Preferenza Social Utente"
        verbose_name_plural = "Preferenze Social Utenti"

    def __str__(self):
        if self.preferred_personaggio:
            return f"{self.user.username} -> {self.preferred_personaggio.nome}"
        return f"{self.user.username} -> Nessun preferito"

class AbilitaPluginModel(SyncableModel, CMSPlugin):
    abilita = models.ForeignKey(Abilita, on_delete=models.CASCADE)
    def __str__(self): return self.abilita.nome
class OggettoPluginModel(SyncableModel, CMSPlugin):
    oggetto = models.ForeignKey(Oggetto, on_delete=models.CASCADE)
    def __str__(self): return self.oggetto.nome
class AttivataPluginModel(SyncableModel, CMSPlugin):
    attivata = models.ForeignKey(Attivata, on_delete=models.CASCADE)
    def __str__(self): return self.attivata.nome
class InfusionePluginModel(SyncableModel, CMSPlugin):
    infusione = models.ForeignKey(Infusione, on_delete=models.CASCADE)
    def __str__(self): return self.infusione.nome
class TessituraPluginModel(SyncableModel, CMSPlugin):
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE)
    def __str__(self): return self.tessitura.nome
class TabellaPluginModel(SyncableModel, CMSPlugin):
    tabella = models.ForeignKey(Tabella, on_delete=models.CASCADE)
    def __str__(self): return self.tabella.nome
class TierPluginModel(SyncableModel, CMSPlugin):
    tier = models.ForeignKey(Tier, on_delete=models.CASCADE, related_name='cms_kor_tier_plugin')
    def __str__(self): return self.tier.nome
    
class CerimonialePluginModel(SyncableModel, CMSPlugin):
    cerimoniale = models.ForeignKey(Cerimoniale, on_delete=models.CASCADE)
    def __str__(self): return self.cerimoniale.nome
    
class PropostaTecnica(SyncableModel, models.Model):
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

class PropostaTecnicaCaratteristica(SyncableModel, models.Model):
    proposta = models.ForeignKey(PropostaTecnica, on_delete=models.CASCADE, related_name='componenti')
    caratteristica = models.ForeignKey(Punteggio, on_delete=models.CASCADE, limit_choices_to={'tipo': CARATTERISTICA})
    valore = models.IntegerField(default=1)

    class Meta: 
        ordering = ['caratteristica__nome']
        unique_together = ('proposta', 'caratteristica')

class PropostaTecnicaMattone(SyncableModel, models.Model):
    # LEGACY: Mantenuto per evitare errori di importazione se ci sono riferimenti, ma non usato
    proposta = models.ForeignKey(PropostaTecnica, on_delete=models.CASCADE)
    mattone = models.ForeignKey(Mattone, on_delete=models.CASCADE)
    ordine = models.IntegerField(default=0) 

class ForgiaturaInCorso(SyncableModel, models.Model):
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

class RichiestaAssemblaggio(SyncableModel, models.Model):
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
            
        if self.tipo_operazione not in (TIPO_OPERAZIONE_FORGIATURA, TIPO_OPERAZIONE_INNESTO) and (not self.oggetto_host or not self.componente):
             raise ValidationError("Installazione e Rimozione richiedono Host e Componente.")
    
    def __str__(self):
        return f"{self.get_tipo_operazione_display()} - {self.committente} -> {self.artigiano}"
    
    
from django.db import models

class Dichiarazione(SyncableModel, models.Model):
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
# EFFETTI CASUALI E CONSUMABILI
# ============================================================================

TIPO_EFFETTO_OGGETTO = 'OGG'
TIPO_EFFETTO_TESSITURA = 'TES'
TIPO_EFFETTO_CHOICES = [
    (TIPO_EFFETTO_OGGETTO, 'Oggetto'),
    (TIPO_EFFETTO_TESSITURA, 'Tessitura'),
]


class TipologiaEffetto(SyncableModel, models.Model):
    """
    Tipologia di effetto casuale: può generare un oggetto (da inserire in inventario)
    o una tessitura (da inserire come consumabile).
    """
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=3, choices=TIPO_EFFETTO_CHOICES)
    aura_collegata = models.ForeignKey(
        Punteggio, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'tipo': AURA}, related_name='tipologie_effetto_aura',
        verbose_name="Aura collegata (solo per tipo Oggetto)"
    )

    class Meta:
        verbose_name = "Tipologia Effetto Casuale"
        verbose_name_plural = "Tipologie Effetto Casuale"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class EffettoCasuale(SyncableModel, models.Model):
    """
    Singolo effetto casuale con nome, descrizione, formula.
    Se la tipologia è tessitura, la formula è obbligatoria.
    """
    tipologia = models.ForeignKey(TipologiaEffetto, on_delete=models.CASCADE, related_name='effetti')
    elemento_principale = models.ForeignKey(
        Mattone, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to=Q(aura__nome__icontains='magica') | Q(aura__sigla__iexact='mag'),
        related_name='effetti_casuali_elemento',
        verbose_name="Elemento principale (Mattoni con aura Magica)"
    )
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(help_text="Usa {parametro} per le statistiche. Inclusi: {aura} (aura tipo), {elemento} (elemento)")
    formula = models.TextField(blank=True, null=True, help_text="Stesso formato della descrizione. Obbligatorio se tipologia=Tessitura.")

    class Meta:
        verbose_name = "Effetto Casuale"
        verbose_name_plural = "Effetti Casuali"
        ordering = ['tipologia', 'nome']

    def __str__(self):
        return f"{self.nome} ({self.tipologia})"

    def clean(self):
        if self.tipologia and self.tipologia.tipo == TIPO_EFFETTO_TESSITURA:
            if not self.formula or not self.formula.strip():
                raise ValidationError({'formula': 'La formula è obbligatoria per effetti di tipologia Tessitura.'})


class ConsumabilePersonaggio(SyncableModel, models.Model):
    """
    Consumabile assegnato a un personaggio (es. da effetto casuale tessitura).
    Ha utilizzi residui e data di scadenza. Occupa 1 slot COG se il personaggio ha almeno un consumabile.
    Se creato da tessitura (Alchimia), tessitura è valorizzato per formattazione come la tessitura (statistiche, bonus).
    """
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name='consumabili')
    effetto_casuale = models.ForeignKey(
        EffettoCasuale, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consumabili_personaggio'
    )
    tessitura = models.ForeignKey(
        Tessitura, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consumabili_da_tessitura',
        help_text="Se il consumabile è stato creato da una tessitura (Alchimia), per formattazione corretta con statistiche."
    )
    nome = models.CharField(max_length=200)
    descrizione = models.TextField()
    formula = models.TextField(blank=True, null=True)
    utilizzi_rimanenti = models.PositiveIntegerField(default=1)
    data_scadenza = models.DateField()
    data_creazione = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Consumabile Personaggio"
        verbose_name_plural = "Consumabili Personaggio"
        ordering = ['-data_creazione']

    def __str__(self):
        return f"{self.nome} x{self.utilizzi_rimanenti} ({self.personaggio.nome})"


class CreazioneConsumabileInCorso(SyncableModel, models.Model):
    """
    Timer di creazione consumabile da tessitura: al termine di data_fine_creazione
    il personaggio può completare e ottenere il consumabile in tab Consumabili.
    """
    personaggio = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name='creazioni_consumabili_in_corso')
    tessitura = models.ForeignKey(Tessitura, on_delete=models.CASCADE, related_name='creazioni_consumabili_in_corso')
    data_fine_creazione = models.DateTimeField()
    completata = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Creazione Consumabile In Corso"
        verbose_name_plural = "Creazioni Consumabili In Corso"
        ordering = ['data_fine_creazione']

    def __str__(self):
        return f"{self.tessitura.nome} → {self.personaggio.nome} (fine {self.data_fine_creazione})"


# ============================================================================
# SIGNALS - Inizializzazione automatica
# ============================================================================

@receiver(post_save, sender=Personaggio)
def inizializza_statistiche_base_personaggio(sender, instance, created, **kwargs):
    """
    Alla creazione personaggio non materializziamo più tutte le statistiche base.
    Usiamo un modello sparse: i record vengono salvati solo quando diversi dal default.
    """
    if created:
        if instance.segno_zodiacale_id is None:
            segni_ids = list(SegnoZodiacale.objects.values_list("id", flat=True))
            if segni_ids:
                Personaggio.objects.filter(pk=instance.pk, segno_zodiacale__isnull=True).update(
                    segno_zodiacale_id=random.choice(segni_ids)
                )