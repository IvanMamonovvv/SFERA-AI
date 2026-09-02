#!/usr/bin/env bash
# scripts/tunnel-backend.sh
#
# Backend-контейнер публикует HTTP только внутри docker-сети `ai_shared` на VPS
# (внутреннее docker DNS-имя), поэтому с локальной машины `HHClient` падает на
# `[Errno 8] nodename nor servname provided` (E11-01, обнаружено 2026-09-01 на
# course_id=39). Туннель — по паттерну tunnel-platform-db.sh, в два прыжка:
#   1. на VPS поднимается временный socat-proxy контейнер внутри сети
#      ai_shared, публикующий backend-контейнер:8000 на 127.0.0.1:<PROXY_PORT>
#      (не наружу — только внутри самого VPS);
#   2. локально ssh -L пробрасывает localhost:<LOCAL_PORT> -> 127.0.0.1:<PROXY_PORT> на VPS.
# Proxy-контейнер удаляется по выходу (trap), в т.ч. при Ctrl+C — история с
# ai-db-tunnel-proxy, забытым висящим на VPS, не должна повториться.
#
# Идемпотентно: если LOCAL_PORT уже слушается, скрипт ничего не трогает и выходит.
#
# Имена контейнера/портов отдельные от db-туннеля (BACKEND_TUNNEL_PROXY vs
# ai-db-tunnel-proxy, 8001/18000 vs 5433/15432) — оба туннеля можно держать
# поднятыми одновременно.
#
# Не меняет .env/config.py — HH_BACKEND_BASE_URL подменяется через переменную
# окружения только при ручном локальном прогоне:
#   HH_BACKEND_BASE_URL=http://localhost:<LOCAL_PORT> uv run python ...
set -euo pipefail

LOCAL_PORT_CHECK="${LOCAL_PORT:-8001}"
if nc -z -w2 localhost "${LOCAL_PORT_CHECK}" 2>/dev/null; then
  echo "Туннель уже поднят на localhost:${LOCAL_PORT_CHECK} — ничего не делаю." >&2
  exit 0
fi

# Подтягиваем VPS_HOST/VPS_USER/VPS_PASSWORD/BACKEND_CONTAINER из .env, если не заданы в окружении.
if [ -f "$(dirname "$0")/../.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$(dirname "$0")/../.env"
  set +a
fi

VPS_HOST="${VPS_HOST:?set VPS_HOST}"
VPS_USER="${VPS_USER:?set VPS_USER}"
LOCAL_PORT="${LOCAL_PORT:-8001}"
PROXY_PORT="${PROXY_PORT:-18000}"
PROXY_NAME="ai-backend-tunnel-proxy"
# Имя backend-контейнера в сети ai_shared — меняется при пересоздании staging-стека.
BACKEND_CONTAINER="${BACKEND_CONTAINER:-sfera-staging-backend-1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

if [ -n "${VPS_PASSWORD:-}" ]; then
  SSH_CMD=(sshpass -e ssh)
  export SSHPASS="${VPS_PASSWORD}"
else
  SSH_CMD=(ssh)
fi

cleanup() {
  "${SSH_CMD[@]}" -o StrictHostKeyChecking=accept-new "${VPS_USER}@${VPS_HOST}" \
    "docker rm -f ${PROXY_NAME} >/dev/null 2>&1 || true"
}
trap cleanup EXIT

"${SSH_CMD[@]}" -o StrictHostKeyChecking=accept-new "${VPS_USER}@${VPS_HOST}" \
  "docker rm -f ${PROXY_NAME} >/dev/null 2>&1 || true; \
   docker run -d --rm --name ${PROXY_NAME} --network ai_shared \
    -p 127.0.0.1:${PROXY_PORT}:${BACKEND_PORT} alpine/socat \
    TCP-LISTEN:${BACKEND_PORT},fork,reuseaddr TCP:${BACKEND_CONTAINER}:${BACKEND_PORT}"

"${SSH_CMD[@]}" -N -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes \
  -L "${LOCAL_PORT}:127.0.0.1:${PROXY_PORT}" "${VPS_USER}@${VPS_HOST}"
