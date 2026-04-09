# 🎛️ Guida Admin - Gestione Widget Homepage

## ✅ Sistema Completato!

Ora **esiste un'interfaccia admin completa** per modificare i contenuti dei widget Chi Siamo e Social senza toccare il codice!

---

## 🚀 Come Accedere all'Admin

1. Vai su **https://www.kor35.it/admin/** (o il tuo dominio)
2. Effettua il login con un account Staff/Superuser
3. Cerca la sezione **"GESTIONE PLOT"**

---

## 📋 Sezioni Disponibili

### 1. **Configurazione Sito** (Singleton)

**Percorso:** Admin Django → Gestione Plot → Configurazione Sito

Questa sezione gestisce tutte le informazioni mostrate nel **Widget "Chi Siamo"**:

#### Campi Disponibili:

**Informazioni Associazione:**
- Nome associazione (es: "KOR35")
- Descrizione breve (2-3 righe)
- Anno fondazione

**Sede:**
- Indirizzo
- CAP
- Città
- Provincia (sigla)
- Nazione

**Contatti:**
- Email principale
- PEC (opzionale)
- Telefono (opzionale)

#### Nota Importante:
- Esiste **un solo record** (Singleton pattern)
- Non puoi eliminarlo o crearne altri
- Le modifiche si riflettono immediatamente sul widget

---

### 2. **Link Social**

**Percorso:** Admin Django → Gestione Plot → Link Social

Questa sezione gestisce i link mostrati nel **Widget "Social"**.

#### Campi Disponibili:

- **Tipo**: Seleziona il tipo di social (WhatsApp, Instagram, Facebook, YouTube, Twitter, Discord, Telegram, Email, Altro)
- **Nome visualizzato**: Testo da mostrare (es: "@kor35official")
- **URL**: Link completo (es: "https://instagram.com/kor35official")
- **Descrizione**: Testo opzionale sotto il nome (es: "Seguici su Instagram")
- **Ordine**: Numero per ordinare i link (1 = primo, 2 = secondo, etc.)
- **Attivo**: Flag per mostrare/nascondere il link

#### Gestione Link:

✅ **Aggiungere un nuovo link:**
1. Clicca su "Aggiungi Link Social"
2. Seleziona il tipo
3. Inserisci nome, URL, descrizione
4. Imposta l'ordine (es: 6 per metterlo dopo gli altri)
5. Lascia "Attivo" spuntato
6. Salva

✅ **Modificare un link esistente:**
1. Clicca sul link dalla lista
2. Modifica i campi desiderati
3. Salva

✅ **Disattivare temporaneamente un link:**
1. Clicca sul link
2. Deseleziona "Attivo"
3. Salva (il link non verrà più mostrato ma rimane nel database)

✅ **Riordinare i link:**
- Modifica il campo "Ordine" per cambiare la posizione
- I numeri più bassi appaiono per primi

✅ **Eliminare un link:**
1. Clicca sul link
2. Clicca su "Elimina" in basso
3. Conferma

---

## 🎨 Tipo di Social Supportati

Il widget riconosce automaticamente questi tipi e applica colori/icone appropriate:

| Tipo | Icona | Colore |
|------|-------|--------|
| WhatsApp | Chat | Verde |
| Instagram | Instagram | Rosa |
| Facebook | Facebook | Blu |
| YouTube | YouTube | Rosso |
| Twitter | Twitter | Azzurro |
| Discord | Chat | Indigo |
| Telegram | Chat | Blu chiaro |
| Email | Mail | Grigio |
| Altro | Condividi | Grigio |

---

## 📊 Esempio Pratico

### Scenario: Vuoi cambiare il numero WhatsApp

1. Vai su `/admin/gestione_plot/linksocial/`
2. Trova il link "WhatsApp"
3. Clicca per modificarlo
4. Cambia l'URL da `https://wa.me/393471234567` al nuovo numero
5. Salva

✅ **Il widget verrà aggiornato automaticamente!**

### Scenario: Vuoi aggiungere Discord

1. Vai su `/admin/gestione_plot/linksocial/`
2. Clicca "Aggiungi Link Social"
3. Compila:
   - Tipo: `Discord`
   - Nome visualizzato: `Server Discord KOR35`
   - URL: `https://discord.gg/tuoinvite`
   - Descrizione: `Unisciti alla community`
   - Ordine: `6`
   - Attivo: ✅
4. Salva

### Scenario: Vuoi modificare la sede dell'associazione

1. Vai su `/admin/gestione_plot/configurazionesito/`
2. Clicca sull'unico record esistente
3. Modifica i campi della sezione "Sede":
   - Indirizzo: `Via Nuova 456`
   - CAP: `39040`
   - Città: `Leifers`
   - etc.
4. Salva

---

## 🔄 Dati Iniziali

Al primo avvio, il sistema ha già popolato:

**Configurazione Sito:**
- Nome: KOR35
- Descrizione generica
- Sede: Via Esempio 123, Bolzano
- Email: info@kor35.it
- Anno fondazione: 2020

**Link Social (5 pre-configurati):**
1. WhatsApp
2. Instagram
3. Facebook
4. YouTube
5. Email

⚠️ **Questi sono dati di esempio!** Modificali con i dati reali dell'associazione.

---

## 🛠️ Comandi Utili

### Ripopolare i dati iniziali (se necessario)

```bash
cd /home/django/kor35
source .venv/bin/activate
python manage.py popola_configurazione
```

**Nota:** Questo comando crea solo i record se non esistono già. Non sovrascrive quelli esistenti.

---

## 📍 API Endpoint

I widget chiamano questi endpoint pubblici (non richiedono autenticazione):

- **Configurazione Sito:** `GET /plot/api/public/configurazione-sito/1/`
- **Link Social:** `GET /plot/api/public/link-social/`

Puoi testarli direttamente nel browser o con Postman:
- https://www.kor35.it/plot/api/public/configurazione-sito/1/
- https://www.kor35.it/plot/api/public/link-social/

---

## 🎯 Widget che Usano Questi Dati

### WidgetChiSiamo
- **Fonte dati:** ConfigurazioneSito (record pk=1)
- **Aggiornamento:** Real-time (fetch ogni volta che la homepage viene caricata)
- **File componente:** `/home/django/kor35-app/src/components/wg/WidgetChiSiamo.jsx`

### WidgetSocial
- **Fonte dati:** LinkSocial (tutti i record con `attivo=True`)
- **Aggiornamento:** Real-time
- **Ordinamento:** Campo `ordine`, poi `tipo`
- **File componente:** `/home/django/kor35-app/src/components/wg/WidgetSocial.jsx`

### WidgetEventi
- **Fonte dati:** Evento (modello già esistente)
- **Gestione:** Admin Django → Gestione Plot → Eventi
- **File componente:** `/home/django/kor35-app/src/components/wg/WidgetEventi.jsx`

---

## ⚡ Ottimizzazioni Future

Se in futuro vuoi aggiungere funzionalità:

### Cache
Per migliorare le performance, potresti aggiungere cache agli endpoint:
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache per 15 minuti
def get_configurazione_sito(request):
    ...
```

### Immagini/Loghi
Potresti aggiungere campi `ImageField` ai modelli per:
- Logo associazione
- Immagini per ogni social link

### Traduzioni
Potresti usare Django i18n per supportare più lingue.

---

## 🆘 Troubleshooting

### I widget non mostrano i dati aggiornati

1. **Controlla che il backend sia attivo:**
   ```bash
   # Verifica che Django sia in esecuzione
   ps aux | grep manage.py
   ```

2. **Verifica che i dati esistano nel database:**
   ```bash
   cd /home/django/kor35
   source .venv/bin/activate
   python manage.py shell
   >>> from gestione_plot.models import ConfigurazioneSito, LinkSocial
   >>> ConfigurazioneSito.objects.all()
   >>> LinkSocial.objects.filter(attivo=True)
   ```

3. **Controlla la console del browser (F12)** per eventuali errori di fetch

### L'admin non mostra le nuove sezioni

1. **Verifica che le migration siano applicate:**
   ```bash
   cd /home/django/kor35
   source .venv/bin/activate
   python manage.py migrate gestione_plot
   ```

2. **Riavvia il server Django**

3. **Effettua un hard refresh del browser:** `Ctrl+Shift+R` (o `Cmd+Shift+R` su Mac)

### I link social non funzionano

- Verifica che gli URL siano completi e corretti (es: `https://` all'inizio)
- Per WhatsApp, usa il formato: `https://wa.me/393471234567` (numero internazionale senza spazi o simboli)
- Per email, usa: `mailto:tuaemail@esempio.it`

---

## 📚 Documenti Correlati

- **Setup Homepage:** `/home/django/kor35-app/HOMEPAGE_SETUP.md`
- **Modelli Django:** `/home/django/kor35/gestione_plot/models.py` (righe 337-420)
- **Admin Django:** `/home/django/kor35/gestione_plot/admin.py` (righe 157-211)

---

## 🎉 Conclusione

Ora puoi gestire completamente i contenuti della homepage tramite l'interfaccia admin Django, senza dover modificare il codice! 

Per qualsiasi dubbio o problema, controlla i log di Django o la console del browser.

---

**Data creazione:** 12 Febbraio 2026  
**Versione:** 1.0
