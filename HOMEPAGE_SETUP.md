# 🏠 Homepage Speciale KOR35 - Documentazione

## Cosa è stato fatto

Ho integrato una homepage speciale per la tua Wiki con il layout personalizzato che hai richiesto. Ecco un riepilogo completo delle modifiche.

---

## 📦 File Creati

### Backend (Django)

1. **`/home/django/kor35/gestione_plot/serializers.py`**
   - Aggiunto `EventoPubblicoSerializer` per esporre gli eventi pubblici

2. **`/home/django/kor35/gestione_plot/views.py`**
   - Aggiunto `PublicEventiViewSet` che espone gli eventi pubblici (ultimi 30 giorni + futuri)

3. **`/home/django/kor35/gestione_plot/urls.py`**
   - Registrato l'endpoint pubblico `/plot/api/public/eventi/`

### Frontend (React)

1. **`/home/django/kor35-app/src/components/HomePage.jsx`**
   - Componente principale della homepage con layout speciale
   - Gestisce i pulsanti "Sei nuovo?" e "Veterano?"
   - Include i tre widget Chi Siamo, Eventi e Social

2. **`/home/django/kor35-app/src/components/wg/WidgetChiSiamo.jsx`**
   - Widget con informazioni statiche sull'associazione
   - Mostra sede, contatti, email

3. **`/home/django/kor35-app/src/components/wg/WidgetEventi.jsx`**
   - Widget che recupera e mostra gli eventi dal backend
   - Distingue eventi futuri da quelli passati

4. **`/home/django/kor35-app/src/components/wg/WidgetSocial.jsx`**
   - Widget con i link ai social dell'associazione
   - Include WhatsApp, Instagram, Facebook, YouTube, Email

5. **`/home/django/kor35-app/src/api.js`**
   - Aggiunta funzione `getEventiPubblici()` per chiamare l'API

6. **`/home/django/kor35-app/src/pages/WikiPage.jsx`**
   - Modificato per rilevare slug "home" e usare il componente HomePage

7. **`/home/django/kor35-app/src/components/WikiRenderer.jsx`**
   - Registrati i nuovi widget (CHI_SIAMO, EVENTI, SOCIAL)

---

## 🎯 Struttura della Homepage

La homepage (slug: `home`) ora ha questo layout:

```
┌─────────────────────────────────────────┐
│           HEADER (con immagine)         │
└─────────────────────────────────────────┘
┌──────────────────┬──────────────────────┐
│  Sei Nuovo?      │  Veterano?           │
│  Scopri          │  Accedi al Profilo   │
└──────────────────┴──────────────────────┘
┌──────────────────┬──────────────────────┐
│  Ambientazione   │  Regolamento         │
└──────────────────┴──────────────────────┘
┌─────────┬─────────┬─────────────────────┐
│ Chi     │ Eventi  │ Social              │
│ Siamo   │         │                     │
└─────────┴─────────┴─────────────────────┘
```

---

## 🔧 Come Personalizzare

### 1. Informazioni Associazione (Chi Siamo)

Modifica il file `/home/django/kor35-app/src/components/wg/WidgetChiSiamo.jsx`:

- Linea 16-19: Descrizione dell'associazione
- Linea 24-29: Sede fisica
- Linea 35-37: Anno di fondazione
- Linea 43-47: Email e PEC

### 2. Link Social

Modifica il file `/home/django/kor35-app/src/components/wg/WidgetSocial.jsx`:

Linee 11-44, aggiorna gli URL:
```javascript
const socialLinks = [
  {
    name: 'WhatsApp',
    url: 'https://wa.me/TUO_NUMERO', // Sostituisci
    // ...
  },
  // ... altri social
];
```

### 3. Header della Homepage

Per modificare l'immagine e il titolo della homepage:
1. Accedi come Staff/Master
2. Clicca sul pulsante "✏️ Modifica Pagina Home" (in alto a destra)
3. Carica un'immagine di copertina
4. Modifica il titolo se necessario

### 4. Pulsanti di Navigazione

I pulsanti puntano a queste pagine (assicurati che esistano):
- "Sei nuovo?" → `/regolamento/nuovo`
- "Ambientazione" → `/regolamento/ambientazione`
- "Regolamento" → `/regolamento/regolamento`

Se vuoi cambiare i link, modifica il file `HomePage.jsx`:
- Linea 45: Link "Sei nuovo?"
- Linea 88: Link "Ambientazione"
- Linea 107: Link "Regolamento"

---

## 🎨 Aggiungere Eventi

Per aggiungere eventi che verranno mostrati sulla homepage:

1. Accedi al pannello admin Django: `https://www.kor35.it/admin/`
2. Vai su **Gestione Plot** → **Eventi**
3. Clicca su "Aggiungi Evento"
4. Compila i campi:
   - **Titolo**: Nome dell'evento
   - **Sinossi**: Descrizione breve
   - **Data inizio/fine**: Date dell'evento
   - **Luogo**: Dove si svolge
5. Salva

Gli eventi verranno automaticamente mostrati sulla homepage. Il widget mostra:
- Eventi futuri (con badge "Prossimo")
- Eventi passati degli ultimi 30 giorni

---

## 🚀 Come Testare

1. **Riavvia il server Django** (se necessario):
   ```bash
   cd /home/django/kor35
   python manage.py runserver
   ```

2. **Riavvia il server frontend** (se necessario):
   ```bash
   cd /home/django/kor35-app
   npm run dev
   ```

3. Vai su `https://app.kor35.it` (o `http://localhost:5173` in dev)

4. Dovresti vedere la nuova homepage con:
   - Header con immagine (se configurato)
   - Pulsanti "Sei nuovo?" e "Veterano?"
   - Pulsanti Ambientazione e Regolamento
   - Widget Chi Siamo, Eventi e Social

---

## 🔍 Troubleshooting

### Gli eventi non si caricano

1. Controlla la console del browser (F12) per errori
2. Verifica che l'endpoint `/plot/api/public/eventi/` sia accessibile
3. Assicurati che ci siano eventi nel database

### I link social non funzionano

Controlla che gli URL in `WidgetSocial.jsx` siano corretti e completi.

### La homepage non si visualizza

1. Verifica che esista una pagina wiki con slug "home"
2. Controlla che la pagina sia pubblica (non bozza)
3. Guarda la console del browser per errori

---

## 📝 Note Aggiuntive

- **Pagine richieste**: Assicurati di creare le seguenti pagine wiki:
  - Slug: `home` (homepage)
  - Slug: `nuovo` (guida per nuovi giocatori)
  - Slug: `ambientazione` (lore del gioco)
  - Slug: `regolamento` (regole)

- **Widget riutilizzabili**: I widget CHI_SIAMO, EVENTI e SOCIAL possono essere usati anche in altre pagine wiki usando i placeholder:
  - `{{WIDGET_CHI_SIAMO:0}}`
  - `{{WIDGET_EVENTI:0}}`
  - `{{WIDGET_SOCIAL:0}}`
  
  (Il numero ID è ignorato per questi widget, usa sempre 0)

- **Permessi**: Solo Staff e Master possono modificare la pagina home tramite il pulsante di modifica

---

## 🎉 Completato!

La tua homepage personalizzata è pronta! Se hai bisogno di ulteriori modifiche o personalizzazioni, non esitare a chiedere.

---

**Data implementazione**: 12 Febbraio 2026
**Versione**: 1.0
