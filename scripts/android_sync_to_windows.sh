#!/usr/bin/env bash
# Copia il progetto Android (self-contained, plugin vendored) su disco Windows.
#
# =============================================================================
# PATH BLOCCATO — NON CAMBIARE SENZA RICHIESTA ESPLICITA DELL'UTENTE
# =============================================================================
# Unica cartella da aprire in Android Studio:
#   C:\dev\kor35-app\android
#
# Layout:
#   C:/dev/kor35-app/          ← destinazione sync (contenitore)
#   C:/dev/kor35-app/android/  ← root Gradle (settings.gradle, gradlew, …)
#
# I plugin Capacitor sono dentro android/capacitor-plugins/ (niente node_modules).
# =============================================================================
#
# Uso (WSL, root monorepo):
#   make android-sync WIN=1
#
# NON usare C:/dev/kor35-android.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"

# Contenitore Windows (override solo se necessario). La cartella Studio è SEMPRE …/android
CANONICAL_ROOT="C:/dev/kor35-app"
CANONICAL_OPEN="${CANONICAL_ROOT}/android"
RAW_ROOT="${WIN_ANDROID_DIR:-$CANONICAL_ROOT}"

case "${RAW_ROOT}" in
  C:/dev/kor35-android|C:\\dev\\kor35-android|c:/dev/kor35-android|c:\\dev\\kor35-android)
    echo "WARN: ${RAW_ROOT} è legacy. Uso ${CANONICAL_ROOT}" >&2
    RAW_ROOT="${CANONICAL_ROOT}"
    ;;
  */android|*/android/)
    # Se qualcuno passa già …/android come WIN_ANDROID_DIR, usa il parent
    echo "WARN: WIN_ANDROID_DIR non deve includere /android. Uso parent → ${CANONICAL_ROOT}" >&2
    RAW_ROOT="${CANONICAL_ROOT}"
    ;;
esac

OPEN_PATH="${RAW_ROOT%/}/android"

echo "=== android_sync_to_windows ==="
echo "Sorgente:       ${SRC_ANDROID}"
echo "Destinazione:   ${OPEN_PATH}"
echo "Apri in Studio: ${OPEN_PATH}"
echo "(path bloccato: ${CANONICAL_OPEN})"

if [[ ! -d "${SRC_ANDROID}" ]]; then
  echo "ERRORE: manca ${SRC_ANDROID}. Esegui prima: make android-sync" >&2
  exit 1
fi
if [[ ! -f "${SRC_ANDROID}/capacitor-plugins/capacitor-status-bar/build.gradle" ]]; then
  echo "ERRORE: plugin non vendored. Esegui: make android-sync" >&2
  echo "Atteso: frontend/android/capacitor-plugins/capacitor-status-bar/build.gradle" >&2
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

OPEN_WIN="$(to_win "${OPEN_PATH}")"
OPEN_WIN="${OPEN_WIN%\\}"

# Copia progetto Android → C:/dev/kor35-app/android (self-contained)
robo "${SRC_ANDROID}" "${OPEN_WIN}"

if [[ "${OPEN_PATH}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
  drive="${BASH_REMATCH[1],,}"
  rest="${BASH_REMATCH[2]//\\//}"
  linux_path="/mnt/${drive}/${rest}"
else
  linux_path=""
fi

if [[ -n "${linux_path}" ]]; then
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

  if grep -q 'node_modules' "${linux_path}/capacitor.settings.gradle"; then
    echo "ERRORE: capacitor.settings.gradle punta ancora a node_modules." >&2
    echo "Rilancia make android-sync (deve eseguire vendor-capacitor-android-plugins)." >&2
    exit 1
  fi

  # Hint anche nel contenitore parent (se qualcuno apre la cartella sbagliata)
  parent_linux="$(dirname "${linux_path}")"
  cat > "${parent_linux}/NON_APRIRE_QUI.txt" <<EOF
NON aprire questa cartella in Android Studio.

Apri SOLO:
  ${OPEN_PATH}

(equivalente: $(echo "${OPEN_PATH}" | sed 's|/|\\|g'))
EOF

  cat > "${linux_path}/APRI_IN_ANDROID_STUDIO.txt" <<EOF
PATH BLOCCATO — unica cartella da aprire in Android Studio:

  ${OPEN_PATH}

(equivalente: $(echo "${OPEN_PATH}" | sed 's|/|\\|g'))

Deve contenere: settings.gradle, gradlew.bat, app/, capacitor-plugins/

NON aprire:
  - C:\\dev\\kor35-android
  - C:\\dev\\kor35-app          (parent: niente Gradle root)
  - \\\\wsl.localhost\\...
EOF
fi

echo
echo "=============================================="
echo " OK — PATH UNICO (bloccato):"
echo "   ${OPEN_WIN}"
echo " Comando: make android-sync WIN=1"
echo "=============================================="
