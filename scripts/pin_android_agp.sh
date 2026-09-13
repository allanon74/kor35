#!/usr/bin/env bash
# Allinea AGP dei moduli Capacitor a quello dell'app.
#
# @capacitor/android 8.x dichiara AGP 8.13.0 (Android Studio Otter).
# Android Studio Ladybug/Meerkat sul PC di sviluppo arriva solo a 8.10.1.
# Dopo npm ci / cap sync i build.gradle in node_modules tornano a 8.13.0:
# questo script va rilanciato (make android-sync lo fa da solo).
#
# Uso:
#   ./scripts/pin_android_agp.sh
#   ANDROID_AGP_VERSION=8.10.1 ./scripts/pin_android_agp.sh [dir ...]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGP="${ANDROID_AGP_VERSION:-8.10.1}"

if (( $# == 0 )); then
  set -- "${ROOT}/frontend/node_modules/@capacitor"
fi

echo "Pin AGP ${AGP} in: $*"

found=0
while IFS= read -r -d '' file; do
  if grep -q 'com.android.tools.build:gradle:' "${file}"; then
    sed -i -E "s/com\\.android\\.tools\\.build:gradle:[0-9][0-9.]*/com.android.tools.build:gradle:${AGP}/g" "${file}"
    echo "  ${file}"
    found=1
  fi
done < <(find "$@" -name 'build.gradle' -print0 2>/dev/null)

if (( found == 0 )); then
  echo "WARN: nessun build.gradle Capacitor trovato sotto $*" >&2
fi
