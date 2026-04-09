# Guida: Generazione Pagine di Istruzione

Questa guida spiega come generare le pagine di istruzione per l'app Kor35 dopo il deploy.

## 📋 Prerequisiti

- Accesso SSH al server remoto
- Permessi per eseguire comandi Django
- Ambiente virtuale attivato

## 🚀 Passaggi da Seguire

### 1. Connettiti al Server Remoto

```bash
ssh tuo_utente@server_kor35.it
```

### 2. Vai nella Directory del Progetto

```bash
cd ~/progetti/kor35
# oppure
cd /home/django/progetti/kor35
```

### 3. Attiva l'Ambiente Virtuale

**Opzione A** (se l'ambiente è in `~/ambienti/kor35`):
```bash
source ~/ambienti/kor35/bin/activate
```

**Opzione B** (se l'ambiente è in `venv` nella directory del progetto):
```bash
source venv/bin/activate
```

**Opzione C** (se l'ambiente è in un'altra posizione):
```bash
source /percorso/completo/al/virtualenv/bin/activate
```

### 4. Verifica che lo Script sia Presente

```bash
ls -la gestione_plot/management/commands/genera_pagine_istruzioni.py
```

Dovresti vedere il file. Se non c'è, assicurati di aver fatto il pull delle ultime modifiche:
```bash
git pull origin main
```

### 5. Esegui lo Script

**Opzione Base** (crea le pagine se non esistono):
```bash
python manage.py genera_pagine_istruzioni
```

**Opzione con Forza** (sovrascrive pagine esistenti):
```bash
python manage.py genera_pagine_istruzioni --force
```

**Opzione Personalizzata** (nome utente e password personalizzati):
```bash
python manage.py genera_pagine_istruzioni \
    --utente-sistema mio_utente_sistema \
    --password mia_password_sicura
```

### 6. Salva le Credenziali dell'Utente Sistema

⚠️ **IMPORTANTE**: Lo script genererà una password casuale per l'utente di sistema. 
**SALVA QUESTA PASSWORD** in un luogo sicuro (password manager, file cifrato, etc.)

Esempio di output:
```
✓ Utente di sistema "kor35_system" creato
  Password: xK9mP2qR7vT4wY8zA1bC3dE5fG6hI0j
  ⚠️ Salva questa password in un luogo sicuro!
```

### 7. Verifica le Pagine Create

Puoi verificare che le pagine siano state create in due modi:

**A) Tramite Admin Django:**
1. Vai su `https://www.kor35.it/admin`
2. Accedi con un account staff
3. Vai su "Gestione Plot" → "Pagine Regolamento"
4. Dovresti vedere le 8 pagine create

**B) Tramite l'App:**
1. Vai su `https://app.kor35.it/regolamento/guida-utilizzo-app`
2. Dovresti vedere la pagina principale con l'indice

### 8. (Opzionale) Riavvia i Servizi

Se necessario, riavvia i servizi:
```bash
# Riavvia Apache
sudo systemctl restart apache2.service

# Riavvia Daphne (per WebSocket)
sudo systemctl restart kor35-daphne
```

## 📄 Pagine Create

Lo script crea le seguenti pagine:

1. **Guida all'utilizzo dell'App** (`guida-utilizzo-app`) - Pagina principale con indice
2. **Primo Accesso** (`primo-accesso`) - Come registrarsi e accedere
3. **Navigazione nell'App** (`navigazione-app`) - Struttura dell'interfaccia
4. **Gestione del Personaggio** (`gestione-personaggio`) - Statistiche, abilità, infusioni
5. **Inventario e Oggetti** (`inventario-oggetti`) - Gestione oggetti e equipaggiamento
6. **Messaggi e Comunicazione** (`messaggi-comunicazione`) - Sistema di messaggistica
7. **Quest e Missioni** (`quest-missioni`) - Come funzionano le quest
8. **Area Amministrazione** (`amministrazione`) - Guida per lo staff (visibile solo a staff)

## 🔧 Utilizzo dell'Utente Sistema

L'utente di sistema creato (`kor35_system` di default) può essere usato per:

- **Gestione via Admin**: Accedi a `https://www.kor35.it/admin` e modifica le pagine
- **Autenticazione API**: Usa il token per modifiche programmatiche
- **Operazioni di Manutenzione**: Script automatici, backup, etc.

### Ottenere il Token API per l'Utente Sistema

Se vuoi usare l'utente di sistema per chiamate API:

```bash
python manage.py shell
```

Poi nel shell Python:
```python
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
user = User.objects.get(username='kor35_system')
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
```

## 🐛 Risoluzione Problemi

### Errore: "Command not found"
- Verifica di essere nella directory corretta (`~/progetti/kor35`)
- Verifica che l'ambiente virtuale sia attivato
- Controlla che il file esista: `ls gestione_plot/management/commands/`

### Errore: "ModuleNotFoundError: No module named 'django'"
- L'ambiente virtuale non è attivato correttamente
- Verifica il percorso: `which python` dovrebbe puntare al virtualenv
- Riactiva l'ambiente virtuale

### Errore: "Permission denied"
- Verifica i permessi sulla directory del progetto
- Potrebbe essere necessario eseguire con l'utente corretto

### Le pagine non appaiono nell'app
- Verifica che siano marcate come `public=True`
- Controlla i log del server per errori
- Prova a ricaricare la pagina con cache pulita (Ctrl+F5)

## 📝 Note Aggiuntive

- Le pagine sono organizzate gerarchicamente (la pagina principale è parent delle altre)
- La pagina "Area Amministrazione" è visibile solo allo staff (`visibile_solo_staff=True`)
- Puoi modificare le pagine in qualsiasi momento tramite l'admin Django
- Lo script può essere eseguito più volte: usa `--force` solo se vuoi sovrascrivere modifiche esistenti

## 🔄 Aggiornare le Pagine

Se vuoi aggiornare le pagine in futuro:

```bash
cd ~/progetti/kor35
source ~/ambienti/kor35/bin/activate  # o il tuo percorso
python manage.py genera_pagine_istruzioni --force
```

Questo sovrascriverà tutte le pagine con i contenuti aggiornati.
