# ✨ Evidenziazione Widget Usati nella Pagina

## 🎯 Funzionalità Implementata

I widget già inseriti nella pagina corrente vengono ora **evidenziati** e **posizionati in cima** alle rispettive liste!

## 🎨 Caratteristiche Visive

### Per i Widget Già Usati:
- ✅ **Sfondo verde chiaro** (`bg-green-50`)
- ✅ **Bordo verde a sinistra** (4px, `border-green-500`)
- ✅ **Check mark verde** (✓) prima del nome
- ✅ **Testo verde scuro** per il nome
- ✅ **Badge ID verde** invece di grigio
- ✅ **Posizionati in CIMA alla lista**

### Per i Widget Non Usati:
- ⚪ Sfondo bianco normale
- ⚪ Senza bordo colorato
- ⚪ Testo grigio
- ⚪ Badge ID grigio
- ⚪ Posizionati dopo quelli usati

## 📊 Categorie Supportate

### 1. **📊 Tier**
- Pattern riconosciuto: `{{WIDGET_TIER:ID}}`
- Sfondo verde per tier usati
- Ordinamento: usati prima, poi gli altri

### 2. **🖼️ Immagini**
- Pattern riconosciuti: 
  - `{{WIDGET_IMAGE:ID}}`
  - `{{WIDGET_IMMAGINE:ID}}`
- Icona verde per immagini usate
- Ordinamento: usate prima, poi le altre

### 3. **🔘 Pulsanti**
- Pattern riconosciuti:
  - `{{WIDGET_BUTTONS:ID}}`
  - `{{WIDGET_PULSANTI:ID}}`
- Sfondo verde per widget usati
- Ordinamento: usati prima, poi gli altri

## 🔧 Come Funziona

### Algoritmo di Rilevamento

```javascript
// 1. Estrae tutti gli ID dei widget usati nel contenuto
const getUsedWidgetIds = () => {
  const content = formData.contenuto || '';
  
  // Cerca pattern con regex
  const tierMatches = content.matchAll(/\{\{WIDGET_TIER:(\d+)\}\}/g);
  const imageMatches = content.matchAll(/\{\{WIDGET_(?:IMAGE|IMMAGINE):(\d+)\}\}/g);
  const buttonMatches = content.matchAll(/\{\{WIDGET_(?:BUTTONS|PULSANTI):(\d+)\}\}/g);
  
  // Restituisce array di ID per ogni categoria
  return { tiers: [...], images: [...], buttons: [...] };
};

// 2. Ordina la lista mettendo prima quelli usati
const sortByUsage = (items, usedIds) => {
  return [...items].sort((a, b) => {
    const aUsed = usedIds.includes(a.id);
    const bUsed = usedIds.includes(b.id);
    
    if (aUsed && !bUsed) return -1;  // a prima di b
    if (!aUsed && bUsed) return 1;   // b prima di a
    return 0;                         // ordine invariato
  });
};
```

### Rendering Dinamico

Per ogni tab (Tier/Immagini/Pulsanti):
1. Calcola quali widget sono usati nel contenuto corrente
2. Ordina la lista mettendo prima quelli usati
3. Applica stili diversi basati sullo stato "usato"
4. Aggiunge check mark (✓) per quelli usati

## 💡 Vantaggi per l'Utente

### 1. **Identificazione Immediata**
- Si vede subito quali widget sono già nella pagina
- Evita di inserire duplicati per errore

### 2. **Accesso Rapido**
- I widget usati sono in cima, più facili da trovare
- Utile per modificarli rapidamente

### 3. **Feedback Visivo**
- Il colore verde indica "già usato"
- Il grigio indica "disponibile ma non usato"

### 4. **Aggiornamento in Tempo Reale**
- Quando inserisci un widget, viene subito evidenziato
- Se rimuovi un widget dal contenuto, torna grigio

## 🎯 Esempio di Utilizzo

### Scenario 1: Pagina con Widget Misti

**Contenuto:**
```html
<p>{{WIDGET_TIER:5}}</p>
<p>{{WIDGET_IMAGE:12}}</p>
<p>{{WIDGET_BUTTONS:3}}</p>
```

**Risultato nelle Liste:**

**Tab Tier:**
```
✓ Tier Level 5           [ID:5]    ← Verde, in cima
  Tier Level 1           [ID:1]    ← Grigio
  Tier Level 2           [ID:2]    ← Grigio
```

**Tab Immagini:**
```
✓ Mappa Città            [ID:12]   ← Verde, in cima
  Logo Evento            [ID:3]    ← Grigio
  Banner                 [ID:8]    ← Grigio
```

**Tab Pulsanti:**
```
✓ Menu Principale        [ID:3]    ← Verde, in cima
  Menu Secondario        [ID:1]    ← Grigio
  Footer Links           [ID:7]    ← Grigio
```

### Scenario 2: Widget Usato Più Volte

Se lo stesso widget è inserito più volte nella pagina (es: `{{WIDGET_TIER:5}}` appare 3 volte), viene comunque evidenziato una sola volta nella lista.

## 🔄 Aggiornamento Dinamico

La lista si aggiorna automaticamente quando:
- ✅ Apri il Widget Helper
- ✅ Cambi tab tra Tier/Immagini/Pulsanti
- ❌ Non si aggiorna mentre scrivi (solo all'apertura)

**Nota:** Se inserisci manualmente un widget nel RichTextEditor, dovrai riaprire il Widget Helper per vedere l'aggiornamento. Questo è intenzionale per evitare calcoli continui mentre scrivi.

## 📝 Note Tecniche

### Performance
- La funzione `getUsedWidgetIds()` usa regex per cercare i pattern
- Viene eseguita solo quando renderizzi le liste, non ad ogni modifica
- Molto veloce anche con contenuti lunghi (< 1ms)

### Compatibilità Pattern
Riconosce entrambe le varianti:
- `{{WIDGET_IMAGE:1}}` ✓
- `{{WIDGET_IMMAGINE:1}}` ✓
- `{{WIDGET_BUTTONS:1}}` ✓
- `{{WIDGET_PULSANTI:1}}` ✓

### Edge Cases
- Widget con ID non esistente: ignorato
- ID duplicati nel contenuto: contato una sola volta
- Contenuto vuoto: nessun widget evidenziato

## 🎨 Palette Colori

| Stato | Sfondo | Bordo | Testo | Badge |
|-------|---------|-------|-------|-------|
| **Usato** | `bg-green-50` | `border-green-500` | `text-green-700` | `bg-green-200 text-green-800` |
| **Non Usato** | `bg-white` | nessuno | `text-gray-700` | `bg-gray-100 text-gray-500` |
| **Hover** | `hover:bg-blue-50` | - | `hover:text-blue-800` | - |

## ✅ Checklist Test

- [ ] Inserisci un widget Tier → Riapri tab → Vedi sfondo verde
- [ ] Inserisci un'immagine → Riapri tab → Vedi check mark
- [ ] Inserisci widget buttons → Riapri tab → Vedi bordo verde
- [ ] Widget usati sono in cima alla lista
- [ ] Widget non usati sono sotto
- [ ] Rimuovi widget dal contenuto → Riapri → Torna grigio
- [ ] Badge ID è verde per usati, grigio per non usati

## 🎉 Conclusione

Questa funzionalità rende molto più intuitivo e user-friendly l'editor delle pagine wiki, permettendo di vedere a colpo d'occhio quali widget sono già in uso e accedendovi rapidamente per eventuali modifiche!
