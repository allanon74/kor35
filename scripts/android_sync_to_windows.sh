#!/usr/bin/env bash
# Copia il progetto Android + dipendenze Capacitor su disco Windows nativo.
#
# UNICO PATH CANONICO (non usarne altri):
#   C:/dev/kor35-app/android          ← apri QUESTA in Android Studio
#   C:/dev/kor35-app/node_modules/... ← sibling obbligatorio (Capacitor)
#
# Uso (WSL, root monorepo):
#   make android-sync WIN=1
#   # oppure:
#   ./scripts/android_sync_to_windows.sh
#
# NON usare C:/dev/kor35-android (layout legacy/rotto).
# Preferisci slash avanti (C:/...). I backslash in Make/bash si corrompono.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"
SRC_NM="${ROOT}/frontend/node_modules"

# Path fisso: override solo se sai cosa fai.
CANONICAL_ROOT="C:/dev/kor35-app"
RAW_ROOT="${WIN_ANDROID_DIR:-$CANONICAL_ROOT}"

# Normalizza alias legacy → canonico
case "${RAW_ROOT}" in
  C:/dev/kor35-android|C:\\dev\\kor35-android|c:/dev/kor35-android|c:\\dev\\kor35-android)
    echo "WARN: ${RAW_ROOT} è il path legacy. Uso il canonico ${CANONICAL_ROOT}" >&2
    RAW_ROOT="${CANONICAL_ROOT}"
    ;;
esac

echo "=== android_sync_to_windows ==="
echo "Sorgente android: ${SRC_ANDROID}"
echo "Root Windows:     ${RAW_ROOT}"
echo "Apri in Studio:   ${RAW_ROOT}/android"

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
ROOT_WIN="${ROOT_WIN%\\}"

# 1) progetto android
robo "${SRC_ANDROID}" "${ROOT_WIN}\\android"

# 2) pacchetti Capacitor richiesti da capacitor.settings.gradle
CAPS=(android app push-notifications status-bar core)
MISSING=0
for pkg in "${CAPS[@]}"; do
  if [[ -d "${SRC_NM}/@capacitor/${pkg}" ]]; then
    robo "${SRC_NM}/@capacitor/${pkg}" "${ROOT_WIN}\\node_modules\\@capacitor\\${pkg}"
  else
    echo "ERRORE: manca @capacitor/${pkg} in node_modules (npm ci / cap sync)." >&2
    MISSING=1
  fi
done
if [[ "${MISSING}" -ne 0 ]]; then
  exit 1
fi

# 3) verifica post-copia (evita "No variants exist" in Studio)
verify_linux_path() {
  local drive rest linux_path
  if [[ "${RAW_ROOT}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
    drive="${BASH_REMATCH[1],,}"
    rest="${BASH_REMATCH[2]//\\//}"
    linux_path="/mnt/${drive}/${rest}"
  else
    echo "WARN: impossibile verificare path Linux per ${RAW_ROOT}" >&2
    return 0
  fi
  local fail=0
  local f
  for f in \
    "${linux_path}/android/capacitor.settings.gradle" \
    "${linux_path}/node_modules/@capacitor/status-bar/android/build.gradle" \
    "${linux_path}/node_modules/@capacitor/push-notifications/android/build.gradle" \
    "${linux_path}/node_modules/@capacitor/app/android/build.gradle" \
    "${linux_path}/node_modules/@capacitor/android/capacitor/build.gradle"
  do
    if [[ ! -f "${f}" ]]; then
      echo "ERRORE: manca dopo sync: ${f}" >&2
      fail=1
    fi
  done
  if [[ "${fail}" -ne 0 ]]; then
    echo "Sync incompleto: non aprire Android Studio finché non è OK." >&2
    exit 1
  fi
  # Hint in chiaro sul disco Windows
  cat > "${linux_path}/APRI_IN_ANDROID_STUDIO.txt" <<EOF
Apri in Android Studio SOLO questa cartella:

  ${RAW_ROOT}/android

(equivalente Windows: $(echo "${RAW_ROOT}" | sed 's|/|\\|g')\\android)

NON aprire:
  - C:\\dev\\kor35-android
  - \\\\wsl.localhost\\...
  - la cartella parent senza \\android
EOF
}

verify_linux_path

echo
echo "=============================================="
echo " OK — path UNICO da usare da ora in poi:"
echo "   ${ROOT_WIN}\\android"
echo " Comando: make android-sync WIN=1"
echo "=============================================="
echo "Ignora C:\\dev\\kor35-android (legacy)."
