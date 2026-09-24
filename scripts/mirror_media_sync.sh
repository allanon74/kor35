#!/usr/bin/env bash
set -uo pipefail

# Sync media mirror: push (best-effort) poi pull obbligatorio.
#
# Il push verso master può fallire per permessi su directory legacy (es. path
# social/profiles annidati di proprietà root). Non deve bloccare il pull:
# altrimenti il timer kor35-mirror-media-sync lascia il Pi senza file nuovi
# (rubriche, post, wiki) e le immagini restano 404.
#
# Uso:
#   ./scripts/mirror_media_sync.sh
#   make -C /home/pi/kor35-replica  (via unit systemd)
#
# Exit code: quello del pull. Se il push fallisce viene stampato un WARN
# ma non determina l'exit (salvo che anche il pull fallisca).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "=== Mirror media sync: push (best-effort) ==="
push_rc=0
if ! make sync-media-push; then
  push_rc=$?
  echo "WARN: sync-media-push fallito (exit ${push_rc}). Continuo con pull da master." >&2
fi

echo "=== Mirror media sync: pull (obbligatorio) ==="
make sync-media
pull_rc=$?

if [ "$push_rc" -ne 0 ]; then
  echo "WARN: push aveva fallito (exit ${push_rc}); pull exit=${pull_rc}." >&2
fi

exit "$pull_rc"
