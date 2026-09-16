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

# Serve un JDK completo: con il solo runtime (JRE) Gradle fallisce con
# "Toolchain installation ... does not provide the required capabilities: [JAVA_COMPILER]".
detect_jdk_home() {
  if [[ -n "${JAVA_HOME:-}" && -x "${JAVA_HOME}/bin/javac" ]]; then
    printf '%s' "${JAVA_HOME}"
    return 0
  fi

  if command -v javac >/dev/null 2>&1; then
    local javac_path
    javac_path="$(readlink -f "$(command -v javac)")"
    printf '%s' "$(dirname "$(dirname "${javac_path}")")"
    return 0
  fi

  # Preferisci 25/21/17 (AGP 8.13 richiede JDK 17+).
  local version dir
  for version in 25 21 17; do
    for dir in /usr/lib/jvm/*"${version}"*/; do
      if [[ -x "${dir}bin/javac" ]]; then
        printf '%s' "${dir%/}"
        return 0
      fi
    done
  done
  for dir in /usr/lib/jvm/*/; do
    if [[ -x "${dir}bin/javac" ]]; then
      printf '%s' "${dir%/}"
      return 0
    fi
  done
  return 1
}

APT_JDK_PACKAGE="openjdk-21-jdk-headless"

install_jdk_with_apt() {
  command -v apt-get >/dev/null 2>&1 || return 1
  command -v sudo >/dev/null 2>&1 || return 1
  echo "Installo ${APT_JDK_PACKAGE} (sudo può chiedere la password)…"
  sudo apt-get update -qq || return 1
  sudo apt-get install -y "${APT_JDK_PACKAGE}" || return 1
  return 0
}

if ! JDK_HOME="$(detect_jdk_home)"; then
  echo "Nessun JDK con compilatore (javac): serve il JDK, non il solo runtime."
  if command -v java >/dev/null 2>&1; then
    echo "Runtime presente: $(java -version 2>&1 | head -1)"
  fi

  if [[ "${ANDROID_APK_NO_APT:-0}" != "1" ]] && install_jdk_with_apt; then
    JDK_HOME="$(detect_jdk_home)" || true
  fi

  if [[ -z "${JDK_HOME:-}" ]]; then
    echo >&2
    echo "ERRORE: installa un JDK e ripeti:" >&2
    echo "  sudo apt update && sudo apt install -y ${APT_JDK_PACKAGE}" >&2
    exit 1
  fi
fi

if [[ ! -x "${JDK_HOME}/bin/javac" ]]; then
  echo "ERRORE: ${JDK_HOME} non contiene bin/javac (installazione JDK incompleta)." >&2
  echo "  sudo apt install --reinstall -y ${APT_JDK_PACKAGE}" >&2
  exit 1
fi

export JAVA_HOME="${JDK_HOME}"
export PATH="${JAVA_HOME}/bin:${PATH}"
echo "JDK      : ${JAVA_HOME} ($("${JAVA_HOME}/bin/javac" -version 2>&1))"

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

# AGP chiede una *toolchain* Java: se un demone Gradle è stato avviato con un JRE
# (o con una detection cached) resta convinto che il JDK non abbia il compilatore
# → "does not provide the required capabilities: [JAVA_COMPILER]".
# Demone fermato + installazione dichiarata esplicitamente = detection pulita.
./gradlew --stop >/dev/null 2>&1 || true

GRADLE_LOG="$(mktemp)"
trap 'rm -f "${GRADLE_LOG}"' EXIT

run_gradle() {
  set +e
  ./gradlew "${GRADLE_TASK}" \
    "-Dorg.gradle.java.home=${JAVA_HOME}" \
    "-Porg.gradle.java.installations.paths=${JAVA_HOME}" \
    "-Dorg.gradle.java.installations.paths=${JAVA_HOME}" \
    "-Dorg.gradle.java.installations.auto-detect=false" \
    "-Dorg.gradle.java.installations.auto-download=false" 2>&1 | tee "${GRADLE_LOG}"
  local rc=${PIPESTATUS[0]}
  set -e
  return "${rc}"
}

if ! run_gradle; then
  # Gradle memorizza le capability dei JVM in ~/.gradle/caches/<ver>/jvms:
  # una voce stantia (rilevata quando c'era solo il JRE) sopravvive ai riavvii
  # del demone. Ripulisci e riprova una volta.
  if grep -q 'JAVA_COMPILER' "${GRADLE_LOG}"; then
    echo
    echo "Cache JVM di Gradle non valida per ${JAVA_HOME}: la ripulisco e riprovo…"
    ./gradlew --stop >/dev/null 2>&1 || true
    rm -rf "${HOME}"/.gradle/caches/*/jvms
    run_gradle
  else
    exit 1
  fi
fi

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
