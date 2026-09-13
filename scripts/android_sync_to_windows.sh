#!/usr/bin/env bash
# Copia il progetto Android (già self-contained) su disco Windows nativo.
#
# UNICO PATH CANONICO — apri QUESTA cartella in Android Studio:
#   C:/dev/kor35-app
#
# (È la root Gradle: settings.gradle, gradlew, app/, capacitor-plugins/)
# Non serve più un sibling node_modules: i plugin Capacitor sono vendored.
#
# Uso (WSL, root monorepo):
#   make android-sync WIN=1
#
# NON usare C:/dev/kor35-android (layout legacy/rotto).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"

CANONICAL_ROOT="C:/dev/kor35-app"
RAW_ROOT="${WIN_ANDROID_DIR:-$CANONICAL_ROOT}"

case "${RAW_ROOT}" in
  C:/dev/kor35-android|C:\\dev\\kor35-android|c:/dev/kor35-android|c:\\dev\\kor35-android)
    echo "WARN: ${RAW_ROOT} è il path legacy. Uso il canonico ${CANONICAL_ROOT}" >&2
    RAW_ROOT="${CANONICAL_ROOT}"
    ;;
  */android|*/android/)
    echo "WARN: non usare .../android come destinazione. Uso ${CANONICAL_ROOT}" >&2
    echo "      (dopo il fix la root Gradle È C:/dev/kor35-app, non una sottocartella)" >&2
    RAW_ROOT="${CANONICAL_ROOT}"
    ;;
esac

echo "=== android_sync_to_windows ==="
echo "Sorgente:       ${SRC_ANDROID}"
echo "Destinazione:   ${RAW_ROOT}"
echo "Apri in Studio: ${RAW_ROOT}"

if [[ ! -d "${SRC_ANDROID}" ]]; then
  echo "ERRORE: manca ${SRC_ANDROID}. Esegui prima: make android-sync" >&2
  exit 1
fi
if [[ ! -f "${SRC_ANDROID}/capacitor-plugins/capacitor-status-bar/build.gradle" ]]; then
  echo "ERRORE: plugin non vendored. Esegui: make android-sync (senza solo WIN)" >&2
  echo "Atteso: frontend/android/capacitor-plugins/capacitor-status-bar/build.gradle" >&2
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

# Copia l'intero progetto Android come root Windows (self-contained).
robo "${SRC_ANDROID}" "${ROOT_WIN}"

# Rimuovi resti legacy confusi (sottocartella android + node_modules sibling).
if [[ "${RAW_ROOT}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
  drive="${BASH_REMATCH[1],,}"
  rest="${BASH_REMATCH[2]//\\//}"
  linux_path="/mnt/${drive}/${rest}"
else
  linux_path=""
fi

if [[ -n "${linux_path}" ]]; then
  # Se esiste ancora una nested android/ da sync vecchi, avvisa.
  if [[ -d "${linux_path}/android" ]] && [[ -f "${linux_path}/settings.gradle" ]]; then
    echo "WARN: trovata nested ${RAW_ROOT}/android (sync vecchio). Ignorala: apri ${RAW_ROOT}" >&2
  fi

  fail=0
  for f in \
    "${linux_path}/settings.gradle" \
    "${linux_path}/gradlew.bat" \
    "${linux_path}/capacitor.settings.gradle" \
    "${linux_path}/capacitor-plugins/capacitor-status-bar/build.gradle" \
    "${linux_path}/capacitor-plugins/capacitor-android/build.gradle" \
    "${linux_path}/app/build.gradle"
  do
    if [[ ! -f "${f}" ]]; then
      echo "ERRORE: manca dopo sync: ${f}" >&2
      fail=1
    fi
  done
  if [[ "${fail}" -ne 0 ]]; then
    exit 1
  fi

  # Se capacitor.settings punta ancora a node_modules → build rotta
  if grep -q 'node_modules' "${linux_path}/capacitor.settings.gradle"; then
    echo "ERRORE: capacitor.settings.gradle punta ancora a node_modules." >&2
    echo "Rilancia make android-sync (deve eseguire vendor-capacitor-android-plugins)." >&2
    exit 1
  fi

  cat > "${linux_path}/APRI_IN_ANDROID_STUDIO.txt" <<EOF
Apri in Android Studio SOLO questa cartella:

  ${RAW_ROOT}

(equivalente: $(echo "${RAW_ROOT}" | sed 's|/|\\|g'))

Deve contenere: settings.gradle, gradlew.bat, app/, capacitor-plugins/

NON aprire:
  - C:\\dev\\kor35-android
  - ${RAW_ROOT}\\android   (vecchio layout nested)
  - \\\\wsl.localhost\\...
EOF
fi

echo
echo "=============================================="
echo " OK — apri in Android Studio SOLO:"
echo "   ${ROOT_WIN}"
echo " Comando: make android-sync WIN=1"
echo "=============================================="
echo "Chiudi progetti vecchi (kor35-android / ...\\android nested)."
