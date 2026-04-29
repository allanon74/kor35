# KOR35 Wear OS MVP (Android Studio)

Progetto Android Studio completo (Gradle Kotlin DSL) per una app Wear OS che replica il comportamento previsto per lo smartwatch:

- pairing con codice temporaneo
- schermata Game con PV/PA/PG/CHA
- update ottimistico locale
- coda offline eventi e flush successivo
- sincronizzazione con backend KOR35

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

1. Apri `extra/local-artifacts/wearos-kor35` in Android Studio.
2. Lascia sincronizzare Gradle.
3. Configura endpoint in `Kor35ApiConfig`.
4. Esegui su emulatore/dispositivo Wear OS.
5. Per release APK verso deploy KOR35 usa `scripts/release_wearos_apk.sh`.

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
