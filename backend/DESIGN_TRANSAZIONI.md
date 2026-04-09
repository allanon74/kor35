# Design Sistema Transazioni Avanzato

## Obiettivo
Implementare un sistema completo di transazioni tra personaggi con:
- Proposte iniziali (crediti + oggetti + messaggio)
- Controproposte
- Rilanci/modifiche
- Accettazione finale che concretizza entrambe le proposte

## Modello Dati Backend

### 1. TransazioneSospesa (Modificato)
```python
class TransazioneSospesa(models.Model):
    # Parti coinvolte
    iniziatore = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="transazioni_iniziate")
    destinatario = models.ForeignKey(Personaggio, on_delete=models.CASCADE, related_name="transazioni_ricevute")
    
    # Stato
    stato = models.CharField(max_length=20, choices=[
        ('IN_ATTESA', 'In Attesa'),
        ('ACCETTATA', 'Accettata'),
        ('RIFIUTATA', 'Rifiutata'),
        ('CHIUSA', 'Chiusa'),  # Chiusa senza accordo
    ], default='IN_ATTESA')
    
    # Timestamps
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_ultima_modifica = models.DateTimeField(auto_now=True)
    data_chiusura = models.DateTimeField(null=True, blank=True)
    
    # Ultima proposta attiva (per performance)
    ultima_proposta_iniziatore = models.ForeignKey('PropostaTransazione', 
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transazione_iniziatore_attiva')
    ultima_proposta_destinatario = models.ForeignKey('PropostaTransazione',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transazione_destinatario_attiva')
    
    class Meta:
        ordering = ['-data_ultima_modifica']
```

### 2. PropostaTransazione (Nuovo)
```python
class PropostaTransazione(models.Model):
    transazione = models.ForeignKey(TransazioneSospesa, on_delete=models.CASCADE, 
        related_name='proposte')
    autore = models.ForeignKey(Personaggio, on_delete=models.CASCADE)
    
    # Cosa l'autore DÀ
    crediti_da_dare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    oggetti_da_dare = models.ManyToManyField('Oggetto', related_name='proposte_oggetti_dati', blank=True)
    
    # Cosa l'autore RICEVE
    crediti_da_ricevere = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    oggetti_da_ricevere = models.ManyToManyField('Oggetto', related_name='proposte_oggetti_ricevuti', blank=True)
    
    # Messaggio
    messaggio = models.TextField(blank=True)
    
    # Timestamp
    data_creazione = models.DateTimeField(auto_now_add=True)
    is_attiva = models.BooleanField(default=True)  # Solo l'ultima proposta per autore è attiva
    
    class Meta:
        ordering = ['-data_creazione']
        indexes = [
            models.Index(fields=['transazione', 'autore', 'is_attiva']),
        ]
```

## Flusso Operativo

### 1. Creazione Transazione (Scansione QR)
```
Utente A scansiona QR di Utente B
→ Crea TransazioneSospesa (iniziatore=A, destinatario=B, stato=IN_ATTESA)
→ Crea PropostaTransazione iniziale (autore=A, is_attiva=True)
```

### 2. Visualizzazione Transazione
```
Utente B vede transazione in "In Entrata"
→ Può vedere proposta di A
→ Può: ACCETTA, RIFIUTA, CONTROPROPONI
```

### 3. Controproposta
```
Utente B crea PropostaTransazione (autore=B, is_attiva=True)
→ Disattiva proposta precedente di B (se esiste)
→ Aggiorna ultima_proposta_destinatario su TransazioneSospesa
```

### 4. Rilancio
```
Utente A vede controproposta di B
→ Può: ACCETTA, RIFIUTA, RILANCIA
→ Se rilancio: crea nuova PropostaTransazione (autore=A, is_attiva=True)
→ Disattiva proposta precedente di A
```

### 5. Accettazione
```
Quando una parte ACCETTA:
→ Verifica che entrambe le parti abbiano una proposta attiva
→ Esegue gli scambi:
  - Trasferisce crediti_da_dare di A → crediti_da_ricevere di B
  - Trasferisce crediti_da_dare di B → crediti_da_ricevere di A
  - Sposta oggetti_da_dare di A → inventario di B
  - Sposta oggetti_da_dare di B → inventario di A
→ Stato transazione = ACCETTATA
→ Crea movimenti credito per audit
```

### 6. Rifiuto/Chiusura
```
Se una parte RIFIUTA:
→ Stato transazione = RIFIUTATA o CHIUSA
→ Nessuno scambio avviene
```

## API Endpoints

### GET /api/transazioni/
Lista transazioni (entrata/uscita) con proposte attive

### GET /api/transazioni/<id>/
Dettaglio transazione con tutte le proposte

### POST /api/transazioni/
Crea nuova transazione con proposta iniziale
```json
{
  "destinatario_id": 123,
  "proposta": {
    "crediti_da_dare": 100,
    "crediti_da_ricevere": 50,
    "oggetti_da_dare": [1, 2],
    "oggetti_da_ricevere": [3],
    "messaggio": "Ti propongo questo scambio..."
  }
}
```

### POST /api/transazioni/<id>/proposta/
Aggiungi controproposta o rilancio
```json
{
  "crediti_da_dare": 80,
  "crediti_da_ricevere": 60,
  "oggetti_da_dare": [4],
  "oggetti_da_ricevere": [1, 2],
  "messaggio": "Controproposta: ..."
}
```

### POST /api/transazioni/<id>/accetta/
Accetta la transazione (esegue scambi)

### POST /api/transazioni/<id>/rifiuta/
Rifiuta la transazione

## Frontend - Componenti

### TransazioniViewer (Modificato)
- Mostra lista transazioni con stato
- Click su transazione → apre TransazioneDetailModal

### TransazioneDetailModal (Nuovo)
- Mostra proposte attive di entrambe le parti
- Storico proposte
- Azioni: Accetta, Rifiuta, Controproponi/Rilancio

### PropostaEditorModal (Nuovo)
- Form per creare/modificare proposta
- Selezione oggetti da dare/ricevere
- Input crediti
- Textarea messaggio

## Migrazione Dati

1. Creare migrazione per nuovi campi in TransazioneSospesa
2. Creare modello PropostaTransazione
3. Migrare dati esistenti:
   - Ogni TransazioneSospesa esistente → crea PropostaTransazione iniziale
   - iniziatore = richiedente (vecchio campo)
   - destinatario = mittente.personaggio (da inventario)

## Note Implementative

- Validazione: verificare che oggetti siano nell'inventario corretto
- Atomicità: usare transaction.atomic() per accettazione
- Notifiche: inviare messaggio quando nuova proposta/accettazione
- Performance: usare select_related/prefetch_related per query ottimizzate
