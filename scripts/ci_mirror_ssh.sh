#!/usr/bin/env bash
# SSH verso il mirror Pi per la CI.
#
# Prima prova kor35.ddns.net (rete di casa). Se non risponde, entra da www.kor35.it
# e usa la galleria: 127.0.0.1:18022 sulla produzione è la porta 22 del Pi.
# Così il deploy funziona anche quando il Pi è su un hotspot del telefono.
#
#   scripts/ci_mirror_ssh.sh probe
#   rsync -e "scripts/ci_mirror_ssh.sh" SRC user@host:DEST
#
# Variabili: HOST, USER, PORT (secret del DDNS), MIRROR_SSH_KEY_FILE,
# MIRROR_SSH_MODE_FILE, MIRROR_JUMP_HOST.
set -euo pipefail

KEY_FILE="${MIRROR_SSH_KEY_FILE:-${HOME}/.ssh/id_rsa}"
MODE_FILE="${MIRROR_SSH_MODE_FILE:-${GITHUB_WORKSPACE:-.}/.mirror-ssh-route}"
JUMP_HOST="${MIRROR_JUMP_HOST:-www.kor35.it}"
JUMP_USER="${MIRROR_JUMP_USER:-kor35-mirror-jump}"
JUMP_PORT="${MIRROR_JUMP_PORT:-22}"
TUNNEL_PORT="${MIRROR_TUNNEL_SSH_PORT:-18022}"

write_route() {
  local mode="$1" host="$2" port="$3" user="$4"
  umask 077
  cat > "$MODE_FILE" <<EOF
mode=${mode}
host=${host}
port=${port}
user=${user}
EOF
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
      echo "mode=${mode}"
      echo "host=${host}"
      echo "port=${port}"
      echo "user=${user}"
      if [ "$mode" = "tunnel" ]; then
        echo "proxy_host=${JUMP_HOST}"
        echo "proxy_user=${JUMP_USER}"
        echo "proxy_port=${JUMP_PORT}"
      else
        echo "proxy_host="
        echo "proxy_user="
        echo "proxy_port="
      fi
    } >> "$GITHUB_OUTPUT"
  fi
}

probe() {
  local direct_host="${HOST:?}"
  local direct_user="${USER:?}"
  local direct_port="${PORT:-10022}"
  mkdir -p "$(dirname "$KEY_FILE")"
  if ssh -i "$KEY_FILE" -o IdentitiesOnly=yes -o BatchMode=yes \
      -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
      -p "$direct_port" "${direct_user}@${direct_host}" true; then
    echo "SSH mirror: diretto ${direct_host}:${direct_port}"
    write_route direct "$direct_host" "$direct_port" "$direct_user"
    return 0
  fi
  echo "SSH mirror: ${direct_host}:${direct_port} non risponde, uso la galleria su ${JUMP_HOST}."
  if ! ssh -i "$KEY_FILE" -o IdentitiesOnly=yes -o BatchMode=yes \
      -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new \
      -o "ProxyCommand=ssh -i ${KEY_FILE} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -W %h:%p -p ${JUMP_PORT} ${JUMP_USER}@${JUMP_HOST}" \
      -p "$TUNNEL_PORT" "${direct_user}@127.0.0.1" true; then
    echo "Né il DDNS né la galleria SSH verso il Pi rispondono." >&2
    return 1
  fi
  write_route tunnel "127.0.0.1" "$TUNNEL_PORT" "$direct_user"
}

if [ "${1:-}" = "probe" ]; then
  probe
  exit 0
fi

if [ ! -f "$MODE_FILE" ]; then
  echo "Manca ${MODE_FILE}. Esegui prima: scripts/ci_mirror_ssh.sh probe" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$MODE_FILE"

if [ "${mode}" = "tunnel" ]; then
  exec ssh -i "$KEY_FILE" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
    -o "ProxyCommand=ssh -i ${KEY_FILE} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -W %h:%p -p ${JUMP_PORT} ${JUMP_USER}@${JUMP_HOST}" \
    -p "$TUNNEL_PORT" \
    "$@"
fi

exec ssh -i "$KEY_FILE" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
  -p "${port}" \
  "$@"
