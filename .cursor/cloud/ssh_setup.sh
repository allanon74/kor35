#!/usr/bin/env bash
# Materializza chiave SSH e config per kor35-mirror / kor35-prod.
# Legge il secret Cloud Agent ID_DOCKER (chiave privata OpenSSH).
# Idempotente: sicuro da rieseguire a ogni boot.
set -euo pipefail

SSH_DIR="${HOME}/.ssh"
KEY_PATH="${SSH_DIR}/id_docker"
CONFIG_PATH="${SSH_DIR}/config"
KNOWN_HOSTS="${SSH_DIR}/known_hosts"

mkdir -p "${SSH_DIR}"
chmod 700 "${SSH_DIR}"

if [[ -z "${ID_DOCKER:-}" ]]; then
  echo "[kor35-cloud] WARN: secret ID_DOCKER assente — SSH mirror/prod non configurata." >&2
  exit 0
fi

# Scrivi chiave senza echo del contenuto
python3 - <<'PY'
import os
from pathlib import Path

key = os.environ["ID_DOCKER"].replace("\r\n", "\n").replace("\r", "\n")
if not key.endswith("\n"):
    key += "\n"
path = Path.home() / ".ssh" / "id_docker"
path.write_text(key)
path.chmod(0o600)
print(f"[kor35-cloud] chiave SSH scritta ({path.stat().st_size} byte)")
PY

# Config SSH (sovrascrive blocco gestito; lascia intatto il resto se presente)
python3 - <<'PY'
from pathlib import Path

marker_begin = "# BEGIN KOR35 CLOUD AGENT"
marker_end = "# END KOR35 CLOUD AGENT"
block = """# BEGIN KOR35 CLOUD AGENT
Host kor35-mirror
  HostName kor35.ddns.net
  User pi
  Port 10022
  IdentityFile ~/.ssh/id_docker
  IdentitiesOnly yes
  ServerAliveInterval 60
  ServerAliveCountMax 3

Host kor35-prod
  HostName www.kor35.it
  User deploy
  Port 22
  IdentityFile ~/.ssh/id_docker
  IdentitiesOnly yes
  ServerAliveInterval 60
  ServerAliveCountMax 3
# END KOR35 CLOUD AGENT
"""

path = Path.home() / ".ssh" / "config"
text = path.read_text() if path.exists() else ""
if marker_begin in text and marker_end in text:
    pre = text.split(marker_begin, 1)[0]
    post = text.split(marker_end, 1)[1]
    # drop leading newline after end marker if any
    if post.startswith("\n"):
        post = post[1:]
    text = pre.rstrip("\n") + ("\n" if pre.strip() else "") + block + post
else:
    if text and not text.endswith("\n"):
        text += "\n"
    text = text + ("\n" if text else "") + block

path.write_text(text)
path.chmod(0o600)
print("[kor35-cloud] ~/.ssh/config aggiornato (kor35-mirror, kor35-prod)")
PY

# known_hosts (best-effort; non fallire se rete down)
touch "${KNOWN_HOSTS}"
chmod 644 "${KNOWN_HOSTS}"
ssh-keyscan -p 10022 -H kor35.ddns.net >> "${KNOWN_HOSTS}" 2>/dev/null || true
ssh-keyscan -H www.kor35.it >> "${KNOWN_HOSTS}" 2>/dev/null || true

# Dedup known_hosts
if command -v sort >/dev/null; then
  sort -u "${KNOWN_HOSTS}" -o "${KNOWN_HOSTS}" 2>/dev/null || true
fi

if ssh-keygen -lf "${KEY_PATH}" >/dev/null 2>&1; then
  echo "[kor35-cloud] fingerprint: $(ssh-keygen -lf "${KEY_PATH}" | awk '{print $2}')"
else
  echo "[kor35-cloud] WARN: fingerprint chiave non leggibile" >&2
fi

echo "[kor35-cloud] SSH setup completato."
