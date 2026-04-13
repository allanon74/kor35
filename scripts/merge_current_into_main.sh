#!/usr/bin/env bash
set -euo pipefail

# Esegue il merge del branch corrente in main con conferma esplicita.
# Uso:
#   ./scripts/merge_current_into_main.sh
#   ./scripts/merge_current_into_main.sh --push

DO_PUSH=false

while [ $# -gt 0 ]; do
  case "$1" in
    --push)
      DO_PUSH=true
      shift
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      echo "Uso: $0 [--push]" >&2
      exit 1
      ;;
  esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Errore: non sei dentro una repository git." >&2
  exit 1
fi

CURRENT_BRANCH="$(git branch --show-current)"
TARGET_BRANCH="main"

if [ -z "$CURRENT_BRANCH" ]; then
  echo "Errore: impossibile determinare il branch corrente (HEAD detached?)." >&2
  exit 1
fi

if [ "$CURRENT_BRANCH" = "$TARGET_BRANCH" ]; then
  echo "Sei gia' su '$TARGET_BRANCH': nessun merge da eseguire." >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Errore: working tree non pulita. Committa/stasha prima di continuare." >&2
  exit 1
fi

if ! git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
  echo "Errore: branch locale '$TARGET_BRANCH' non trovato." >&2
  exit 1
fi

echo "Stai per eseguire:"
echo "  merge di '$CURRENT_BRANCH' in '$TARGET_BRANCH'"
if [ "$DO_PUSH" = true ]; then
  echo "  push di '$TARGET_BRANCH' su 'origin'"
fi
echo
read -r -p "Confermi? [y/N] " CONFIRM

case "$CONFIRM" in
  y|Y|yes|YES)
    ;;
  *)
    echo "Operazione annullata."
    exit 0
    ;;
esac

echo "Checkout di '$TARGET_BRANCH'..."
git checkout "$TARGET_BRANCH"

echo "Merge di '$CURRENT_BRANCH' in '$TARGET_BRANCH'..."
git merge "$CURRENT_BRANCH"

if [ "$DO_PUSH" = true ]; then
  echo "Push di '$TARGET_BRANCH' su 'origin'..."
  git push origin "$TARGET_BRANCH"
fi

echo "Merge completato con successo."
