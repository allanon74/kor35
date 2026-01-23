# Istruzioni per applicare le modifiche

## 1. Creare le migration

Connettiti al server remoto ed esegui:

```bash
cd /home/django/progetti/kor35
source venv/bin/activate  # o il path al tuo virtualenv

# Migration per personaggi (PersonaggioStatisticaBase)
python manage.py makemigrations personaggi
python manage.py migrate personaggi

# Migration per gestione_plot (QuestVista con nuovi campi)
python manage.py makemigrations gestione_plot
python manage.py migrate gestione_plot
```

## 2. Inizializzare le statistiche base per i personaggi esistenti (PREGRESSO)

Dopo aver applicato la migration, esegui il management command per sistemare i personaggi già esistenti:

```bash
python manage.py inizializza_statistiche_base
```

Questo creerà automaticamente i record `PersonaggioStatisticaBase` per tutti i personaggi esistenti, usando i `valore_base_predefinito` di ogni statistica.

**Opzioni disponibili:**
- `--force`: Sovrascrive anche i valori già esistenti con i valori predefiniti (usa con cautela!)

## 3. Riavviare il server (e controllare eventuali errori)

```bash
sudo systemctl restart gunicorn
sudo systemctl status gunicorn  # Verifica che sia tutto ok
```

**NOTA**: Se usi altri server (es. Daphne per WebSocket), ricorda di riavviarli:
```bash
sudo systemctl restart daphne  # Se applicabile
```

## 3. Cosa è stato modificato

### Nuovi modelli:
- **PersonaggioStatisticaBase**: Modello per memorizzare i valori base delle statistiche per ogni personaggio

### Modifiche al modello Personaggio:
- Aggiunto campo `statistiche_base` (ManyToMany con Statistica attraverso PersonaggioStatisticaBase)
- Aggiunto metodo `get_valore_statistica_base(statistica)`: recupera/crea automaticamente il valore base
- Aggiunta property `statistiche_base_dict`: restituisce dizionario {parametro: valore} con auto-inizializzazione

### Modifiche alla logica:
- `formatta_testo_generico` ora usa `statistiche_base_dict` del personaggio
- I valori base delle statistiche vengono inizializzati automaticamente con `valore_base_predefinito` quando mancanti
- Questo risolve il problema dei personaggi nuovi che non avevano valori per `rango`, `molt`, etc.

### Modifiche all'admin:
- Aggiunto `PersonaggioStatisticaBaseInline` per gestire le statistiche base dall'admin Django

## 4. Come funziona

### Inizializzazione automatica (nuovi personaggi):
Quando viene creato un nuovo personaggio, un **signal Django** (`post_save`) crea automaticamente tutti i record `PersonaggioStatisticaBase` per ogni statistica esistente, inizializzandoli con `valore_base_predefinito`.

### Lazy initialization (fallback per il pregresso):
Se il record non esiste (personaggi vecchi prima della migration), il metodo `get_valore_statistica_base()` lo crea al volo quando richiesto.

### Formattazione formule:
Quando un personaggio equipaggia un'arma con formula tipo `"{rango|:RANGO}{molt|:MOLT}Chop!"`:

1. Il sistema cerca `rango` e `molt` nelle `statistiche_base` dell'oggetto
2. Se `valore_base=0`, usa `valore_base_predefinito` della statistica (es. 1)
3. Cerca nel `statistiche_base_dict` del personaggio (valori intrinseci)
4. Aggiunge le `caratteristiche_base` del personaggio (da abilità)
5. Applica i modificatori del personaggio
6. Renderizza la formula

**Risultato**: 
- Un personaggio nuovo senza abilità ha `rango=1` e `molt=1` (dai valori predefiniti) 
- Formula renderizzata: **"Chop!"** (perché 1 viene sottinteso)
- Un personaggio con abilità che modificano `rango` vedrà il valore modificato applicato

## 5. Verifiche post-migrazione

Dopo aver completato i passi 1-3, verifica:

1. **Admin Django**: Vai su un personaggio e verifica che veda il nuovo inline "Statistiche Base Personaggio"
2. **Test arma base**: Equipaggia un'arma base su un personaggio nuovo senza abilità e verifica che i valori siano corretti
3. **Console**: Controlla i log per eventuali errori durante l'inizializzazione
