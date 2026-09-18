# Shell Android Capacitor (KOR35)

## Obiettivo

- **PWA** = canale universale (iOS, Windows, browser) con tutte le funzioni.
- **App Android** = wrapper Capacitor della stessa PWA + bridge nativi (FCM, in futuro chiamate in arrivo / audio background).

## Stato attuale (spike)

- Progetto `frontend/android/` (appId `nativeapp.kor35.it`, nome UI **KOR35**).
- `capacitor.config.json` con `server.url` default `https://www.kor35.it` (override `CAPACITOR_SERVER_URL` per edge).
- Detection: `isNativeApp()` / `data-kor35-native`.
- Push unificato: in app → FCM; in browser → Web Push.
- Backend: `FcmDeviceToken` + `POST /api/personaggi/api/fcm/register/` + invio FCM **HTTP v1** (service account).

## Prerequisiti host sviluppatore

1. Node 20+ e Android Studio (SDK recente, JDK 21).
2. Progetto Firebase con app Android `nativeapp.kor35.it`.
3. Copiare `google-services.json` in `frontend/android/app/` (gitignored).
4. Backend: **FCM HTTP v1** (non usare la Legacy API — in Console risulta *Disabilitata*).

### Firebase: Legacy disabilitata → HTTP v1

La voce **API Cloud Messaging (legacy) = Disabilitata** è normale sui progetti nuovi.
KOR35 invia le push con l’API **HTTP v1** e un **account di servizio** (non con `FCM_SERVER_KEY`).

1. Firebase Console → ⚙️ **Impostazioni progetto** → tab **Account di servizio**.
2. In Google Cloud Console abilita **Firebase Cloud Messaging API**
   (API e servizi → Libreria → cerca “Firebase Cloud Messaging API” → Abilita).
3. Nella tab Account di servizio Firebase: **Genera nuova chiave privata** → scarichi un JSON
   (`project_id`, `client_email`, `private_key`, …).
4. Sul server salva il file **fuori da git**, es. `/srv/kor35/secrets/firebase-fcm.json`
   (permessi `600`).
5. Nel `backend/.env.prod`:

```bash
FCM_SERVICE_ACCOUNT_FILE=/app/secrets/firebase-fcm.json
# opzionale se già nel JSON:
FCM_PROJECT_ID=il-tuo-project-id-firebase
# Legacy: lascia vuota
FCM_SERVER_KEY=
```

6. Monta il file nel container backend (volume read-only), es.:

```yaml
services:
  backend:
    volumes:
      - /srv/kor35/secrets/firebase-fcm.json:/app/secrets/firebase-fcm.json:ro
```

7. Riavvia il backend: `make restart-be ENV=prod`.

Nota: `google-services.json` serve all’**app** per ottenere il token sul telefono.
Il JSON del service account serve solo al **backend** per *inviare* le push.

## SSO Arcana Domine nella shell Android

Sintomo tipico: tap su «Accedi con Arcana Domine» → si apre **Chrome** e a fine login
resti nel browser invece che nell’app.

**Causa:** il dominio Arcana non era in `server.allowNavigation` di Capacitor, quindi la
WebView scaricava la navigazione al browser esterno; il callback
`https://www.kor35.it/login?arcana_ticket=…` restava in Chrome.

**Fix (già in repo):**
1. `allowNavigation` include `arcanadomine.it` / `*.arcanadomine.it` → il flusso OAuth resta in WebView.
2. Intent-filter su `/login` + schema `kor35://login` → se Chrome ha ancora il ticket, Android può riaprire l’app.
3. Bridge JS `nativeArcanaSsoBridge` gestisce `appUrlOpen` / launch URL.

Dopo il fix: `make android-sync WIN=1`, reinstalla l’APK, riprova il login SSO.
Se il dominio reale di Arcana non è `*.arcanadomine.it`, aggiungilo in
`frontend/capacitor.config.json` → `server.allowNavigation`.

## Build / sync

```bash
# dalla root monorepo (Node sull'host / in WSL, non nel container Django)
make android-sync
make android-open
```

### APK senza Android Studio (consigliato)

Un solo comando, una sola copia del progetto (`frontend/android` nel repo):

```bash
make android-apk              # debug
make android-apk RELEASE=1    # release non firmata
```

Cosa fa: verifica il JDK, installa l'SDK Android se manca (in `$ANDROID_SDK_ROOT`
o `~/android-sdk`), esegue `cap sync` + vendor plugin, poi `gradlew assembleDebug`.
In WSL copia l'APK in `C:\dev\kor35-apk\` (override con `ANDROID_APK_WIN_DIR`).

**Serve un JDK, non il solo runtime.** Con il JRE Gradle fallisce con
`Toolchain installation ... does not provide the required capabilities: [JAVA_COMPILER]`.
Lo script cerca `javac` (`JAVA_HOME`, PATH, `/usr/lib/jvm/*`) e, se manca, prova
`sudo apt install -y openjdk-21-jdk-headless` (disattivabile con
`ANDROID_APK_NO_APT=1`).

Lo stesso errore **persiste anche con il JDK installato** se Gradle ha memorizzato
le capability del JVM prima: la rilevazione resta nel demone e in
`~/.gradle/caches/<ver>/jvms`. Lo script quindi:

1. ferma i demoni (`gradlew --stop`);
2. passa `-Dorg.gradle.java.home` e disattiva l'auto-detect delle toolchain, così
   l'unico JVM candidato è il JDK trovato;
3. se il messaggio `JAVA_COMPILER` compare comunque, svuota `…/caches/*/jvms` e
   riprova una volta.

Installazione sul telefono (da PowerShell, telefono in USB debug):

```powershell
adb install -r C:\dev\kor35-apk\kor35-debug.apk
```

Oppure copia l'APK sul telefono e aprilo.

Questo evita il problema tipico del flusso con Studio: **due copie** su disco
Windows (`C:\dev\kor35-app` e `C:\dev\kor35-app\android`) e Studio ancorato a
quella sbagliata. Indizio nei log di Studio: il path in
`file:///C:/dev/kor35-app/build/reports/...` (senza `/android/`) indica che sta
compilando il parent, quindi **non** vede le modifiche sincronizzate.

### WSL + Android Studio su Windows (alternativa)

**PATH BLOCCATO — unica cartella, non cambiarla:**

```text
C:\dev\kor35-app\android
```

```bash
make android-sync WIN=1
make android-path   # stampa C:\dev\kor35-app\android
```

- Sync verso `C:/dev/kor35-app/android` = **root Gradle** (`settings.gradle`, `gradlew.bat`, `app/`, `capacitor-plugins/`).
- I plugin Capacitor sono **vendored** in `capacitor-plugins/` (niente sibling `node_modules`).
- **Non** aprire `C:\dev\kor35-android`, né il parent `C:\dev\kor35-app` (Studio: «no configuration»).
- **Non** aprire `\\wsl.localhost\...`.
- Override contenitore solo se necessario: `WIN_ANDROID_DIR='D:/altro'` → Studio resta `D:/altro/android`.
- Se Studio dice «no configuration»: cartella sbagliata (manca `settings.gradle`).

Questo clone **pinna AGP 8.10.1** (Android Studio Ladybug/Meerkat). Capacitor 8 a monte chiede 8.13.0 / Studio Otter: `make android-sync` riscrive i `build.gradle` in `node_modules/@capacitor` così Studio non rifiuta il sync.

Oppure:

```bash
cd frontend
npm ci
CAPACITOR_SERVER_URL=https://www.kor35.it npm run build
npx cap sync android
npx cap open android
```

Per puntare all’edge in evento:

```bash
CAPACITOR_SERVER_URL=http://10.42.0.1 npm run build && npx cap sync android
# oppure:
CAPACITOR_SERVER_URL=http://10.42.0.1 make android-sync WIN=1
```

## Flusso push

1. Utente in app Android: banner in Home o tab Notifiche → **Attiva** (FCM nativo).
2. Capacitor registra FCM → token salvato via `POST …/fcm/register/`.
3. `notify_user(..., category=...)` se preferenza `webpush` attiva: prova Web Push **e** FCM.

### Troubleshooting: push OK su Windows PWA, zero su Android

Sono **due canali diversi**. Windows usa Web Push (VAPID); l’APK usa **FCM**.

| Check | Dove |
|-------|------|
| `google-services.json` reale in `frontend/android/app/` al build APK | altrimenti timeout registrazione FCM |
| Service account montato su prod + `FCM_SERVICE_ACCOUNT_FILE` | altrimenti il backend non *invia* FCM (Web Push sì) |
| Riga `FcmDeviceToken` per l’utente | admin / DB dopo «Attiva» in app |
| Preferenza notifiche categoria (messaggi / chiamate) | come sulla PWA |
| Frontend deployato su `www.kor35.it` | l’APK carica la WebView remota |

Volume esempio in `compose.prod.yml` (scommentare e riavviare backend):

```yaml
- /srv/kor35/secrets/firebase-fcm.json:/app/secrets/firebase-fcm.json:ro
```

### `No matching variant of project :capacitor-status-bar` / `No variants exist`

Significa che il modulo plugin non ha prodotto varianti compatibili con `:app`.
Causa tipica: **versioni AGP diverse** tra progetto root e moduli Capacitor
(il messaggio riporta l'`AgpVersionAttr` atteso dal consumer, es. `8.10.1`).

I moduli Capacitor 8 dichiarano AGP `8.13.0` nel loro `buildscript`; se
`android/build.gradle` ne dichiara un'altra, Gradle/Studio non trova varianti.

`vendor-capacitor-android-plugins.mjs` legge l'AGP dal root e **riscrive** la
stessa versione nei moduli vendored (plugin + cordova). Per cambiare versione si
edita solo `frontend/android/build.gradle`, poi `make android-sync WIN=1`.

Verifica: `make android-doctor WIN=1` segnala se trova più di una versione AGP.
Se Android Studio è più vecchio dell'AGP richiesto, abbassa la versione nel root:
i moduli vengono riallineati automaticamente al prossimo sync.

### Solo «Add Configuration…», nessun device selector

Sintomo: la cartella si apre ma Studio non ha né modulo app né device.
Non è un problema di cartella sbagliata: **il Gradle sync di `:app` fallisce**.

Riproduzione fuori da Studio (mostra la vera causa):

```bash
cd frontend/android && ./gradlew projects
```

Deve elencare `:app` + i moduli `:capacitor-*`. Se invece dà:

```text
Could not read script '…/capacitor-cordova-android-plugins/cordova.variables.gradle'
```

manca la cartella Cordova, richiesta da `settings.gradle` e
`app/capacitor.build.gradle`. Senza `:app`, Studio non crea la run configuration.

**Catena del bug:** `app/src/main/assets/` non era in git → `npx cap sync` non
riusciva a scrivere `capacitor.plugins.json` e abortiva →
`capacitor-cordova-android-plugins/` non veniva generata (era anche gitignored).

Fix in repo: `capacitor-cordova-android-plugins/` è **versionata**,
`app/src/main/assets/.gitkeep` esiste, e `cap:sync` crea la cartella assets prima
del sync. `vendor-capacitor-android-plugins.mjs` verifica entrambe.

### Gradle OK in WSL ma Studio resta su «Add Configuration…»

Se `./gradlew projects` elenca `:app` ma Studio no, il problema è il **modello di
progetto salvato da Studio**: dopo un import fallito resta un `.idea` non
collegato a Gradle (senza `.idea/gradle.xml`) e riaprendo la cartella Studio
**non ritenta** l'import.

```bash
make android-reset-studio WIN=1   # chiudi prima il progetto in Studio
```

Poi in Studio: **Open** → `C:\dev\kor35-app\android` → *Trust Project* → attendi il
Gradle sync. `make android-sync WIN=1` rileva e rimuove da sé un `.idea` rotto.

File per-macchina che il mirror **non** deve toccare:

| File | Serve per |
|---|---|
| `local.properties` (`sdk.dir`) | senza → `SDK location not found`, nessuna run config |
| `.idea/` | run configurations di Studio |

`make android-sync WIN=1` esclude `.idea/`, `.gradle/`, `build/` e
`local.properties` dal mirror e crea `local.properties` con `sdk.dir`.

Verifica: `make android-doctor WIN=1`.

### Status bar: header sotto la barra notifiche

Sintomo: UI / pulsanti in alto sotto la status bar Android (non tappabili).

**Causa:** con `targetSdk` ≥ 35 Android forza edge-to-edge. `StatusBar.setOverlaysWebView(false)`
è un no-op e `env(safe-area-inset-top)` nella WebView Android resta 0.

**Come lo risolviamo (senza strisce vuote):** l'inset sta **dentro la pagina**, non
come padding nativo della WebView.

1. `capacitor.config.json` → `SystemBars.insetsHandling: "css"`: il plugin core
   inietta `--safe-area-inset-top/right/bottom/left` (px reali) nella pagina.
2. `index.css` → `--kor-safe-top: var(--safe-area-inset-top, env(safe-area-inset-top, 0px))`.
3. La UI usa quel valore: `.kor-app-header` (header MainPage), `.kor-safe-header`
   (header ad altezza fissa) e `.kor-safe-shell` (pagine senza header: Start, Login).

Così l'area della status bar è coperta dallo **sfondo dell'header/shell**: niente
banda vuota, niente contenuto sotto le icone di sistema.

**Da non fare:** padding nativo (`WindowInsets` sul layout bridge) o
`EdgeToEdge.enable` in `MainActivity`. Sposta l'intera WebView e lascia una
striscia vuota che mostra il window background (con il tema di lancio, la splash
**bianca**). `MainActivity` fa solo `setTheme(AppTheme.NoActionBar)`, colori barre
e fondo scuro.

Serve **deploy frontend** (CSS/JS) + **nuovo APK** (config Capacitor + tema).

### Tap notifica: non fa nulla

Cause tipiche:
1. FCM con `click_action` custom senza intent-filter → Android non apre MainActivity.
2. Handler JS gestiva solo chiamate (`call_id`), non i messaggi.

Fix: niente `click_action` custom in FCM v1 + handler che apre Messaggi per ogni tap + intent-filter compat `OPEN_KOR35_PUSH`.

Serve **deploy backend** (payload FCM) + **deploy frontend** (handler) + **nuovo APK** (intent-filter).

### Gradle: `No variants` / `:capacitor-status-bar` / «no configuration»

Causa tipica: Android Studio apre una cartella senza `settings.gradle`/`gradlew`, oppure un sync
vecchio che punta a `../node_modules` assente.

1. Da WSL (repo aggiornato su questo branch): `make android-sync WIN=1`
2. Chiudi tutti i progetti Android Studio vecchi.
3. **File → Open** solo `C:\dev\kor35-app\android` (deve avere `gradlew.bat` + `capacitor-plugins\`).
4. Non aprire `C:\dev\kor35-app` (parent) né `C:\dev\kor35-android`.
5. Verifica file: `C:\dev\kor35-app\android\capacitor-plugins\capacitor-status-bar\build.gradle`

## Chiamate in arrivo (shell Android)

- Push FCM/webpush per `category=chiamate` include `call_id`, `action` (`VOCE_INVITO` / `VOCE_PERSA`) e URL `/?tab=messaggi&call={call_id}&voce={voce_action}`.
- Canale Android `kor35_incoming_calls` (IMPORTANCE_HIGH) creato in `MainActivity` (più `kor35_default` per il resto).
- Bridge JS `nativeIncomingCallBridge` + `callDeepLink`: tap notifica / resume app → `kor35:voce-wake` → refresh chiamata ringing.
- ConnectionService Telecom / fullscreen intent nativo / foreground service audio WebRTC: ancora da fare.

## Prossimi passi

- Notifica full-screen Intent / ConnectionService (Telecom) per lockscreen.
- Foreground service microfono durante WebRTC.
- CI che pubblica AAB su Play Internal testing.

## Documentazione agenti

Vedi `.cursor/rules/android-capacitor.mdc`, sezione in `.cursorrules` e `AGENTS.md`.
