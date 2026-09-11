#!/bin/sh
# Relè TURN (WebRTC).
# LAN (Pi/ufficio): --lt-cred-mech + TURN_USERNAME/TURN_CREDENTIAL.
# Prod: TURN_AUTH_SECRET → REST/HMAC a tempo (stesso secret di Django).
set -eu

PORT="${TURN_PORT:-3478}"
REALM="${TURN_REALM:-kor35.local}"
MIN_PORT="${TURN_MIN_PORT:-49160}"
MAX_PORT="${TURN_MAX_PORT:-49259}"

if [ "${TURN_REQUIRE_AUTH_SECRET:-}" = "true" ] && [ -z "${TURN_AUTH_SECRET:-}" ]; then
  echo "TURN_AUTH_SECRET obbligatorio su questo nodo (niente credenziali statiche in pubblico)." >&2
  exit 1
fi

EXTRA=""
if [ -n "${TURN_EXTERNAL_IP:-}" ]; then
  EXTRA="${EXTRA} --external-ip=${TURN_EXTERNAL_IP}"
fi

if [ "${TURN_DENY_PRIVATE_PEERS:-}" = "true" ]; then
  EXTRA="${EXTRA} --denied-peer-ip=0.0.0.0-0.255.255.255"
  EXTRA="${EXTRA} --denied-peer-ip=10.0.0.0-10.255.255.255"
  EXTRA="${EXTRA} --denied-peer-ip=127.0.0.0-127.255.255.255"
  EXTRA="${EXTRA} --denied-peer-ip=169.254.0.0-169.254.255.255"
  EXTRA="${EXTRA} --denied-peer-ip=192.168.0.0-192.168.255.255"
  EXTRA="${EXTRA} --denied-peer-ip=172.16.0.0-172.31.255.255"
fi

if [ -n "${TURN_AUTH_SECRET:-}" ]; then
  AUTH="--use-auth-secret --static-auth-secret=${TURN_AUTH_SECRET}"
  if [ -n "${TURN_USER_QUOTA:-}" ]; then
    EXTRA="${EXTRA} --user-quota=${TURN_USER_QUOTA}"
  fi
  if [ -n "${TURN_TOTAL_QUOTA:-}" ]; then
    EXTRA="${EXTRA} --total-quota=${TURN_TOTAL_QUOTA}"
  fi
else
  USER="${TURN_USERNAME:-kor35turn}"
  PASS="${TURN_CREDENTIAL:-kor35turnlocal}"
  AUTH="--lt-cred-mech --user=${USER}:${PASS}"
fi

# Word-splitting di AUTH/EXTRA intenzionale (token senza spazi).
# shellcheck disable=SC2086
exec turnserver -n \
  --log-file=stdout \
  --pidfile=/tmp/turnserver.pid \
  --listening-port="${PORT}" \
  --fingerprint \
  --realm="${REALM}" \
  --no-cli \
  --no-tls \
  --no-dtls \
  --min-port="${MIN_PORT}" \
  --max-port="${MAX_PORT}" \
  ${AUTH} \
  ${EXTRA}
