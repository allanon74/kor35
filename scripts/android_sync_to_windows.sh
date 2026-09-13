#!/usr/bin/env bash
# Copia il progetto Android + dipendenze Capacitor su disco Windows nativo.
#
# Android Studio deve aprire la cartella Android (settings.gradle), non il monorepo.
# I moduli Capacitor stanno in node_modules/@capacitor; su Windows li mettiamo
# DENTRO il progetto copiato, così settings.gradle li trova anche se la CWD di
# Gradle non è quella cartella.
#
# Layout prodotto (default):
#   C:/dev/kor35-android/                  ← apri QUESTA in Android Studio
#   C:/dev/kor35-android/node_modules/@capacitor/{android,app,push-notifications,core}
#
# Uso (WSL, root monorepo):
#   ./scripts/android_sync_to_windows.sh
#   WIN_ANDROID_DIR=C:/dev/kor35-android ./scripts/android_sync_to_windows.sh
#
# Preferisci slash avanti (C:/...). I backslash in Make/bash si corrompono.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"
SRC_NM="${ROOT}/frontend/node_modules"
RAW_ROOT="${WIN_ANDROID_DIR:-C:/dev/kor35-android}"

echo "=== android_sync_to_windows ==="
echo "Sorgente android: ${SRC_ANDROID}"
echo "Dest Windows:     ${RAW_ROOT}"

if [[ ! -d "${SRC_ANDROID}" ]]; then
  echo "ERRORE: manca ${SRC_ANDROID}. Esegui prima: make android-sync" >&2
  exit 1
fi
if [[ ! -d "${SRC_NM}/@capacitor/android" ]]; then
  echo "ERRORE: manca ${SRC_NM}/@capacitor/android. Esegui: cd frontend && npm ci" >&2
  exit 1
fi
# I moduli Capacitor dichiarano AGP 8.13.0; pin prima della copia Windows.
"${ROOT}/scripts/pin_android_agp.sh" "${SRC_NM}/@capacitor"
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
    echo "Usa: WIN_ANDROID_DIR=C:/dev/kor35-android" >&2
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
ROOT_WIN="${ROOT_WIN%\\}"

# 1) progetto android (/MIR cancella anche un eventuale node_modules precedente)
robo "${SRC_ANDROID}" "${ROOT_WIN}"

# 2) pacchetti Capacitor DENTRO il progetto (non come sibling)
CAPS=(android app push-notifications core)
for pkg in "${CAPS[@]}"; do
  if [[ -d "${SRC_NM}/@capacitor/${pkg}" ]]; then
    robo "${SRC_NM}/@capacitor/${pkg}" "${ROOT_WIN}\\node_modules\\@capacitor\\${pkg}"
  else
    echo "WARN: manca @capacitor/${pkg} — skip"
  fi
done

echo
echo "OK: layout Windows pronto."
echo "In Android Studio: File → Open → ${ROOT_WIN}"
echo "(Non aprire \\\\wsl.localhost\\... e non aprire C:\\\\dev\\\\kor35-app)"
echo "Poi: File → Sync Project with Gradle Files"
