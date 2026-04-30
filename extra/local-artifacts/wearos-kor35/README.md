# KOR35 Wear OS MVP (Android Studio)

Progetto Android Studio completo (Gradle Kotlin DSL) per una app Wear OS che replica il comportamento previsto per lo smartwatch:

- pairing con codice temporaneo
- schermata Game con PV/PA/PG/CHA
- update ottimistico locale
- coda offline eventi e flush successivo
- sincronizzazione con backend KOR35

## Icona launcher (come la web app)

L’app nel drawer dello smartwatch usa **`@mipmap/ic_launcher`** (adaptive icon: sfondo slate + foreground).

- **Default in repo**: foreground vettoriale (fallback) così Gradle compila senza PNG del logo.
- **Logo reale**: dalla root monorepo esegui `./scripts/sync_wear_launcher_icon_from_web.sh` (serve **ImageMagick**). Lo script usa il **primo file esistente** tra:
  - `frontend/public/Logo Kor-AD.png` (favicon PWA, `index.html`)
  - `frontend/public/Logo Kor-AD_Trasp.png` (header React)
  - `frontend/public/pwa-512x512.png` e `pwa-192x192.png` (icone manifest PWA)
  - `frontend/public/logo.png`, `icon.png`, `favicon.png` se presenti
  - `backend/static/tema/logo.png` (template Django `{% static 'tema/logo.png' %}`)

  Poi committa `drawable/kor35_launcher_logo.png` e `drawable/ic_launcher_foreground.xml` generati.

## Posizione progetto

Questo progetto e' in `extra/local-artifacts/`: viene versionato su GitHub ma viene rimosso esplicitamente dagli step di deploy su production/mirror.

## API KOR35 da usare

- `POST /api/personaggi/api/device/watch/pair/start/`
- `GET /api/personaggi/api/device/watch/pair/status/`
- `POST /api/personaggi/api/device/watch/pair/confirm/`
- `GET /api/personaggi/api/device/watch/profile/`
- `POST /api/personaggi/api/device/watch/sync/`
- `POST /api/personaggi/api/device/watch/disconnect/`

## Stack incluso

- Jetpack Compose (UI watch)
- Retrofit + OkHttp (API)
- Room (queue offline)
- WorkManager (flush eventi)

## Struttura moduli

- `settings.gradle.kts`, `build.gradle.kts`, `gradle.properties`: bootstrap Gradle
- `app/build.gradle.kts`: modulo app Wear
- `app/src/main/java/it/kor35/wearos/ui/`: schermate Compose (orologio, pairing, game)
- `app/src/main/java/it/kor35/wearos/data/`: config/api/models/repository
- `app/src/main/java/it/kor35/wearos/offline/`: Room + worker flush queue
- `docs/`: note architettura e contratti

## Build

Da terminale (nella cartella del modulo):

```bash
./gradlew assembleDebug      # APK debug firmato (installabile via adb)
./gradlew assembleRelease    # release (serve firma configurata in Gradle)
```

Manca `./gradlew`? Il progetto include ora il **Gradle Wrapper** (`gradlew`, `gradlew.bat`, `gradle/wrapper/`): va committato sul repo. Serve un JDK **completo** con `jlink` (es. OpenJDK 17: `sudo apt install openjdk-17-jdk`, poi `export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`).

1. Apri `extra/local-artifacts/wearos-kor35` in Android Studio.
2. Lascia sincronizzare Gradle.
3. L’endpoint di default è `https://www.kor35.it/` in `Kor35ApiConfig` (modificalo solo per test fuori produzione).
4. Esegui su emulatore/dispositivo Wear OS.
5. Per release APK verso deploy KOR35 usa `scripts/release_wearos_apk.sh` (vedi **Firma release** sotto).

### Firma release (APK installabile via `adb`)

Senza keystore Gradle produce un APK **unsigned** (`INSTALL_PARSE_FAILED_NO_CERTIFICATES` sullo SW).

1. Genera un keystore (una tantum): `keytool -genkeypair -v -keystore wear-release.jks -alias wear -keyalg RSA -keysize 2048 -validity 10000` (nella cartella del modulo Wear).
2. Copia `signing.env.example` → `signing.env`, valorizza `WEAR_RELEASE_*` (file **non** in git).
3. Esegui `scripts/release_wearos_apk.sh`: lo script fa `source` di `signing.env` se presente.

Stesse variabili si possono esportare nel shell o definire in `gradle.properties` locale come `wear.release.storeFile`, ecc. (senza committare segreti).

## Troubleshooting WSL (Gradle)

Se il progetto e' su WSL (`/home/...`) e Android Studio e' su Windows:

- build e wrapper vanno eseguiti in terminale WSL
- non usare JDK/Gradle Windows per path `\\wsl$...`

Comandi consigliati:

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk zip unzip curl
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install gradle 8.7
cd /home/django/progetti/kor35/extra/local-artifacts/wearos-kor35
gradle wrapper --gradle-version 8.7
cd /home/django/progetti/kor35
./scripts/release_wearos_apk.sh
```

## Note MVP

- Orologio sempre visibile in alto, aggiornato ogni secondo.
- Schermata pairing: pulsante `Connetti` + codice device.
- Polling automatico stato pairing fino a ricezione `pair_token`.
- Persistenza `pair_token` su DataStore e restore automatico sessione al riavvio.
- Schermata game: tap `-1`, long press `+1` su PV/PA/PG/CHA.
- Ogni delta viene applicato subito in UI e messo in coda locale.
- WorkManager prova il flush verso backend quando schedulato.
