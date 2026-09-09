#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_PROJECT="sfera-ai"
BRANCH="${DEPLOY_BRANCH:-main}"
API_PORT="${API_PORT:-8000}"

compose() {
  docker compose -p "$COMPOSE_PROJECT" "$@"
}

cd "$PROJECT_DIR"

if [[ ! -f .env ]]; then
  echo "Ошибка: файл .env не найден в $PROJECT_DIR"
  echo "Создайте его из .env.example и задайте свои секреты."
  exit 1
fi

echo "==> Обновление из origin/$BRANCH..."
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> Сборка и запуск (ai-service + ai-scheduler)..."
# ВАЖНО: никогда не добавлять сюда --scale ai-scheduler=N>1 — планировщик
# должен быть ровно в одном экземпляре (docs/DEPLOYMENT.md, «Единственный
# инстанс планировщика»). Два тикающих процесса удваивают платные LLM-вызовы.
compose up -d --build

echo "==> Миграции (alembic upgrade head)..."
compose exec -T ai-service uv run alembic upgrade head

echo ""
echo "==> Статус контейнеров:"
compose ps

echo ""
echo "==> Проверка HTTP (ai-service):"
curl -sI --max-time 5 "http://127.0.0.1:${API_PORT}/health" | head -5 || true

echo ""
echo "==> Проверка, что ai-scheduler ровно один экземпляр:"
count=$(compose ps -q ai-scheduler | wc -l | tr -d ' ')
echo "ai-scheduler контейнеров: $count"
if [[ "$count" != "1" ]]; then
  echo "ОШИБКА: ожидался ровно 1 контейнер ai-scheduler, найдено $count. Проверьте compose-конфиг."
  exit 1
fi

echo ""
echo "Готово. API: http://127.0.0.1:${API_PORT}/"
