# Istruzioni per applicare le modifiche

## 1. Creare la migration

Connettiti al server remoto ed esegui:

```bash
cd /home/django/progetti/kor35
source venv/bin/activate  # o il path al tuo virtualenv
python manage.py makemigrations personaggi
python manage.py migrate personaggi
```

## 2. Riavviare il server

```bash
sudo systemctl restart gunicorn
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

Quando un personaggio equipaggia un'arma con formula tipo `"{rango|:RANGO}{molt|:MOLT}Chop!"`:

1. Il sistema cerca `rango` e `molt` nelle `statistiche_base` dell'oggetto
2. Se `valore_base=0`, usa `valore_base_predefinito` della statistica (es. 1)
3. Cerca nel `statistiche_base_dict` del personaggio
4. Se non esiste il record per quel personaggio+statistica, lo crea automaticamente con `valore_base_predefinito`
5. Applica i modificatori del personaggio
6. Renderizza la formula

**Risultato**: Un personaggio nuovo senza abilità ora avrà correttamente `rango=1` e `molt=1` (dai valori predefiniti) invece di 0.
