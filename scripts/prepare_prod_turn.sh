#!/usr/bin/env bash
# Prepara TURN su nodo prod: secret HMAC in .env.prod, IP pubblico, porte ufw.
# Eseguire SUL droplet (utente deploy) oppure: ssh kor35-prod 'sudo bash -s' < scripts/prepare_prod_turn.sh
set -euo pipefail

ENV_FILE="${KOR35_BACKEND_ENV_FILE:-/srv/kor35/backend/.env.prod}"
EXTERNAL_IP="${TURN_EXTERNAL_IP_OVERRIDE:-}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Manca $ENV_FILE" >&2
  exit 1
fi

if [[ -z "$EXTERNAL_IP" ]]; then
  EXTERNAL_IP="$(ip -4 -o addr show scope global 2>/dev/null | awk '/eth0/ {print $4}' | cut -d/ -f1 | head -n1 || true)"
fi
if [[ -z "$EXTERNAL_IP" ]]; then
  EXTERNAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

python3 - "$ENV_FILE" "$EXTERNAL_IP" <<'PY'
import datetime, pathlib, re, secrets, shutil, sys

env_path = pathlib.Path(sys.argv[1])
external_ip = (sys.argv[2] or "").strip()
text = env_path.read_text()
backup = env_path.with_name(env_path.name + ".bak-turn-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
shutil.copy2(env_path, backup)


def get(key: str):
    m = re.search(rf"^{re.escape(key)}=(.*)$", text, re.M)
    if not m:
        return None
    return m.group(1).strip().strip("\"'\t ")


def upsert(key: str, value: str, only_if_empty: bool = False) -> str:
    global text
    cur = get(key)
    if only_if_empty and cur:
        return "kept"
    line = f"{key}={value}"
    if re.search(rf"^{re.escape(key)}=", text, re.M):
        text = re.sub(rf"^{re.escape(key)}=.*$", line, text, count=1, flags=re.M)
        return "replaced"
    if not text.endswith("\n"):
        text += "\n"
    text += line + "\n"
    return "added"


actions = {}
if get("TURN_AUTH_SECRET"):
    actions["TURN_AUTH_SECRET"] = "kept"
else:
    upsert("TURN_AUTH_SECRET", secrets.token_hex(32))
    actions["TURN_AUTH_SECRET"] = "generated"

if external_ip:
    actions["TURN_EXTERNAL_IP"] = upsert("TURN_EXTERNAL_IP", external_ip, only_if_empty=True)
else:
    actions["TURN_EXTERNAL_IP"] = "skipped-no-ip"

if get("TURN_CREDENTIAL_TTL") in (None, ""):
    actions["TURN_CREDENTIAL_TTL"] = upsert("TURN_CREDENTIAL_TTL", "28800")
else:
    actions["TURN_CREDENTIAL_TTL"] = "kept"

env_path.write_text(text)
print("backup", backup.name)
for key, status in actions.items():
    print(key, status)
print("TURN_EXTERNAL_IP", get("TURN_EXTERNAL_IP") or "")
print("TURN_AUTH_SECRET_len", len(get("TURN_AUTH_SECRET") or ""))
PY

if command -v ufw >/dev/null 2>&1; then
  sudo -n ufw allow 3478/udp comment "KOR35 TURN" || true
  sudo -n ufw allow 3478/tcp comment "KOR35 TURN" || true
  sudo -n ufw allow 49160:49259/udp comment "KOR35 TURN relay" || true
  sudo -n ufw status numbered | head -n 40
else
  echo "ufw non trovato: apri a mano 3478/udp, 3478/tcp, 49160:49259/udp"
fi
