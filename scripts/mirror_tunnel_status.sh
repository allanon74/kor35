#!/usr/bin/env bash
# Stato galleria sul Pi, oppure sul prod se MIRROR_TUNNEL_STATUS_ROLE=prod.
set -euo pipefail

ROLE="${MIRROR_TUNNEL_STATUS_ROLE:-pi}"

if [ "$ROLE" = "prod" ]; then
  echo "bridge: $(systemctl is-active kor35-prod-mirror-tunnel-bridge.service 2>/dev/null || echo assente)"
  echo "--- ascolto 18443 ---"
  ss -ltn | grep 18443 || echo "(nessun ascolto)"
  echo "--- health via galleria (localhost prod) ---"
  curl -kfsS --max-time 8 https://127.0.0.1:18443/api/healthz/ -H 'Host: mirror.kor35.it' \
    && echo || echo "galleria verso il Pi non risponde"
  exit 0
fi

echo "service: $(systemctl is-active kor35-mirror-tunnel.service 2>/dev/null || echo assente)"
echo "enabled: $(systemctl is-enabled kor35-mirror-tunnel.service 2>/dev/null || echo n/d)"
echo "--- journal ---"
journalctl -u kor35-mirror-tunnel.service -n 20 --no-pager || true
