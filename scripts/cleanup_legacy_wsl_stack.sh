#!/usr/bin/env bash
set -euo pipefail

# Rimuove i container legacy della vecchia stack WSL (prefisso kor35_wsl_).
# Opzioni:
#   --dry-run   mostra i container trovati senza rimuoverli

DRY_RUN=false

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Opzione non riconosciuta: $1" >&2
      echo "Uso: $0 [--dry-run]" >&2
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "docker non trovato. Installa Docker e riprova." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon non raggiungibile. Avvia Docker e riprova." >&2
  exit 1
fi

mapfile -t LEGACY_CONTAINERS < <(docker ps -a --format '{{.Names}}' | awk '/^kor35_wsl_/ { print }')

if [ "${#LEGACY_CONTAINERS[@]}" -eq 0 ]; then
  echo "Nessun container legacy trovato (prefisso: kor35_wsl_)."
  exit 0
fi

echo "Container legacy trovati:"
printf ' - %s\n' "${LEGACY_CONTAINERS[@]}"

if [ "$DRY_RUN" = true ]; then
  echo "Dry-run attivo: nessuna rimozione eseguita."
  exit 0
fi

echo "Rimozione container legacy in corso..."
docker rm -f "${LEGACY_CONTAINERS[@]}"
echo "Cleanup completato."
