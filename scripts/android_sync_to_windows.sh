#!/usr/bin/env bash
# Copia frontend/android dal filesystem WSL a un path Windows nativo
# per Android Studio (evita errore Gradle JVM su \\wsl.localhost\...).
#
# Uso (da root monorepo, in WSL):
#   ./scripts/android_sync_to_windows.sh
#   WIN_ANDROID_DIR='C:/dev/kor35-android' ./scripts/android_sync_to_windows.sh
#   WIN_ANDROID_DIR=/mnt/c/dev/kor35-android ./scripts/android_sync_to_windows.sh
#
# Preferisci slash avanti (C:/dev/...) o path /mnt/c/... — i backslash
# in Make/bash vengono spesso mangiati (c:\dev → c:dev).
#
# Exit codes robocopy 0–7 = successo; >=8 = errore.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_LINUX="${ROOT}/frontend/android"
RAW_DEST="${WIN_ANDROID_DIR:-C:/dev/kor35-android}"

echo "=== android_sync_to_windows ==="
echo "Sorgente WSL: ${SRC_LINUX}"
echo "Destinazione richiesta: ${RAW_DEST}"

if [[ ! -d "${SRC_LINUX}" ]]; then
  echo "ERRORE: manca ${SRC_LINUX}. Esegui prima: make android-sync" >&2
  exit 1
fi

if ! command -v wslpath >/dev/null 2>&1; then
  echo "ERRORE: wslpath non trovato. Questo script va eseguito dentro WSL." >&2
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
  echo "ERRORE: Robocopy.exe non trovato sotto /mnt/c/Windows. Windows montato?" >&2
  exit 1
fi

# Normalizza destinazione → path Windows con backslash per robocopy.
normalize_dest_win() {
  local dest="$1"
  # Path Linux montato (/mnt/c/...)
  if [[ "${dest}" == /mnt/* ]]; then
    if [[ ! -d "$(dirname "${dest}")" ]]; then
      mkdir -p "$(dirname "${dest}")"
    fi
    wslpath -w "${dest}"
    return
  fi
  # Slash avanti tipo C:/dev/kor35-android
  if [[ "${dest}" =~ ^[A-Za-z]:/ ]]; then
    dest="${dest//\//\\}"
  fi
  # Se qualcuno ha passato c:\dev\... e bash ha mangiato i backslash
  # resta tipo c:devkor35-android → recupera forma tipica
  if [[ "${dest}" =~ ^[A-Za-z]:[^/\\] ]] && [[ "${dest}" != *\\* ]] && [[ "${dest}" != */* ]]; then
    echo "ATTENZIONE: path sospetto '${dest}' (i \\\\ sono stati mangiati dalla shell)." >&2
    echo "Usa: WIN_ANDROID_DIR='C:/dev/kor35-android'  oppure  WIN_ANDROID_DIR=/mnt/c/dev/kor35-android" >&2
    exit 2
  fi
  # Crea la cartella padre via path /mnt se possibile
  if [[ "${dest}" =~ ^([A-Za-z]):[\\/](.*)$ ]]; then
    local drive="${BASH_REMATCH[1],,}"
    local rest="${BASH_REMATCH[2]//\\//}"
    local parent_linux="/mnt/${drive}/$(dirname "${rest}")"
    mkdir -p "${parent_linux}"
  fi
  printf '%s' "${dest}"
}

DEST_WIN="$(normalize_dest_win "${RAW_DEST}")"
SRC_WIN="$(wslpath -w "${SRC_LINUX}")"

echo "Robocopy:"
echo "  da: ${SRC_WIN}"
echo "  a:  ${DEST_WIN}"

set +e
"${ROBOCOPY}" "${SRC_WIN}" "${DEST_WIN}" /MIR /NFL /NDL /NJH /NJS /nc /ns /np
rc=$?
set -e

if (( rc >= 8 )); then
  echo "ERRORE: robocopy exit ${rc}" >&2
  exit "${rc}"
fi

echo "OK: progetto Android su Windows in ${DEST_WIN}"
echo "In Android Studio: File → Open → ${DEST_WIN}"
echo "(Non aprire il path \\\\wsl.localhost\\... )"
