#!/usr/bin/env bash
set -euo pipefail

# Release helper OTA firmware per LilyGO T-Watch 2021.
# - Build PlatformIO
# - Copia firmware.bin nella cartella artefatti deployati dalla pipeline

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WATCH_PROJECT_DIR="${ROOT_DIR}/extra/local-artifacts/lilygo-twatch-2021"
OTA_ARTIFACT_DIR="${ROOT_DIR}/extra/ota-artifacts/lilygo-twatch-2021"
PIO_ENV="${PIO_ENV:-ttgo-t-watch}"
SOURCE_BIN="${WATCH_PROJECT_DIR}/.pio/build/${PIO_ENV}/firmware.bin"
TARGET_BIN="${OTA_ARTIFACT_DIR}/firmware.bin"

echo "==> KOR35 Watch OTA release"
echo "Root: ${ROOT_DIR}"
echo "Project: ${WATCH_PROJECT_DIR}"
echo "Environment: ${PIO_ENV}"

if ! command -v pio >/dev/null 2>&1; then
  echo "Errore: PlatformIO CLI non trovato (comando 'pio')."
  echo "Installa PlatformIO e riprova."
  exit 1
fi

if [[ ! -d "${WATCH_PROJECT_DIR}" ]]; then
  echo "Errore: cartella progetto watch non trovata: ${WATCH_PROJECT_DIR}"
  exit 1
fi

mkdir -p "${OTA_ARTIFACT_DIR}"

echo "==> Build firmware..."
(
  cd "${WATCH_PROJECT_DIR}"
  pio run -e "${PIO_ENV}"
)

if [[ ! -f "${SOURCE_BIN}" ]]; then
  echo "Errore: firmware.bin non trovato dopo la build: ${SOURCE_BIN}"
  exit 1
fi

cp -f "${SOURCE_BIN}" "${TARGET_BIN}"

echo "==> Firmware copiato:"
echo "    ${TARGET_BIN}"
ls -lh "${TARGET_BIN}"
echo "==> OK. Puoi fare commit/push e il deploy lo sincronizzera' su production + mirror."
