# LilyGO T-Watch 2021 (workspace locale)

Questa cartella contiene una base firmware reale per usare il LilyGO T-Watch 2021
come estensione hardware di KOR35.

## Perche' questa posizione

- Si trova sotto `extra/local-artifacts/`, gia' esclusa da `.gitignore`.
- Quindi, per default, non va in repository e non entra nel deploy server.
- E' la zona corretta per firmware, test hardware, prototipi rapidi e asset locali.

## Cosa include la base

- `platformio.ini`: progetto PlatformIO (ESP32 + librerie T-Watch).
- `include/kor35_watch_config.h`: configurazione locale (Wi-Fi, endpoint API, device id).
- `src/main.cpp`: bootstrap dispositivo, clock sempre visibile, pairing code, schermate base/game/timers, queue eventi locale con flush.

## Flusso rapido (Docker-first per KOR35, locale per firmware)

Nota: il firmware gira su microcontrollore e si sviluppa localmente con PlatformIO.

1. Apri questa cartella in VSCode con PlatformIO.
2. Aggiorna `include/kor35_watch_config.h` con:
   - SSID/password hotspot o rete locale.
   - `KOR35_API_BASE_URL` (es. `http://10.42.0.1` in edge offline).
   - `KOR35_DEVICE_ID` univoco.
3. Collega il watch via USB.
4. Build + flash:
   - `pio run`
   - `pio run -t upload`
   - `pio device monitor`

## Prossimi step integrazione KOR35

- Definire endpoint gameplay dedicati (es. eventi missione, stato personaggio, token QR).
- Passare da solo polling health a protocollo applicativo (JSON firmato + retry).
- Aggiungere UX watch (schermate missione, alert vibrazione, input touch).
- Gestire modalita' offline robusta con coda eventi locale e sincronizzazione.
