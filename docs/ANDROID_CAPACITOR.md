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

### WSL + Android Studio su Windows (consigliato)

Gradle non può usare il JDK Windows se il progetto sta su `\\wsl.localhost\...`.
Dopo il sync, copia su disco Windows nativo:

```bash
make android-sync WIN=1
# destinazione default: C:/dev/kor35-android  (è la cartella da aprire in Studio)
# IMPORTANTE: usa slash avanti, non c:\\dev\\... (bash mangia i backslash)
# personalizza:
make android-sync WIN=1 WIN_ANDROID_DIR='D:/android/kor35'
```

Poi in Android Studio: **File → Open** → `C:\dev\kor35-android`
(lo script copia `node_modules/@capacitor/*` *dentro* quella cartella). Non aprire `C:\dev\kor35-app` né `\\wsl.localhost\...`.

Se Gradle dice *No matching variant / No variants exist* sui moduli `:capacitor-*`, stai aprendo la copia sbagliata (senza quei pacchetti). Chiudi il progetto, ri-esegui `make android-sync WIN=1`, apri di nuovo `C:\dev\kor35-android` e fai **Sync Project with Gradle Files**.

Questo clone **pinnà AGP 8.10.1** (Android Studio Ladybug/Meerkat). Capacitor 8 a monte chiede 8.13.0 / Studio Otter: `make android-sync` riscrive i `build.gradle` in `node_modules/@capacitor` così Studio non rifiuta il sync.

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

1. Utente in app Android apre Notifiche → “Attiva su questo dispositivo”.
2. Capacitor registra FCM → token salvato via API autenticata.
3. `notify_user(..., category=...)` se preferenza `webpush` attiva: prova Web Push **e** FCM.

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
