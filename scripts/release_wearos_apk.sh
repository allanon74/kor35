#!/usr/bin/env bash
set -euo pipefail

# Release helper APK Wear OS.
# - Build Gradle release APK
# - Copia app-release.apk nella cartella artefatti deployati dalla pipeline

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEAR_PROJECT_DIR="${ROOT_DIR}/extra/local-artifacts/wearos-kor35"
ARTIFACT_DIR="${ROOT_DIR}/extra/ota-artifacts/wearos-kor35"
SOURCE_APK="${WEAR_PROJECT_DIR}/app/build/outputs/apk/release/app-release.apk"
SOURCE_APK_UNSIGNED="${WEAR_PROJECT_DIR}/app/build/outputs/apk/release/app-release-unsigned.apk"
TARGET_APK="${ARTIFACT_DIR}/app-release.apk"
BOOTSTRAP_GRADLE_VERSION="${BOOTSTRAP_GRADLE_VERSION:-8.7}"

echo "==> KOR35 Wear OS APK release"
echo "Root: ${ROOT_DIR}"
echo "Project: ${WEAR_PROJECT_DIR}"

if [[ ! -d "${WEAR_PROJECT_DIR}" ]]; then
  echo "Errore: cartella progetto Wear OS non trovata: ${WEAR_PROJECT_DIR}"
  exit 1
fi

mkdir -p "${ARTIFACT_DIR}"

# Firma release (APK installabile): env WEAR_RELEASE_* oppure signing.env accanto al modulo Wear.
SIGNING_ENV="${WEAR_PROJECT_DIR}/signing.env"
if [[ -f "${SIGNING_ENV}" ]]; then
  echo "==> Carico firma da ${SIGNING_ENV}"
  set -a
  # shellcheck source=/dev/null
  source "${SIGNING_ENV}"
  set +a
fi
if [[ -z "${WEAR_RELEASE_STORE_FILE:-}" || -z "${WEAR_RELEASE_STORE_PASSWORD:-}" || -z "${WEAR_RELEASE_KEY_ALIAS:-}" ]]; then
  echo "WARN: Firma release non configurata (WEAR_RELEASE_* mancanti)."
  echo "    Senza keystore l'APK sarà unsigned e su device può fallire (INSTALL_PARSE_FAILED_NO_CERTIFICATES)."
  echo "    Vedi: extra/local-artifacts/wearos-kor35/signing.env.example"
fi

# Forza un JDK completo (con jlink) per AGP.
if [[ -z "${JAVA_HOME:-}" || ! -x "${JAVA_HOME}/bin/jlink" ]]; then
  for CANDIDATE in \
    "/usr/lib/jvm/java-17-openjdk-amd64" \
    "/usr/lib/jvm/java-21-openjdk-amd64"
  do
    if [[ -x "${CANDIDATE}/bin/jlink" ]]; then
      export JAVA_HOME="${CANDIDATE}"
      export PATH="${JAVA_HOME}/bin:${PATH}"
      break
    fi
  done
fi

if [[ -z "${JAVA_HOME:-}" || ! -x "${JAVA_HOME}/bin/jlink" ]]; then
  echo "Errore: JDK non valido. Serve un JDK con jlink (es. openjdk-17-jdk)."
  exit 1
fi

echo "JDK in uso: ${JAVA_HOME}"

echo "==> Build APK release..."
(
  cd "${WEAR_PROJECT_DIR}"
  if [[ -f "./gradlew" ]]; then
    chmod +x ./gradlew
    ./gradlew --no-daemon assembleRelease
  elif command -v gradle >/dev/null 2>&1; then
    gradle --no-daemon assembleRelease
  else
    echo "Gradle wrapper non trovato: avvio bootstrap locale Gradle ${BOOTSTRAP_GRADLE_VERSION}..."
    if ! command -v curl >/dev/null 2>&1; then
      echo "Errore: curl non trovato. Installa curl o genera gradlew da Android Studio."
      exit 1
    fi
    if ! command -v python3 >/dev/null 2>&1; then
      echo "Errore: python3 non trovato. Serve per estrarre Gradle bootstrap."
      exit 1
    fi
    TMP_DIR="$(mktemp -d "${ROOT_DIR}/.gradle-bootstrap.XXXXXX")"
    ZIP_PATH="${TMP_DIR}/gradle-${BOOTSTRAP_GRADLE_VERSION}-bin.zip"
    DIST_URLS=(
      "https://services.gradle.org/distributions/gradle-${BOOTSTRAP_GRADLE_VERSION}-bin.zip"
      "https://downloads.gradle.org/distributions/gradle-${BOOTSTRAP_GRADLE_VERSION}-bin.zip"
    )
    trap 'rm -rf "${TMP_DIR}"' EXIT
    DOWNLOADED=0
    for DIST_URL in "${DIST_URLS[@]}"; do
      if curl -fsSL "${DIST_URL}" -o "${ZIP_PATH}"; then
        DOWNLOADED=1
        break
      fi
    done
    if [[ "${DOWNLOADED}" -ne 1 ]]; then
      echo "Errore: download Gradle fallito. Verifica connessione internet o proxy."
      exit 1
    fi
    python3 - <<PY
import zipfile
zipfile.ZipFile("${ZIP_PATH}").extractall("${TMP_DIR}")
PY
    chmod +x "${TMP_DIR}/gradle-${BOOTSTRAP_GRADLE_VERSION}/bin/gradle" || true
    "${TMP_DIR}/gradle-${BOOTSTRAP_GRADLE_VERSION}/bin/gradle" --no-daemon wrapper
    chmod +x ./gradlew
    ./gradlew --no-daemon assembleRelease
  fi
)

APK_UNSIGNED_FALLBACK=0
if [[ ! -f "${SOURCE_APK}" ]]; then
  if [[ -f "${SOURCE_APK_UNSIGNED}" ]]; then
    SOURCE_APK="${SOURCE_APK_UNSIGNED}"
    APK_UNSIGNED_FALLBACK=1
  else
    echo "Errore: APK non trovato dopo build: ${SOURCE_APK}"
    echo "Controllati anche: ${SOURCE_APK_UNSIGNED}"
    exit 1
  fi
fi

if [[ "${APK_UNSIGNED_FALLBACK}" -eq 1 ]]; then
  echo "ATTENZIONE: in uso app-release-unsigned.apk (nessuna firma release configurata)." >&2
fi

cp -f "${SOURCE_APK}" "${TARGET_APK}"

echo "==> APK copiato:"
echo "    ${TARGET_APK}"
ls -lh "${TARGET_APK}"
echo "==> OK. Commit/push su main per distribuirlo su production + mirror."
