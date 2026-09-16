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
#   C:/dev/kor35-app/          ← SOLO contenitore (niente settings.gradle qui)
#   C:/dev/kor35-app/android/  ← root Gradle (settings.gradle, gradlew, app/, …)
#
# Dopo ogni sync rimuoviamo eventuali file Gradle lasciati per errore nel parent
# (sync “piatto” legacy): altrimenti Studio apre C:\dev\kor35-app e sembra
# funzionare, mentre …\android risulta “senza configuration”.
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"

CANONICAL_ROOT="C:/dev/kor35-app"
CANONICAL_OPEN="${CANONICAL_ROOT}/android"
RAW_ROOT="${WIN_ANDROID_DIR:-$CANONICAL_ROOT}"

case "${RAW_ROOT}" in
  C:/dev/kor35-android|C:\\dev\\kor35-android|c:/dev/kor35-android|c:\\dev\\kor35-android)
    echo "WARN: ${RAW_ROOT} è legacy. Uso ${CANONICAL_ROOT}" >&2
    RAW_ROOT="${CANONICAL_ROOT}"
    ;;
  */android|*/android/)
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

need_vendor=0
if [[ ! -f "${SRC_ANDROID}/capacitor-plugins/capacitor-status-bar/build.gradle" ]]; then
  need_vendor=1
fi
if grep -Eq "projectDir[[:space:]]*=[[:space:]]*new File\(['\"].*node_modules" \
  "${SRC_ANDROID}/capacitor.settings.gradle" 2>/dev/null
then
  need_vendor=1
fi
if [[ "${need_vendor}" -eq 1 ]]; then
  echo "Re-vendor Capacitor Android plugins…"
  (cd "${ROOT}/frontend" && node scripts/vendor-capacitor-android-plugins.mjs)
fi

if [[ ! -f "${SRC_ANDROID}/capacitor-plugins/capacitor-status-bar/build.gradle" ]]; then
  echo "ERRORE: plugin non vendored dopo retry." >&2
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

to_linux() {
  local dest="$1"
  if [[ "${dest}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
    local drive="${BASH_REMATCH[1],,}"
    local rest="${BASH_REMATCH[2]//\\//}"
    printf '%s' "/mnt/${drive}/${rest}"
    return
  fi
  printf '%s' ""
}

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
    echo "ATTENZIONE: path sospetto '${dest}'." >&2
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

# --- pulizia parent: togli progetto Gradle “piatto” legacy ---
# Se settings.gradle sta in C:\dev\kor35-app\, Studio apre il parent e
# …\android sembra “senza configuration”.
cleanup_parent_gradle_root() {
  local parent_linux="$1"
  local open_linux="$2"
  [[ -n "${parent_linux}" && -d "${parent_linux}" ]] || return 0

  # Non toccare la destinazione corretta.
  if [[ "${parent_linux}" == "${open_linux}" ]]; then
    return 0
  fi

  local removed=0
  local name
  for name in \
    settings.gradle build.gradle gradle.properties variables.gradle \
    gradlew gradlew.bat local.properties \
    capacitor.settings.gradle \
    app gradle .idea .gradle build \
    capacitor-plugins capacitor-cordova-android-plugins \
    APRI_IN_ANDROID_STUDIO.txt
  do
    local p="${parent_linux}/${name}"
    if [[ -e "${p}" ]]; then
      echo "Cleanup parent legacy: rimuovo ${p}"
      rm -rf "${p}"
      removed=1
    fi
  done

  cat > "${parent_linux}/NON_APRIRE_QUI.txt" <<EOF
NON aprire questa cartella in Android Studio.

Questa è solo la cartella contenitore.
Apri SOLO:

  ${OPEN_PATH}

(equivalente: $(echo "${OPEN_PATH}" | sed 's|/|\\|g'))

Se Android Studio riapre da solo questa cartella:
  File → Close Project → Open → seleziona la cartella android sopra.
EOF

  if [[ "${removed}" -eq 1 ]]; then
    echo "OK: parent ripulito (niente più root Gradle in ${RAW_ROOT})."
  fi
}

# Copia local.properties (sdk.dir) se esiste già altrove, così Studio riconosce l'SDK.
seed_local_properties() {
  local open_linux="$1"
  local parent_linux="$2"
  local dest="${open_linux}/local.properties"
  if [[ -f "${dest}" ]]; then
    return 0
  fi

  local candidate=""
  if [[ -f "${parent_linux}/local.properties.bak_kor35" ]]; then
    candidate="${parent_linux}/local.properties.bak_kor35"
  fi
  # SDK Windows tipico
  local sdk_guess=""
  if [[ -d "/mnt/c/Users" ]]; then
    local u
    for u in /mnt/c/Users/*; do
      if [[ -d "${u}/AppData/Local/Android/Sdk" ]]; then
        sdk_guess="${u}/AppData/Local/Android/Sdk"
        break
      fi
    done
  fi

  if [[ -n "${candidate}" ]]; then
    cp "${candidate}" "${dest}"
    echo "Ripristinato local.properties da backup."
    return 0
  fi

  if [[ -n "${sdk_guess}" ]]; then
    local sdk_win
    sdk_win="$(wslpath -w "${sdk_guess}" | sed 's/\\/\\\\/g')"
    printf 'sdk.dir=%s\n' "${sdk_win}" > "${dest}"
    echo "Creato local.properties → sdk.dir=${sdk_win}"
  else
    echo "WARN: nessun SDK Android trovato; al primo open Studio chiederà l'SDK." >&2
  fi
}

OPEN_WIN="$(to_win "${OPEN_PATH}")"
OPEN_WIN="${OPEN_WIN%\\}"
PARENT_WIN="$(to_win "${RAW_ROOT}")"
PARENT_WIN="${PARENT_WIN%\\}"

linux_path="$(to_linux "${OPEN_PATH}")"
parent_linux="$(to_linux "${RAW_ROOT}")"

# Backup local.properties dal parent prima della pulizia (se c'era sync piatto)
if [[ -n "${parent_linux}" && -f "${parent_linux}/local.properties" ]]; then
  cp "${parent_linux}/local.properties" "${parent_linux}/local.properties.bak_kor35" || true
fi

# 1) pulisci parent PRIMA così non resta un secondo progetto
cleanup_parent_gradle_root "${parent_linux}" "${linux_path}"

# 2) copia progetto completo in …/android
robo "${SRC_ANDROID}" "${OPEN_WIN}"

if [[ -z "${linux_path}" || ! -d "${linux_path}" ]]; then
  echo "ERRORE: destinazione Linux non raggiungibile: ${OPEN_PATH}" >&2
  exit 1
fi

fail=0
for f in \
  "${linux_path}/settings.gradle" \
  "${linux_path}/gradlew.bat" \
  "${linux_path}/build.gradle" \
  "${linux_path}/capacitor.settings.gradle" \
  "${linux_path}/capacitor-plugins/capacitor-status-bar/build.gradle" \
  "${linux_path}/capacitor-plugins/capacitor-android/build.gradle" \
  "${linux_path}/app/build.gradle" \
  "${linux_path}/app/src/main/AndroidManifest.xml"
do
  if [[ ! -f "${f}" ]]; then
    echo "ERRORE: manca dopo sync: ${f}" >&2
    fail=1
  fi
done
if [[ "${fail}" -ne 0 ]]; then
  exit 1
fi

if grep -Eq "projectDir[[:space:]]*=[[:space:]]*new File\(['\"].*node_modules" \
  "${linux_path}/capacitor.settings.gradle"
then
  echo "ERRORE: capacitor.settings.gradle punta ancora a node_modules." >&2
  exit 1
fi
if ! grep -q "capacitor-plugins/capacitor-status-bar" \
  "${linux_path}/capacitor.settings.gradle"
then
  echo "ERRORE: capacitor.settings.gradle non usa capacitor-plugins/." >&2
  exit 1
fi

seed_local_properties "${linux_path}" "${parent_linux}"

# Ripeti cleanup: robocopy non deve aver ricreato nulla nel parent
cleanup_parent_gradle_root "${parent_linux}" "${linux_path}"

cat > "${linux_path}/APRI_IN_ANDROID_STUDIO.txt" <<EOF
PATH BLOCCATO — unica cartella da aprire in Android Studio:

  ${OPEN_PATH}

(equivalente: $(echo "${OPEN_PATH}" | sed 's|/|\\|g'))

Checklist file (devono esserci TUTTI):
  - settings.gradle
  - gradlew.bat
  - app\\build.gradle
  - capacitor-plugins\\capacitor-status-bar\\build.gradle

NON aprire:
  - C:\\dev\\kor35-app          (parent — solo contenitore)
  - C:\\dev\\kor35-android
  - \\\\wsl.localhost\\...

In Studio: File → Close Project → Open → questa cartella → Trust Project → Sync Gradle.
EOF

echo
echo "=============================================="
echo " OK — apri in Android Studio SOLO:"
echo "   ${OPEN_WIN}"
echo
echo " Se Studio riapre C:\\dev\\kor35-app (parent):"
echo "   File → Close Project, poi Open sulla cartella android."
echo " Il parent è stato ripulito (niente più app lì)."
echo "=============================================="
