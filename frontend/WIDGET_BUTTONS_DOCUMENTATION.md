# Widget Pulsanti Configurabili - Documentazione Implementazione

## 📋 Panoramica

È stato implementato un sistema completo per gestire pulsanti configurabili nelle pagine Wiki. I pulsanti possono puntare a:
- **Pagine Wiki** (tramite slug)
- **Sezioni App** (tramite route)

## 🎨 Caratteristiche

### Stili Disponibili
1. **Gradiente (Grande)**: Pulsanti grandi con gradiente colorato, effetto hover e cerchio animato
2. **Chiaro (Compatto)**: Pulsanti più compatti con sfondo chiaro e bordo colorato

### Dimensioni
- **Piccolo**: Padding 4, icona 24px
- **Medio**: Padding 5, icona 28px  
- **Grande**: Padding 6, icona 32px

### Schemi Colore (10 preset)
1. Indaco-Viola
2. Rosso-Arancio
3. Smeraldo-Verde Acqua
4. Blu-Indaco
5. Rosa
6. Ambra-Arancio
7. Ciano-Blu
8. Viola-Porpora
9. Ardesia-Grigio
10. Lime-Verde

### Icone
- 50+ icone comuni da Lucide React
- Opzionale (può essere omessa)

### Layout Responsive
- **Desktop**: Distribuzione automatica su più colonne (1-3)
- **Mobile**: Adattamento automatico a larghezza piena
- Gestione intelligente delle righe in base al numero di pulsanti

## 📁 File Creati/Modificati

### Frontend React

#### Nuovi File
1. **`src/components/wg/WidgetButtons.jsx`**
   - Component principale che renderizza il widget
   - Gestisce layout e distribuzione pulsanti
   - Supporta entrambi gli stili (gradient/light)
   - Export dei preset per uso in altri componenti

2. **`src/components/wiki/ButtonWidgetEditorModal.jsx`**
   - Modal completo per configurare i widget
   - Interfaccia a due colonne (lista + form)
   - Drag & drop per riordinare pulsanti
   - Preview live dei colori
   - Form di configurazione completo

#### File Modificati
3. **`src/components/WikiRenderer.jsx`**
   - Aggiunto import di `WidgetButtons`
   - Aggiunto case `'BUTTONS'` e `'PULSANTI'` nello switch

4. **`src/components/wiki/WikiPageEditorModal.jsx`**
   - Aggiunto import del `ButtonWidgetEditorModal`
   - Aggiunta tab "🔘 Pulsanti" nel widget helper
   - Implementata logica per creare e inserire widget

5. **`src/api.js`**
   - Aggiunte funzioni API:
     - `getWidgetButtons(id)`
     - `getWidgetButtonsList()`
     - `createWidgetButtons(data, onLogout)`
     - `updateWidgetButtons(id, data, onLogout)`
     - `deleteWidgetButtons(id, onLogout)`

### Backend Django

#### File Modificati

6. **`gestione_plot/models.py`**
   - Aggiunto modello `WikiButtonWidget`:
     - Contiene lista di pulsanti
     - Metadati (creatore, date)
     - Relazione one-to-many con WikiButton
   
   - Aggiunto modello `WikiButton`:
     - Tutti i campi di configurazione
     - Choice fields per style, size, color, link_type
     - Foreign key a WikiButtonWidget
     - Ordinamento

7. **`gestione_plot/serializers.py`**
   - `WikiButtonSerializer`: Serializer per singoli pulsanti
   - `WikiButtonWidgetSerializer`: Serializer per widget completo
     - Gestisce creazione/update annidato dei pulsanti
     - Metodi `create()` e `update()` personalizzati

8. **`gestione_plot/views.py`**
   - `PublicWikiButtonWidgetViewSet`: API pubblica read-only
   - `StaffWikiButtonWidgetViewSet`: API staff con CRUD completo
     - Usa `prefetch_related('buttons')` per performance
     - Imposta automaticamente il creatore

9. **`gestione_plot/urls.py`**
   - Route pubbliche: `/plot/api/public/wiki-buttons/`
   - Route staff: `/plot/api/staff/wiki-buttons/`

10. **`gestione_plot/admin.py`**
    - `WikiButtonInline`: Inline per gestire pulsanti
    - `WikiButtonWidgetAdmin`: Admin del widget con inline
    - `WikiButtonAdmin`: Admin standalone per pulsanti

## 🚀 Prossimi Passi (per l'utente)

### 1. Creare le Migration Django

```bash
cd /home/django/progetti/kor35
source venv/bin/activate  # o il percorso del tuo virtual environment
python manage.py makemigrations gestione_plot
python manage.py migrate
```

### 2. Riavviare il Server Django (se in esecuzione)

```bash
python manage.py runserver
```

### 3. Testare il Sistema

1. Accedi al Django Admin
2. Vai su "Widget Pulsanti" 
3. Crea un nuovo widget con alcuni pulsanti
4. Modifica una pagina wiki
5. Clicca su "Inserisci Widget" → Tab "🔘 Pulsanti"
6. Seleziona il widget creato
7. Salva la pagina
8. Visualizza la pagina per vedere i pulsanti

## 💡 Utilizzo nel Contenuto Wiki

### Sintassi per Inserire il Widget

```html
<p>{{WIDGET_BUTTONS:1}}</p>
```

Dove `1` è l'ID del widget creato.

### Note Importanti

- I widget BUTTONS supportano sia `{{WIDGET_BUTTONS:ID}}` che `{{WIDGET_PULSANTI:ID}}`
- Il sistema riconosce automaticamente entrambe le sintassi
- I pulsanti vengono distribuiti automaticamente su più righe se necessari
- Il layout è completamente responsive

## 🎯 Esempi di Configurazione

### Esempio 1: Menu Principale (2 pulsanti grandi)
- **Stile**: Gradiente
- **Dimensione**: Grande
- **Pulsante 1**: "Sei Nuovo?" → wiki slug: `nuovo` (Colore: Indaco-Viola)
- **Pulsante 2**: "Veterano?" → app route: `/app` (Colore: Rosso-Arancio)

### Esempio 2: Menu Sezioni (4 pulsanti compatti)
- **Stile**: Chiaro
- **Dimensione**: Medio
- **Pulsante 1**: "Ambientazione" → wiki slug: `ambientazione` (Colore: Smeraldo-Verde Acqua)
- **Pulsante 2**: "Regolamento" → wiki slug: `regolamento` (Colore: Blu-Indaco)
- **Pulsante 3**: "Personaggi" → wiki slug: `personaggi` (Colore: Rosa)
- **Pulsante 4**: "Eventi" → wiki slug: `eventi` (Colore: Ambra-Arancio)

## 🔧 Struttura Dati API

### Formato Request per Creazione Widget

```json
{
  "title": "Menu Principale",
  "buttons": [
    {
      "title": "Ambientazione",
      "description": "Scopri il mondo",
      "subtext": "Inizia da qui →",
      "icon": "Scroll",
      "style": "gradient",
      "size": "large",
      "color_preset": "emerald_teal",
      "link_type": "wiki",
      "wiki_slug": "ambientazione",
      "app_route": "",
      "ordine": 0
    }
  ]
}
```

### Formato Response

```json
{
  "id": 1,
  "title": "Menu Principale",
  "buttons": [...],
  "data_creazione": "2026-02-12T10:30:00Z",
  "data_modifica": "2026-02-12T10:30:00Z",
  "creatore": 1,
  "creatore_nome": "admin"
}
```

## 📱 Responsive Design

Il widget si adatta automaticamente:

- **1 pulsante**: 1 colonna
- **2 pulsanti**: 2 colonne (md:grid-cols-2)
- **3 pulsanti**: 3 colonne (md:grid-cols-3)
- **4 pulsanti**: 2 colonne (md:grid-cols-2)
- **5-6 pulsanti**: 3 colonne (md:grid-cols-3)
- **7+ pulsanti**: 3 colonne (md:grid-cols-3)

Su mobile (`< md breakpoint`), tutti i pulsanti vanno a larghezza piena (1 colonna).

## ✅ Checklist Completamento

- ✅ Modelli Django creati
- ✅ Serializer implementati
- ✅ ViewSet pubblici e staff configurati
- ✅ URL registrate
- ✅ Admin Django configurato con inline
- ✅ Component React widget creato
- ✅ Modal editor completo
- ✅ Integrazione nel WikiRenderer
- ✅ Integrazione nel WikiPageEditorModal
- ✅ API frontend create
- ✅ Preset colori (10)
- ✅ Preset dimensioni (3)
- ✅ Stili (2)
- ✅ Icone (50+)
- ✅ Layout responsive
- ✅ Supporto link wiki e app

## 🐛 Note per Debug

Se i pulsanti non vengono visualizzati:
1. Verificare che la migration sia stata applicata
2. Controllare la console browser per errori API
3. Verificare che l'ID del widget sia corretto
4. Controllare i permessi (staff può vedere anche in bozza)

## 🎉 Conclusione

Il sistema è completo e pronto all'uso! Permette di creare pulsanti configurabili bellissimi e funzionali, identici a quelli della home page, con totale libertà di personalizzazione colori, dimensioni, icone e destinazioni.
