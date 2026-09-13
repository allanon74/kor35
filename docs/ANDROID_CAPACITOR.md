# Shell Android Capacitor (KOR35)

## Obiettivo

- **PWA** = canale universale (iOS, Windows, browser) con tutte le funzioni.
- **App Android** = wrapper Capacitor della stessa PWA + bridge nativi (FCM, in futuro chiamate in arrivo / audio background).

## Stato attuale (spike)

- Progetto `frontend/android/` (appId `nativeapp.kor35.it`, nome UI **KOR35**).
- `capacitor.config.json` con `server.url` default `https://www.kor35.it` (override `CAPACITOR_SERVER_URL` per edge).
- Detection: `isNativeApp()` / `data-kor35-native`.
- Push unificato: in app → FCM; in browser → Web Push.
- Backend: `FcmDeviceToken` + `POST /api/personaggi/api/fcm/register/` + invio opzionale se `FCM_SERVER_KEY` è valorizzata.

## Prerequisiti host sviluppatore

1. Node 20+ e Android Studio (SDK recente, JDK 21).
2. Progetto Firebase con app Android `nativeapp.kor35.it`.
3. Copiare `google-services.json` in `frontend/android/app/` (gitignored).
4. In `backend/.env.<profilo>`: `FCM_SERVER_KEY=...` (legacy HTTP key; no-op se vuota).

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
