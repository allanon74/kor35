#!/usr/bin/env bash
# Copia il progetto Android (self-contained, plugin vendored) su disco Windows.
#
# =============================================================================
# PATH BLOCCATO — NON CAMBIARE SENZA RICHIESTA ESPLICITA DELL'UTENTE
#   Apri in Android Studio:  C:\dev\kor35-app\android
# =============================================================================
#
# Cosa serve perché Studio mostri device selector + Run (non "Add Configuration"):
#   - settings.gradle / build.gradle / app/build.gradle           (dal repo)
#   - capacitor-plugins/…            (vendored, no node_modules)
#   - capacitor-cordova-android-plugins/  (generata da `npx cap sync`)
#   - local.properties  → sdk.dir                (per-macchina, NON in git)
#   - .idea/            → run configurations Studio (per-macchina)
#
# local.properties e .idea NON esistono nel repo: robocopy /MIR li cancellerebbe
# dalla destinazione. Sono esclusi dal mirror e local.properties viene creato.
#
# Uso (WSL, root monorepo):  make android-sync WIN=1

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_ANDROID="${ROOT}/frontend/android"

CANONICAL_ROOT="C:/dev/kor35-app"
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
echo "Apri in Studio: ${OPEN_PATH}"

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

# settings.gradle include ':capacitor-cordova-android-plugins' e
# app/capacitor.build.gradle fa apply from ../capacitor-cordova-android-plugins/…
# Se manca, il Gradle sync fallisce → Studio non crea la run configuration.
if [[ ! -f "${SRC_ANDROID}/capacitor-cordova-android-plugins/cordova.variables.gradle" ]]; then
  echo "ERRORE: manca ${SRC_ANDROID}/capacitor-cordova-android-plugins/" >&2
  echo "Senza quella cartella Studio non configura il modulo app." >&2
  echo "Rigenerala: cd frontend && npx cap sync android" >&2
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
  if [[ "$1" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
    local drive="${BASH_REMATCH[1],,}"
    local rest="${BASH_REMATCH[2]//\\//}"
    printf '%s' "/mnt/${drive}/${rest}"
  else
    printf '%s' ""
  fi
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
  if [[ "${dest}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
    local drive="${BASH_REMATCH[1],,}"
    local rest="${BASH_REMATCH[2]//\\//}"
    mkdir -p "/mnt/${drive}/${rest}"
  fi
  printf '%s' "${dest}"
}

# Mirror del progetto, ma NON toccare stato locale di Studio:
#   /XD .idea .gradle build   → preserva run configurations e cache
#   /XF local.properties      → preserva sdk.dir
robo_project() {
  local src_linux="$1"
  local dest_win="$2"
  local src_win
  src_win="$(wslpath -w "${src_linux}")"
  echo "Robocopy: ${src_win}  →  ${dest_win}"
  set +e
  "${ROBOCOPY}" "${src_win}" "${dest_win}" /MIR \
    /XD "${dest_win}\\.idea" "${dest_win}\\.gradle" "${dest_win}\\build" \
    /XF local.properties \
    /NFL /NDL /NJH /NJS /nc /ns /np
  local rc=$?
  set -e
  if (( rc >= 8 )); then
    echo "ERRORE: robocopy exit ${rc}" >&2
    exit "${rc}"
  fi
}

detect_sdk_dir_win() {
  local u
  for u in /mnt/c/Users/*; do
    if [[ -d "${u}/AppData/Local/Android/Sdk" ]]; then
      wslpath -w "${u}/AppData/Local/Android/Sdk"
      return 0
    fi
  done
  return 1
}

# Senza local.properties → "SDK location not found" → nessuna run configuration.
ensure_local_properties() {
  local open_linux="$1"
  local parent_linux="$2"
  local dest="${open_linux}/local.properties"

  if [[ -f "${dest}" ]] && grep -q '^sdk.dir=' "${dest}"; then
    echo "OK: local.properties già presente (sdk.dir)."
    return 0
  fi

  # 1) riusa quello del progetto che funzionava (parent, sync legacy)
  if [[ -n "${parent_linux}" && -f "${parent_linux}/local.properties" ]]; then
    cp "${parent_linux}/local.properties" "${dest}"
    echo "OK: local.properties copiato dal progetto precedente (${RAW_ROOT})."
    return 0
  fi

  # 2) altrimenti individua l'SDK Android su Windows
  local sdk_win=""
  if sdk_win="$(detect_sdk_dir_win)"; then
    printf 'sdk.dir=%s\n' "${sdk_win//\\/\\\\}" > "${dest}"
    echo "OK: creato local.properties → sdk.dir=${sdk_win}"
    return 0
  fi

  echo "WARN: SDK Android non trovato: al primo Open, Studio chiederà l'SDK." >&2
  return 0
}

OPEN_WIN="$(to_win "${OPEN_PATH}")"
OPEN_WIN="${OPEN_WIN%\\}"
linux_path="$(to_linux "${OPEN_PATH}")"
parent_linux="$(to_linux "${RAW_ROOT}")"

robo_project "${SRC_ANDROID}" "${OPEN_WIN}"

if [[ -z "${linux_path}" || ! -d "${linux_path}" ]]; then
  echo "ERRORE: destinazione non raggiungibile: ${OPEN_PATH}" >&2
  exit 1
fi

ensure_local_properties "${linux_path}" "${parent_linux}"

fail=0
for f in \
  "${linux_path}/settings.gradle" \
  "${linux_path}/build.gradle" \
  "${linux_path}/gradlew.bat" \
  "${linux_path}/capacitor.settings.gradle" \
  "${linux_path}/capacitor-plugins/capacitor-status-bar/build.gradle" \
  "${linux_path}/capacitor-cordova-android-plugins/cordova.variables.gradle" \
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

if [[ ! -f "${linux_path}/app/google-services.json" ]]; then
  echo "NOTA: app/google-services.json assente → build OK ma push FCM non funzionano." >&2
fi

# Se un import precedente è fallito, Studio lascia un .idea NON collegato a Gradle
# (senza .idea/gradle.xml) e al riapri NON ritenta: risultato "Add Configuration…"
# e nessun device. In quel caso il .idea va buttato: Studio rifà l'import.
reset_broken_idea() {
  local proj="$1"
  local idea="${proj}/.idea"
  [[ -d "${idea}" ]] || return 0

  if [[ -f "${idea}/gradle.xml" ]]; then
    echo "OK: .idea collegato a Gradle (run configurations preservate)."
    return 0
  fi

  echo "ATTENZIONE: ${OPEN_PATH}/.idea esiste ma non è un progetto Gradle."
  echo "            (import precedente fallito) → lo rimuovo per forzare il re-import."
  rm -rf "${idea}"
  rm -rf "${proj}/.gradle"
  echo "OK: .idea e .gradle rimossi. Alla prossima apertura Studio reimporta."
}

if [[ "${ANDROID_RESET_STUDIO:-0}" = "1" ]]; then
  echo "ANDROID_RESET_STUDIO=1 → rimuovo .idea/.gradle/build dalla destinazione"
  rm -rf "${linux_path}/.idea" "${linux_path}/.gradle" "${linux_path}/build"
else
  reset_broken_idea "${linux_path}"
fi

# Il parent resta com'è: non cancelliamo nulla di tuo. Solo un promemoria.
if [[ -n "${parent_linux}" && -d "${parent_linux}" && "${parent_linux}" != "${linux_path}" ]]; then
  cat > "${parent_linux}/APRI_LA_CARTELLA_ANDROID.txt" <<EOF
Progetto aggiornato da 'make android-sync WIN=1':

  ${OPEN_PATH}

Apri quella cartella in Android Studio.
Questa cartella (parent) può contenere una copia vecchia: non viene più aggiornata.
EOF
fi

echo
echo "=============================================="
echo " OK — apri in Android Studio:"
echo "   ${OPEN_WIN}"
echo
echo " Presenti: settings.gradle, app/, capacitor-plugins/,"
echo "           capacitor-cordova-android-plugins/, local.properties"
echo
echo " In Studio, se non vedi il device selector:"
echo "   1) File → Close Project"
echo "   2) Open → ${OPEN_WIN}  (seleziona la cartella, non un file)"
echo "   3) Trust Project → attendi 'Gradle sync'"
echo "   4) se serve: File → Sync Project with Gradle Files"
echo
echo " Reset totale progetto Studio (butta .idea/.gradle/build):"
echo "   make android-reset-studio WIN=1"
echo "=============================================="
