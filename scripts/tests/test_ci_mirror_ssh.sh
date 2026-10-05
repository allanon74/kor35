#!/usr/bin/env bash
# Il wrapper SSH della CI aggiunge porta e salto senza aprire connessioni vere.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/home/.ssh"
cat > "$TMP/bin/ssh" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" >> "$FAKE_SSH_LOG"
exit 0
EOF
chmod +x "$TMP/bin/ssh"
touch "$TMP/home/.ssh/id_rsa"

run_wrap() {
  FAKE_SSH_LOG="$TMP/ssh.log" \
  PATH="$TMP/bin:$PATH" \
  HOME="$TMP/home" \
  MIRROR_SSH_KEY_FILE="$TMP/home/.ssh/id_rsa" \
  MIRROR_SSH_MODE_FILE="$TMP/route" \
  "$ROOT/scripts/ci_mirror_ssh.sh" pi@127.0.0.1 true
  cat "$TMP/ssh.log"
  : > "$TMP/ssh.log"
}

printf 'mode=direct\nhost=kor35.ddns.net\nport=10022\nuser=pi\n' > "$TMP/route"
direct="$(run_wrap)"
printf '%s\n' "$direct" | grep -q -- '-p 10022'
printf '%s\n' "$direct" | grep -q 'pi@127.0.0.1'
if printf '%s\n' "$direct" | grep -q 'ProxyCommand'; then
  echo "la strada diretta non deve usare il salto" >&2
  exit 1
fi

printf 'mode=tunnel\nhost=127.0.0.1\nport=18022\nuser=pi\n' > "$TMP/route"
tunnel="$(run_wrap)"
printf '%s\n' "$tunnel" | grep -q -- '-p 18022'
printf '%s\n' "$tunnel" | grep -q 'kor35-mirror-jump@www.kor35.it'
printf '%s\n' "$tunnel" | grep -q '127.0.0.1:18022\|-p 18022'

echo "OK test_ci_mirror_ssh"
