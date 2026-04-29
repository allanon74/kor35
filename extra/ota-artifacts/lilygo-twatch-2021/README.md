# OTA artifacts T-Watch 2021

Questa cartella contiene il firmware compilato da distribuire ai server per OTA.

## File atteso

- `firmware.bin` (build release del T-Watch 2021)

## Flusso

1. Compila il firmware in locale con PlatformIO.
2. Copia il binario in questa cartella come `firmware.bin`.
3. Commit/push su `main`.
4. La pipeline deploy sincronizza il file su produzione/mirror in:
   - `config/docker/nginx-docker/react_build/watch-ota/lilygo-twatch-2021/firmware.bin`

Il backend espone un manifest OTA con URL assoluto del firmware.
