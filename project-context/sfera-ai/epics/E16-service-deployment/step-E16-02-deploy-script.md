# Шаг E16-02 — deploy-скрипт по образцу backend/frontend

**Статус:** DONE
**Слой:** Infra · **Зависит от:** E16-01
**Перед началом:** прочитай `sfera_backend/scripts/deploy-backend.sh`,
`SPHERA/scripts/deploy-frontend.sh` (образец паттерна), новый `scripts/deploy-ai-service.sh`.

## Цель

Деплой SFERA-AI на VPS — той же командой и тем же паттерном, что уже используется для
`sfera_backend`/`SPHERA`: один скрипт, который сам обновляется из `origin/main` и
пересобирает контейнеры — не набор ручных команд.

## Что сделать

1. `scripts/deploy-ai-service.sh` — `git fetch/checkout/pull origin main` →
   `docker compose up -d --build` → `alembic upgrade head` внутри `ai-service` → healthcheck
   `/health` → явная проверка, что `ai-scheduler` поднят ровно в одном экземпляре
   (`docker compose ps -q ai-scheduler | wc -l`), падает с ошибкой, если не 1.
2. Ветка деплоя переопределяема `DEPLOY_BRANCH` (default `main`), порт API — `API_PORT`
   (default `8000`) — тот же паттерн переменных, что в `deploy-backend.sh`.

## Файлы

- `scripts/deploy-ai-service.sh` — новый.

## Критерии готовности (DoD)

- [x] Скрипт исполняемый (`chmod +x`).
- [x] Проверяет наличие `.env` перед стартом, иначе понятная ошибка вместо падения на
  середине.
- [x] Проверяет единственность `ai-scheduler` после подъёма — жёстко (`exit 1`), не
  предупреждением.
- [x] Не содержит `--scale` ни в каком виде.

## Как проверить

```bash
bash -n scripts/deploy-ai-service.sh   # синтаксис скрипта корректен
shellcheck scripts/deploy-ai-service.sh   # если установлен, не обязательный гейт
```

Живой прогон на VPS — на первом реальном деплое (не выполнялся в этой сессии, нет доступа
поднимать прод-контейнеры без отдельного запроса владельца).

## Журнал

- `2026-09-09` — выполнено. Паттерн скопирован с `deploy-backend.sh`/`deploy-frontend.sh`
  (git pull main → compose up -d --build → миграции → healthcheck → статус). Отличие от
  backend-скрипта — доп. проверка `count(ai-scheduler) == 1` в конце, специфичная для этого
  сервиса (E16-01). Живой прогон на VPS не выполнялся — ждёт решения владельца о первом
  деплое (`docs/DEPLOYMENT.md`, «Первый деплой»).
