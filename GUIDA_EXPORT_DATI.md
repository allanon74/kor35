# Guida: Esportazione Dati per Istruzioni

Questa guida spiega come esportare dati reali dal database per generare istruzioni accurate.

## 🚀 Passaggi

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

```bash
source ~/ambienti/kor35/bin/activate
# oppure
source venv/bin/activate
```

### 4. Esegui l'Export

**Opzione Base** (3 record per tipo):
```bash
python manage.py esporta_dati_esempio
```

**Opzione Personalizzata** (più record):
```bash
python manage.py esporta_dati_esempio --limit 5 --output dati_esempio.json
```

**Opzione Completa** (tutti i punteggi):
```bash
python manage.py esporta_dati_esempio --limit 5 --include-all-punteggi
```

### 5. Verifica il File Creato

```bash
ls -lh dati_esempio.json
cat dati_esempio.json | head -50  # Anteprima
```

### 6. Scarica il File sul Tuo Computer

```bash
# Dal tuo computer locale
scp tuo_utente@server_kor35.it:~/progetti/kor35/dati_esempio.json ./
```

## 📊 Cosa Viene Esportato

Il file JSON contiene:

- **punteggi**: Tutti i punteggi disponibili (ST, CA, AU) con nomi, colori, icone
- **statistiche**: Tutte le statistiche con valori predefiniti
- **classi_oggetto**: Classi di oggetti disponibili
- **tipologie_personaggio**: Tipologie di personaggio
- **personaggi**: Esempi di personaggi con:
  - Crediti e Punti Caratteristica
  - Statistiche base
  - Punteggi base
  - Conteggi abilità/infusioni/tessiture
- **oggetti**: Esempi di oggetti con:
  - Tipo oggetto
  - Slot corpo
  - Cariche
  - Statistiche base
- **abilita**: Esempi di abilità con:
  - Costi (PC, Crediti)
  - Statistiche modificate
  - Punteggi associati
- **infusioni**: Esempi con livelli, costi, effetti
- **tessiture**: Esempi con livelli, costi, aura richiesta
- **metadata**: Riepilogo e tipi/slot realmente utilizzati

## 🔍 Analisi del File

Puoi analizzare il file per vedere:
- Quali statistiche sono realmente usate
- Quali tipi di oggetti esistono
- Quali slot corporei sono utilizzati
- Costi reali di abilità/infusioni/tessiture
- Esempi concreti dal database

## ⚠️ Note

- Il file può essere grande (dipende da `--limit`)
- Non contiene dati sensibili (password, etc.)
- Puoi condividerlo per analisi
- Usa `--limit` basso (3-5) per file più piccoli

## 📝 Prossimi Passi

Dopo l'export, puoi:

1. **Condividere il file** per analisi e generazione istruzioni accurate
2. **Usare `genera_istruzioni_da_dati.py`** per generare automaticamente le pagine:
   ```bash
   python manage.py genera_istruzioni_da_dati --input dati_esempio.json --force
   ```
3. **Analizzare manualmente** il JSON per capire la struttura reale

## 🐛 Risoluzione Problemi

### Errore: "ModuleNotFoundError"
- Verifica che l'ambiente virtuale sia attivato
- Controlla che tutti i modelli siano importabili

### Errore: "Field does not exist"
- Potrebbe essere un campo che non esiste nel modello
- Controlla i log per vedere quale campo manca

### File troppo grande
- Riduci `--limit` a 2 o 3
- Rimuovi `--include-all-punteggi` se non necessario
