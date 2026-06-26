# Eventi viaggio — ST / SP / CA

Catalogo degli **eventi randomici** sulla console pilota: condizioni di risoluzione e effetti **Catastrofe (CA)**.

Aggiorna il catalogo eventi in **Dashboard staff → Pilotaggio → Eventi**, poi esegui `make wiki-staff-sync ENV=dev-home WIKI_STAFF_FORCE=1` per riflettere l'elenco in fondo a questa pagina.

---

## Ciclo di vita di un evento

1. Il motore sorteggia un evento dal pool **attivo** (peso `peso_random`, probabilità DEFCON in *Stati allerta*).
2. Parte il **countdown in tick**: ogni tick dura `tempo_risoluzione_secondi` del DEFCON corrente (non l'intervallo runtime standard).
3. Dopo il **tempo di reazione** iniziale, a ogni tick il motore valuta le condizioni **ST**, poi **SP**, poi **CA** (in quest'ordine).
4. Se nessuna condizione è vera allo scadere dei tick:
   - con **scadenza critica** → applica `ca_effetto` (Catastrofe);
   - altrimenti → l'evento termina senza penalità DEFCON.

---

## Esiti ST / SP / CA

| Esito | Significato | Effetto tipico |
|-------|-------------|----------------|
| **ST** (soluzione totale) | Configurazione sottosistemi soddisfa la formula ST | Evento chiuso, **DEFCON −1** |
| **SP** (soluzione parziale) | Formula SP vera, ST no | Evento **prosegue**, DEFCON invariato |
| **CA** (condizione critica) | Formula CA vera (dopo il periodo di reazione) | Applica **`ca_effetto`** |

Le condizioni usano il **composer** in modifica evento: sottosistema (codice 1 char), operatore (`>`, `<`, `=`, `between`, `direction`, stati booleani…), formula con parentesi es. `(1 AND 2) OR 3`.

### Effetto Catastrofe (`ca_effetto`)

Configurato nel pannello **Effetto esito CA** (o in `regole_json.ca_effetto`):

| Tipo | Comportamento |
|------|----------------|
| `precipizio` | Nave precipita (default) |
| `guasto_sottosistema` | Guasto forzato su un sottosistema (per id/codice) |
| `guasto_sottosistemi` | Guasto su **tutti** i sottosistemi scelti, oppure **N random** da elenco o da tutti quelli online |

**Nota:** al **primo** check CA con tipo `precipizio`, il motore applica una penalità DEFCON (+1) come periodo di grazia — non precipita immediatamente.

### Codici legacy (3 caratteri)

Paralleli alle regole JSON, ancora supportati:

- `codice_soluzione_esatta` — equivale a risoluzione immediata (ST legacy)
- `codici_soluzione_parziale` — pattern con jolly `_` o intervallo terza cifra `XY(4-9)` → SP
- `codici_precipizio` — pattern che causano precipizio immediato

---

## Campi utili in catalogo

| Campo | Descrizione |
|-------|-------------|
| Durata tick | `N` o `A–B` tick (secondi ≈ tick × durata DEFCON) |
| Scadenza CA | Se attiva, allo scadere tick senza ST applica `ca_effetto` |
| Sottosistema | Collegamento opzionale per guasti/eventi mirati |
| Peso random | Frequenza relativa nel sorteggio |

---
