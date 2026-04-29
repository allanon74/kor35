# OTA artifacts Wear OS

Questa cartella contiene l'APK Wear OS compilato da distribuire ai server.

## File atteso

- `app-release.apk` (build release della app Wear OS)

## Flusso

1. Compila l'app Wear OS in locale (`scripts/release_wearos_apk.sh`).
2. Verifica che l'APK sia presente in questa cartella.
3. Commit/push su `main`.
4. La pipeline deploy sincronizza il file su produzione/mirror in:
   - `config/docker/nginx-docker/react_build/watch-apps/wearos-kor35/app-release.apk`

La web app KOR35 espone il link download agli utenti con personaggio `watch_enabled`.
