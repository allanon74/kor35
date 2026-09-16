#!/usr/bin/env bash
# Compila l'APK di KOR35 direttamente in WSL/Linux, senza Android Studio.
#
# Perché: il doppio progetto su disco Windows (C:\dev\kor35-app e ...\android)
# porta Studio a compilare la copia sbagliata. Qui c'è UNA sola sorgente:
# frontend/android nel repo.
#
# Uso:
#   make android-apk              # debug APK
#   make android-apk RELEASE=1    # release non firmata
#
# L'SDK viene installato in ~/android-sdk se manca (solo cmdline-tools + platform).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="${ROOT}/frontend"
ANDROID_DIR="${FRONTEND}/android"

RELEASE="${RELEASE:-0}"
if [[ "${RELEASE}" = "1" ]]; then
  GRADLE_TASK=":app:assembleRelease"
  APK_REL="app/build/outputs/apk/release/app-release-unsigned.apk"
  APK_NAME="kor35-release-unsigned.apk"
else
  GRADLE_TASK=":app:assembleDebug"
  APK_REL="app/build/outputs/apk/debug/app-debug.apk"
  APK_NAME="kor35-debug.apk"
fi

SDK_DIR="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/android-sdk}}"
CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

# Versioni allineate a frontend/android/variables.gradle
COMPILE_SDK="$(grep -oP 'compileSdkVersion\s*=\s*\K[0-9]+' "${ANDROID_DIR}/variables.gradle" || echo 36)"
BUILD_TOOLS="${COMPILE_SDK}.0.0"

echo "=== build APK KOR35 (senza Android Studio) ==="
echo "Sorgente : ${ANDROID_DIR}"
echo "SDK      : ${SDK_DIR}"
echo "Task     : ${GRADLE_TASK}"

if ! command -v java >/dev/null 2>&1; then
  echo "ERRORE: serve un JDK 21 (sudo apt install -y openjdk-21-jdk)" >&2
  exit 1
fi

ensure_sdk() {
  local sdkmanager="${SDK_DIR}/cmdline-tools/latest/bin/sdkmanager"

  if [[ ! -x "${sdkmanager}" ]]; then
    echo "SDK command line tools assenti: installo in ${SDK_DIR}"
    command -v curl >/dev/null 2>&1 || { echo "ERRORE: serve curl" >&2; exit 1; }
    command -v unzip >/dev/null 2>&1 || { echo "ERRORE: serve unzip" >&2; exit 1; }
    local tmp
    tmp="$(mktemp -d)"
    curl -fsSL -o "${tmp}/cmdline.zip" "${CMDLINE_TOOLS_URL}"
    mkdir -p "${SDK_DIR}/cmdline-tools"
    unzip -q "${tmp}/cmdline.zip" -d "${tmp}/unpacked"
    rm -rf "${SDK_DIR}/cmdline-tools/latest"
    mv "${tmp}/unpacked/cmdline-tools" "${SDK_DIR}/cmdline-tools/latest"
    rm -rf "${tmp}"
  fi

  if [[ ! -d "${SDK_DIR}/platforms/android-${COMPILE_SDK}" ]]; then
    echo "Installo platform android-${COMPILE_SDK} e build-tools ${BUILD_TOOLS}"
    yes | "${sdkmanager}" --licenses >/dev/null 2>&1 || true
    "${sdkmanager}" "platform-tools" "platforms;android-${COMPILE_SDK}" "build-tools;${BUILD_TOOLS}" >/dev/null
  fi
}

ensure_sdk

# local.properties: unica fonte per Gradle sull'SDK
printf 'sdk.dir=%s\n' "${SDK_DIR}" > "${ANDROID_DIR}/local.properties"

echo
echo "--- build web + cap sync + vendor plugin ---"
cd "${FRONTEND}"
if [[ ! -d node_modules ]]; then
  npm ci || npm install
fi
npm run cap:sync

echo
echo "--- gradle ${GRADLE_TASK} ---"
cd "${ANDROID_DIR}"
chmod +x gradlew
./gradlew "${GRADLE_TASK}"

APK_PATH="${ANDROID_DIR}/${APK_REL}"
if [[ ! -f "${APK_PATH}" ]]; then
  echo "ERRORE: APK non trovato in ${APK_PATH}" >&2
  exit 1
fi

echo
echo "APK: ${APK_PATH}"

# Copia su Windows se siamo in WSL, così è installabile dal telefono/adb.exe
WIN_TARGET=""
if [[ -d /mnt/c ]]; then
  WIN_DIR="${ANDROID_APK_WIN_DIR:-/mnt/c/dev/kor35-apk}"
  mkdir -p "${WIN_DIR}"
  cp -f "${APK_PATH}" "${WIN_DIR}/${APK_NAME}"
  WIN_TARGET="${WIN_DIR}/${APK_NAME}"
  echo "Copia Windows: ${WIN_TARGET}"
fi

echo
echo "=============================================="
echo " APK pronto: ${APK_NAME}"
if [[ -n "${WIN_TARGET}" ]]; then
  win_display="$(printf '%s' "${WIN_TARGET}" | sed 's|/mnt/c|C:|; s|/|\\|g')"
  echo "   ${win_display}"
  echo
  echo " Installazione su telefono via USB (da PowerShell/cmd):"
  echo "   adb install -r ${win_display}"
  echo
  echo " Oppure copia il file sul telefono e aprilo."
fi
echo
echo " Niente Android Studio, niente copie doppie."
echo "=============================================="
