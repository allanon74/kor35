# Console Scientifica — utilizzo

La **Console Scientifica** è il laboratorio di bordo. Non fa partire il volo e non pilota la nave: legge la sessione aperta dalla **console di navigazione** e interviene sul fenomeno in corso (eventi ST / SP / CA).

Si aggiorna da sola circa ogni 4 secondi.

---

## Dove si apre

| Postazione | Percorso |
|------------|----------|
| Browser / PC | `/pilot/?screen=scientifica` |
| Pi 7" 800×480 | pulsante **Scientifica** sulla pagina di scelta (`/pilot/?screen=station&viewport=800x480`) |

Schede: **Spettro**, **Scan**, **Matrice**, **Interventi**. Su schermo piccolo sono quattro linguette; **Logout** torna alla scelta stazione.

Installazione del Raspberry: pagina **Console stazione — kiosk 800×480**.

---

## Accensione (staff)

**Dashboard staff → Pilotaggio → Runtime console di bordo.** Le modifiche valgono solo dopo **Salva runtime**.

1. Nel riquadro **Statistiche navigazione**, riga **Console Scientifica**: sigla (default `0SC`), requisito `> 0`. La statistica deve esistere in admin Django (app personaggi).
2. Nel riquadro **Console Scientifica**:
   - **Abilita console** (`/pilot/?screen=scientifica`)
   - **Login richiesto** (QR; se spento, l'accesso dopo il pulsante è automatico)
   - **Scan profondo** e **Max scan profondi per volo** (default 2)
   - **Matrice R/S/T e interventi attivi**
   - cap coerenza (default 24), livello minimo R/S/T (default 1), max interventi per volo (default 12)
   - energia per +1 coerenza (default 4), carica richiesta (default 100), carica guadagnata × energia/tick (default 5)
3. Sul server la feature console deve essere accesa (`PILOT_CONSOLE_ENABLED`). Se è spenta, `enabled` resta falso anche con la checkbox attiva.

Il QR della stazione usa **questa** sigla. Un personaggio con solo navigazione (`0PI`) o solo ingegneria (`0IN`) non sblocca la scientifica.

---

## Login del giocatore

Con **Login richiesto** spento l'accesso è automatico, come in ingegneria: la sigla non viene controllata.

Con **Login richiesto** attivo, la console mostra un QR. Lo smartphone deve essere già nell'app, con un personaggio la cui statistica (sigla staff, default `0SC`) è maggiore di 0. Creare la statistica in admin non basta: sul personaggio, in **Statistiche base**, il valore deve essere sopra 0. Il claim è un ticket di ruolo `scientifica`: non vale il ticket della plancia di navigazione.

A fine volo coerenza, fasi della matrice e carica si azzerano.

---

## Cosa mostra l'HUD

| Stato | Significato |
|-------|-------------|
| Console spenta | Checkbox staff spenta, oppure feature console disattivata sul server |
| Nessun volo | La navigazione non ha una sessione attiva |
| In attesa di fenomeno | Volo in corso, nessun evento pending |
| Fenomeno attivo | Nome evento, firma, countdown, DEFCON |

---

## Spettro

La scheda **Spettro** è utile solo con un evento in corso (`pending`). Mostra nome del fenomeno, firma spettrale, delta di navigazione, stato della soluzione e rischio CA, con il countdown a tick.

Lo scienziato legge il fenomeno e lo comunica al pilota. Non risolve da solo le formule ST/SP: quelle restano sulla configurazione dei sottosistemi (vedi **Pilotaggio — eventi ST/SP/CA**).

---

## Scan profondo

Consuma **1 componente di stiva** (o i requisiti in `scientifica_scan_requisiti_json`; lista vuota = 1 unità qualsiasi).

| Vincolo | Default |
|---------|---------|
| Una volta per evento | sì |
| Massimo per volo | 2 (`scientifica_scan_max_per_volo`) |
| Serve un evento pending | sì |

Rivela il **primo indizio SP o ST non ancora soddisfatto**. Se non resta nulla da rivelare, lo scan viene rifiutato e il componente non si consuma. Se lo scan su quell'evento è già stato fatto, o il tetto di volo è pieno, il pulsante non parte.

---

## Matrice R / S / T

Lo scienziato imposta la **fase** di ogni nucleo: 0, 1 o 2. Il pilota tiene online i tre sottosistemi esotici e ci manda energia.

| Codice | Sottosistema |
|--------|----------------|
| **R** | Nucleo Temporale |
| **S** | Nucleo Dimensionale |
| **T** | Correttore Paradossi |

A ogni tick del volo, se l'energia combinata dei tre è almeno la soglia, sale la **coerenza di campo**:

- soglia ≈ livello minimo × (1,8 + 1,9 + 2,1). Con livello minimo 1 servono circa **5,8** di energia/tick (i tre nuclei almeno a livello 1 e online);
- guadagno ≈ energia / `scientifica_energia_per_coerenza` (default **4**), almeno +1 se la soglia è superata;
- se tutte e tre le fasi sono a **2** e gli esotici alimentano, **+1 coerenza** in più;
- tetto default **24**.

In parallelo sale la **carica intervento** (default +5 punti per ogni unità di energia/tick, fino alla soglia, default **100**). Senza carica piena i quattro interventi a pagamento restano bloccati. Il **Reset risonanza** non chiede carica.

---

## Interventi

Scheda **Interventi**. I primi quattro spendono coerenza, azzerano la carica appena usata e contano nel tetto di volo (default **12**). Servono un volo attivo e un evento pending.

| Intervento | Effetto | Coerenza | Componenti | Limite |
|------------|---------|----------|------------|--------|
| Dilatazione temporale | +1 tick rimanente | 8 | 1 | 2 per evento |
| Gabbia dimensionale | La prossima valutazione CA non scatta | 10 | 2 | 1 per evento |
| Correzione paradosso | DEFCON −1, l'evento **non** si chiude | 12 | 1 | 1 per evento |
| Eco parziale | La prossima valutazione SP non consuma un tick | 6 | 0 | 1 per evento |
| Reset risonanza | Fasi R/S/T a 0 | 0 | 0 | libero, non conta nel tetto di volo, anche senza evento |

I componenti, se richiesti, escono dalla stiva (override per tipo in `scientifica_interventi_requisiti_json`). La dilatazione non si applica a un evento a durata infinita. Coerenza insufficiente, gabbia già armata, correzione già usata o eco già attiva: il pulsante resta spento e indica il motivo.

---

## In gioco, in breve

1. Il pilota apre il volo sulla console di navigazione.
2. Lo scienziato entra con il QR (`0SC > 0`, o la sigla che avete salvato).
3. Con i nuclei R/S/T online, alza le fasi e accumula coerenza e carica.
4. All'evento: legge lo **Spettro**, eventualmente uno **Scan** per un indizio ST/SP, poi un **Intervento** se serve tempo, bloccare la CA, abbassare il DEFCON o non bruciare un tick sulla SP.
5. A fine volo il laboratorio si azzera.

---

## Vedi anche

- **Pilotaggio — eventi ST/SP/CA** — cosa significano ST, SP e l'effetto CA
- **Console stazione — kiosk 800×480** — Pi touch, WiFi `kor35-larp`, installazione
