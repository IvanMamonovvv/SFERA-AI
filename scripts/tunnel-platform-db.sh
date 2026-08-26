#!/usr/bin/env bash
# scripts/tunnel-platform-db.sh
#
# `db` не публикует порт на host VPS (только внутри docker-сети `ai_shared`,
# см. 03_TDD.md, раздел «Инфраструктура и сеть» — проброс на 127.0.0.1
# осознанно отклонён). Поэтому туннель идёт в два прыжка:
#   1. на VPS поднимается временный socat-proxy контейнер внутри сети
#      ai_shared, публикующий db:5432 на 127.0.0.1:<PROXY_PORT> (не наружу —
#      только внутри самого VPS);
#   2. локально ssh -L пробрасывает localhost:<LOCAL_PORT> -> 127.0.0.1:<PROXY_PORT> на VPS.
# Proxy-контейнер удаляется по выходу (trap), в т.ч. при Ctrl+C.
set -euo pipefail

VPS_HOST="${VPS_HOST:?set VPS_HOST}"
VPS_USER="${VPS_USER:?set VPS_USER}"
LOCAL_PORT="${LOCAL_PORT:-5433}"
PROXY_PORT="${PROXY_PORT:-15432}"
PROXY_NAME="ai-db-tunnel-proxy"

cleanup() {
  ssh "${VPS_USER}@${VPS_HOST}" "docker rm -f ${PROXY_NAME} >/dev/null 2>&1 || true"
}
trap cleanup EXIT

ssh "${VPS_USER}@${VPS_HOST}" \
  "docker run -d --rm --name ${PROXY_NAME} --network ai_shared \
    -p 127.0.0.1:${PROXY_PORT}:5432 alpine/socat \
    TCP-LISTEN:5432,fork,reuseaddr TCP:db:5432"

ssh -N -L "${LOCAL_PORT}:127.0.0.1:${PROXY_PORT}" "${VPS_USER}@${VPS_HOST}"
