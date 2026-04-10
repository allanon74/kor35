# 🐛 Debug Icone Widget Buttons

## ❌ Problema

Le icone NON compaiono quando si visualizza la pagina wiki, ma COMPAIONO nel preview durante creazione/modifica.

## 🔍 Diagnosi

### Differenze tra Preview e Render Finale

**Nel Modal di Editing (ButtonWidgetEditorModal.jsx):**
```jsx
// Questo FUNZIONA
const IconPreview = ({ iconName, size = 20 }) => {
  const Icon = LucideIcons[iconName];
  return Icon ? <Icon size={size} /> : <div>...</div>;
};
```

**Nel Render della Pagina (WidgetButtons.jsx):**
```jsx
// Questo dovrebbe funzionare ma non lo fa
const IconComponent = button.icon && LucideIcons[button.icon] 
  ? LucideIcons[button.icon] 
  : null;
```

## 🔎 Step di Debug

### 1. Verifica Console Browser

Dopo aver fatto le modifiche, apri la console (F12) e cerca questi log:

```
=== Widget Buttons Full Data ===
Widget ID: 1
Widget Data: { ... }
Buttons Array: [ ... ]
First Button: { title: "...", icon: "...", ... }
Available Lucide Icons (sample): [ ... ]
================================
```

**Controlla:**
- ✅ Il campo `icon` è presente?
- ✅ Il valore dell'icona è una stringa non vuota?
- ✅ Il nome dell'icona è in PascalCase? (es: `"Sparkles"` non `"sparkles"`)

### 2. Verifica Dati Backend

Poi cerca questi log per ogni pulsante:

```
Button 0: {
  title: "Ambientazione",
  icon: "Scroll",              ← Deve essere presente
  iconExists: true,             ← Deve essere true
  iconComponent: function()     ← Deve essere una funzione
}
```

**Se vedi:**
- `icon: undefined` → Il backend non sta inviando il campo
- `icon: ""` → Il campo è vuoto nel database
- `icon: "scroll"` (lowercase) → Il nome non corrisponde (deve essere "Scroll")
- `iconExists: false` → Lucide non ha quell'icona
- `iconComponent: "not found"` → L'icona non esiste in Lucide

## 🛠️ Possibili Soluzioni

### Caso 1: Campo `icon` non arriva dal Backend

**Problema:** Il serializer Django non include il campo `icon`.

**Verifica nel serializer (`gestione_plot/serializers.py`):**

```python
class WikiButtonSerializer(serializers.ModelSerializer):
    class Meta:
        model = WikiButton
        fields = [
            'id', 'title', 'description', 'subtext', 'icon',  # ← 'icon' deve essere qui
            'style', 'size', 'color_preset',
            'link_type', 'wiki_slug', 'app_route', 'ordine'
        ]
```

**Se manca, aggiungilo** e riavvia Django.

### Caso 2: Nome Icona Errato nel Database

**Problema:** L'icona è salvata come `"scroll"` invece di `"Scroll"`.

**Soluzione:** 
- Nel Django Admin, apri il widget
- Correggi il nome dell'icona in PascalCase
- Salva

**Nomi corretti Lucide:**
- ✅ `Sparkles` (non `sparkles` o `SPARKLES`)
- ✅ `BookOpen` (non `bookopen` o `book-open`)
- ✅ `LogIn` (non `login` o `Login`)
- ✅ `Scroll` (non `scroll`)

### Caso 3: Icona Non Esiste in Lucide

**Problema:** Hai usato un nome che non esiste in Lucide.

**Soluzione:**
1. Controlla i nomi disponibili nel modal di editing
2. Usa solo i nomi dalla lista dropdown
3. Oppure cerca in: https://lucide.dev/icons

## 🔧 Modifiche Implementate

### 1. Debug Avanzato

Ho aggiunto log dettagliati che mostrano:
- Dati completi del widget
- Ogni singolo pulsante con dettagli icona
- Lista sample delle icone Lucide disponibili
- Warning se un'icona non viene trovata

### 2. Fallback Visivo

Se l'icona non viene trovata:
- Mostra un "?" al posto dell'icona
- Il pulsante si vede comunque (non crasha)
- Aiuta a identificare il problema visivamente

### 3. Case-Insensitive Lookup

Ora prova a cercare l'icona in due modi:
```javascript
IconComponent = LucideIcons[button.icon] ||                    // Esatto
               LucideIcons[button.icon.charAt(0).toUpperCase() + button.icon.slice(1)] || // Capitalizzato
               null;
```

## 📋 Checklist Debug

1. [ ] Apri console browser (F12)
2. [ ] Vai su una pagina con widget buttons
3. [ ] Cerca "Widget Buttons Full Data"
4. [ ] Verifica che `icon` sia presente e corretto
5. [ ] Cerca "Button 0:", "Button 1:", etc.
6. [ ] Verifica `iconExists: true` e `iconComponent: function`
7. [ ] Se vedi warnings, correggi i nomi delle icone
8. [ ] Ricarica la pagina

## 🎯 Test Rapido

### Crea un Widget di Test Semplice

1. Django Admin → Widget Pulsanti → Aggiungi
2. Aggiungi UN pulsante con:
   - Title: "Test"
   - Icon: `Sparkles` (esattamente così)
   - Style: gradient
   - Size: large
   - Link type: wiki
   - Wiki slug: home
3. Salva
4. Inserisci `{{WIDGET_BUTTONS:1}}` in una pagina
5. Apri console e controlla i log

## ✅ Verifica Finale

Una volta risolto, dovresti vedere:
- ✅ Icona visibile nel pulsante
- ✅ Log senza warning
- ✅ `iconExists: true` per ogni pulsante
- ✅ Nessun "?" al posto delle icone

## 💡 Nota Importante

**Il fatto che le icone compaiano nel preview del modal MA NON nella pagina** suggerisce che:

1. Il codice React è corretto (altrimenti non funzionerebbe nel modal)
2. Il problema è nei **dati che arrivano dal backend**
3. Probabilmente il campo `icon` è vuoto o non viene serializzato

**Soluzione più probabile:** Controlla il database Django e verifica che le icone siano effettivamente salvate nel campo `icon` del modello `WikiButton`.
