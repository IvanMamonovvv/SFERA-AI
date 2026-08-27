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
#
# Идемпотентно: если LOCAL_PORT уже слушается (туннель поднят в другом запуске/сессии),
# скрипт ничего не трогает и просто выходит — не плодит второй ssh/прокси и не рискует
# оборвать чужую уже открытую сессию к БД.
#
# ВАЖНО: этот скрипт и всё, что через него подключается, не должно запускать
# `alembic downgrade` против этой БД — только `alembic upgrade head`. Staging делят
# несколько инструментов, downgrade реально дропает таблицы с данными (см. случай
# с ai_candidate_profile, project-context/sfera-ai/04_STATE.md). Откат проверять
# только на SQLite tmp_engine в тестах.
set -euo pipefail

LOCAL_PORT_CHECK="${LOCAL_PORT:-5433}"
if nc -z -w2 localhost "${LOCAL_PORT_CHECK}" 2>/dev/null; then
  echo "Туннель уже поднят на localhost:${LOCAL_PORT_CHECK} — ничего не делаю." >&2
  exit 0
fi

# Подтягиваем VPS_HOST/VPS_USER/VPS_PASSWORD/DB_CONTAINER из .env, если не заданы в окружении.
if [ -f "$(dirname "$0")/../.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$(dirname "$0")/../.env"
  set +a
fi

VPS_HOST="${VPS_HOST:?set VPS_HOST}"
VPS_USER="${VPS_USER:?set VPS_USER}"
LOCAL_PORT="${LOCAL_PORT:-5433}"
PROXY_PORT="${PROXY_PORT:-15432}"
PROXY_NAME="ai-db-tunnel-proxy"
# Имя контейнера БД в сети ai_shared — не имеет alias "db", берём реальное имя
# (docker ps --filter network=ai_shared на VPS), меняется при пересоздании staging-стека.
DB_CONTAINER="${DB_CONTAINER:-sfera-staging-db-1}"

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
    -p 127.0.0.1:${PROXY_PORT}:5432 alpine/socat \
    TCP-LISTEN:5432,fork,reuseaddr TCP:${DB_CONTAINER}:5432"

"${SSH_CMD[@]}" -N -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes \
  -L "${LOCAL_PORT}:127.0.0.1:${PROXY_PORT}" "${VPS_USER}@${VPS_HOST}"
