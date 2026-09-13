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
# destinazione default: C:/dev/kor35-android
# IMPORTANTE: usa slash avanti, non c:\\dev\\... (bash mangia i backslash)
# personalizza:
make android-sync WIN=1 WIN_ANDROID_DIR='D:/android/kor35'
```

Poi in Android Studio: **Open** → `C:/dev/kor35-android` (o `C:\\dev\\kor35-android` in Esplora risorse) (non il path `\\wsl.localhost\...`).

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

## Prossimi passi (non in questo spike)

- Notifica full-screen / ConnectionService per chiamate in arrivo.
- Foreground service audio durante WebRTC.
- CI che pubblica AAB su Play Internal testing.
- Deep link per aprire conversazione/chiamata.

## Documentazione agenti

Vedi `.cursor/rules/android-capacitor.mdc`, sezione in `.cursorrules` e `AGENTS.md`.
