#!/usr/bin/env bash
# Riporta il branch corrente aggiornato rispetto a origin/main (dopo push diretti su main, ecc.).
#
# Uso:
#   ./scripts/realign_branch_to_main.sh           # merge di origin/main nel branch corrente
#   ./scripts/realign_branch_to_main.sh --hard    # il branch corrente diventa identico a origin/main (ATTENZIONE)
#
# Opzioni:
#   --hard     git reset --hard origin/main (perdi commit solo sul branch locale non ancora pushati altrove)
#   --yes      salta la conferma interattiva (solo con --hard)
#   --remote R default: origin
#   --main B   default: main

set -euo pipefail

REMOTE="origin"
MAIN_BRANCH="main"
HARD=0
SKIP_CONFIRM=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hard) HARD=1; shift ;;
    --yes) SKIP_CONFIRM=1; shift ;;
    --remote)
      REMOTE="${2:-}"
      if [[ -z "$REMOTE" ]]; then echo "Errore: --remote richiede un nome." >&2; exit 2; fi
      shift 2
      ;;
    --main)
      MAIN_BRANCH="${2:-}"
      if [[ -z "$MAIN_BRANCH" ]]; then echo "Errore: --main richiede un nome." >&2; exit 2; fi
      shift 2
      ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Argomento sconosciuto: $1 (usa --help)" >&2
      exit 2
      ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Errore: non sei in un repository git." >&2
  exit 1
fi

CURRENT="$(git branch --show-current 2>/dev/null || true)"
if [[ -z "$CURRENT" ]]; then
  echo "Errore: HEAD detached o nessun branch. Fai checkout del branch da riallineare (es. test)." >&2
  exit 1
fi

if ! git diff-index --quiet HEAD -- 2>/dev/null; then
  echo "Errore: working tree sporco. Committa o stash prima di proseguire." >&2
  exit 1
fi

echo "==> Fetch $REMOTE ..."
git fetch "$REMOTE"

REF_MAIN="${REMOTE}/${MAIN_BRANCH}"
if ! git rev-parse --verify "$REF_MAIN" >/dev/null 2>&1; then
  echo "Errore: ref non trovata: $REF_MAIN (controlla nome remote/branch)." >&2
  exit 1
fi

if [[ "$CURRENT" == "$MAIN_BRANCH" ]]; then
  echo "Sei già sul branch $MAIN_BRANCH. Per aggiornarlo da $REMOTE:"
  echo "  git pull $REMOTE $MAIN_BRANCH"
  exit 0
fi

if [[ "$HARD" -eq 1 ]]; then
  echo "ATTENZIONE: --hard esegue: git reset --hard $REF_MAIN"
  echo "         Branch corrente: $CURRENT → identico a $REF_MAIN"
  if [[ "$SKIP_CONFIRM" -ne 1 ]]; then
    read -r -p "Confermi? [y/N] " ans
    case "$ans" in
      y|Y|yes|YES) ;;
      *) echo "Annullato."; exit 1 ;;
    esac
  fi
  git reset --hard "$REF_MAIN"
  echo "==> Fatto. $CURRENT ora punta allo stesso commit di $REF_MAIN."
  exit 0
fi

echo "==> Merge $REF_MAIN → $CURRENT (i tuoi commit sul branch restano; in caso di conflitti risolvili a mano)"
git merge "$REF_MAIN" -m "chore: merge $REF_MAIN into $CURRENT (realign_branch_to_main)"

echo "==> Fatto. Branch $CURRENT aggiornato con le ultime modifiche da $MAIN_BRANCH."
