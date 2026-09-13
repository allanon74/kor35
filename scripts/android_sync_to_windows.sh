#!/usr/bin/env bash
# Copia il progetto Android + dipendenze Capacitor su disco Windows nativo.
#
# Capacitor settings.gradle punta a ../node_modules/@capacitor/...
# Quindi NON basta copiare solo frontend/android: serve anche node_modules.
#
# Layout prodotto (default):
#   C:/dev/kor35-app/android
#   C:/dev/kor35-app/node_modules/@capacitor/{android,app,push-notifications,status-bar,core}
#
# Uso (WSL, root monorepo):
#   ./scripts/android_sync_to_windows.sh
#   WIN_ANDROID_DIR=C:/dev/kor35-app ./scripts/android_sync_to_windows.sh
#
# Poi in Android Studio: Open → C:\dev\kor35-app\android
#
# Preferisci slash avanti (C:/...). I backslash in Make/bash si corrompono.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"
SRC_NM="${ROOT}/frontend/node_modules"
RAW_ROOT="${WIN_ANDROID_DIR:-C:/dev/kor35-app}"

echo "=== android_sync_to_windows ==="
echo "Sorgente android: ${SRC_ANDROID}"
echo "Root Windows:     ${RAW_ROOT}"

if [[ ! -d "${SRC_ANDROID}" ]]; then
  echo "ERRORE: manca ${SRC_ANDROID}. Esegui prima: make android-sync" >&2
  exit 1
fi
if [[ ! -d "${SRC_NM}/@capacitor/android" ]]; then
  echo "ERRORE: manca ${SRC_NM}/@capacitor/android. Esegui: cd frontend && npm ci" >&2
  exit 1
fi
if ! command -v wslpath >/dev/null 2>&1; then
  echo "ERRORE: wslpath non trovato. Esegui dentro WSL." >&2
  exit 1
fi

ROBOCOPY=""
for candidate in \
  /mnt/c/Windows/System32/Robocopy.exe \
  /mnt/c/Windows/SysWOW64/Robocopy.exe
do
  if [[ -x "${candidate}" ]]; then
    ROBOCOPY="${candidate}"
    break
  fi
done
if [[ -z "${ROBOCOPY}" ]]; then
  echo "ERRORE: Robocopy.exe non trovato sotto /mnt/c/Windows." >&2
  exit 1
fi

to_win() {
  local dest="$1"
  if [[ "${dest}" == /mnt/* ]]; then
    mkdir -p "${dest}"
    wslpath -w "${dest}"
    return
  fi
  if [[ "${dest}" =~ ^[A-Za-z]:/ ]]; then
    dest="${dest//\//\\}"
  fi
  if [[ "${dest}" =~ ^[A-Za-z]:[^/\\] ]] && [[ "${dest}" != *\\* ]] && [[ "${dest}" != */* ]]; then
    echo "ATTENZIONE: path sospetto '${dest}' (backslash mangiati dalla shell)." >&2
    echo "Usa: WIN_ANDROID_DIR=C:/dev/kor35-app" >&2
    exit 2
  fi
  if [[ "${dest}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
    local drive="${BASH_REMATCH[1],,}"
    local rest="${BASH_REMATCH[2]//\\//}"
    mkdir -p "/mnt/${drive}/${rest}"
  fi
  printf '%s' "${dest}"
}

robo() {
  local src_linux="$1"
  local dest_win="$2"
  local src_win
  src_win="$(wslpath -w "${src_linux}")"
  echo "Robocopy: ${src_win}  →  ${dest_win}"
  set +e
  "${ROBOCOPY}" "${src_win}" "${dest_win}" /MIR /NFL /NDL /NJH /NJS /nc /ns /np
  local rc=$?
  set -e
  if (( rc >= 8 )); then
    echo "ERRORE: robocopy exit ${rc} (${src_linux})" >&2
    exit "${rc}"
  fi
}

ROOT_WIN="$(to_win "${RAW_ROOT}")"
# Normalizza eventuale trailing slash
ROOT_WIN="${ROOT_WIN%\\}"

# 1) progetto android
robo "${SRC_ANDROID}" "${ROOT_WIN}\\android"

# 2) pacchetti Capacitor richiesti da capacitor.settings.gradle
# Allineare a frontend/android/capacitor.settings.gradle (cap sync).
CAPS=(android app push-notifications status-bar core)
for pkg in "${CAPS[@]}"; do
  if [[ -d "${SRC_NM}/@capacitor/${pkg}" ]]; then
    robo "${SRC_NM}/@capacitor/${pkg}" "${ROOT_WIN}\\node_modules\\@capacitor\\${pkg}"
  else
    echo "WARN: manca @capacitor/${pkg} — skip"
  fi
done

echo
echo "OK: layout Windows pronto."
echo "Apri in Android Studio:"
echo "  ${ROOT_WIN}\\android"
echo "(Non aprire\\\\wsl.localhost\\... e non aprire solo C:\\dev\\kor35-android senza node_modules)"
