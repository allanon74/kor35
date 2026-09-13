#!/usr/bin/env bash
# Copia frontend/android dal filesystem WSL a un path Windows nativo
# per Android Studio (evita errore Gradle JVM su \\wsl.localhost\...).
#
# Uso (da root monorepo, in WSL):
#   ./scripts/android_sync_to_windows.sh
#   WIN_ANDROID_DIR='C:\dev\kor35-android' ./scripts/android_sync_to_windows.sh
#
# Exit codes robocopy 0–7 = successo; >=8 = errore.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_LINUX="${ROOT}/frontend/android"
DEST_WIN="${WIN_ANDROID_DIR:-C:\dev\kor35-android}"

if [[ ! -d "${SRC_LINUX}" ]]; then
  echo "ERRORE: manca ${SRC_LINUX}. Esegui prima make android-sync (senza WIN) o npm run cap:sync." >&2
  exit 1
fi

if ! command -v wslpath >/dev/null 2>&1; then
  echo "ERRORE: wslpath non trovato. Questo script va eseguito dentro WSL." >&2
  exit 1
fi

ROBOCOPY=""
for candidate in \
  /mnt/c/Windows/System32/Robocopy.exe \
  /mnt/c/Windows/SysWOW64/Robocopy.exe \
  Robocopy.exe
do
  if command -v "${candidate}" >/dev/null 2>&1 || [[ -x "${candidate}" ]]; then
    ROBOCOPY="${candidate}"
    break
  fi
done

if [[ -z "${ROBOCOPY}" ]]; then
  echo "ERRORE: Robocopy.exe non trovato (Windows non montato in /mnt/c?)." >&2
  exit 1
fi

SRC_WIN="$(wslpath -w "${SRC_LINUX}")"
echo "Robocopy: ${SRC_WIN}  →  ${DEST_WIN}"

set +e
"${ROBOCOPY}" "${SRC_WIN}" "${DEST_WIN}" /MIR /NFL /NDL /NJH /NJS /nc /ns /np
rc=$?
set -e

# Robocopy: 0–7 ok, 8+ fail
if (( rc >= 8 )); then
  echo "ERRORE: robocopy exit ${rc}" >&2
  exit "${rc}"
fi

echo "OK: progetto Android su Windows in ${DEST_WIN}"
echo "In Android Studio: File → Open → ${DEST_WIN}"
