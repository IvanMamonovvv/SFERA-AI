# Шаг E0-07 — Общая docker-сеть с backend

**Статус:** TODO
**Слой:** DevOps · **Зависит от:** E0-06
**Перед началом:** прочитай `03_TDD.md`, раздел «Инфраструктура и сеть», вариант 1 —
уже согласовано владельцем 2026-08-25.

**⚠️ Затрагивает `docker-compose.staging.yml` другого репозитория (`sfera_backend`) и
боевой VPS. Владелец дал добро на этот конкретный пункт (2026-08-25) — но перед
фактическим выполнением на проде подтвердить ещё раз, что именно сейчас подходящее
время (downtime `db` при пересоздании сети — риск для backend). Не выполнять
автоматически вместе с остальными шагами эпика.**

## Цель

`db` платформы и AI-сервис подключены к одной именованной внешней docker-сети, порт
Postgres по-прежнему не торчит наружу VPS.

## Что сделать

**Step 1: Добавить именованную внешнюю сеть в `docker-compose.staging.yml` backend'а**

```yaml
services:
  db:
    networks:
      - default
      - ai_shared

networks:
  ai_shared:
    name: ai_shared
    external: true
```

Перед применением на VPS: `docker network create ai_shared` (один раз, вручную).

**Step 2: Применить на VPS**

Run (на VPS, по существующему деплой-скрипту `scripts/deploy-backend.sh` или вручную):
```bash
docker network create ai_shared || true
docker compose -f docker-compose.staging.yml up -d db
```
Expected: `db` пересоздан, подключён к `ai_shared`, backend/scheduler продолжают
работать (проверить `docker compose ps`, логи `backend`).

**Step 3: `docker-compose.yml` AI-сервиса (в `SFERA-AI`)**

```yaml
services:
  ai-service:
    build: .
    env_file: .env
    networks:
      - ai_shared

networks:
  ai_shared:
    name: ai_shared
    external: true
```

**Step 4: Commit (только AI-репозиторий)**

```bash
git add docker-compose.yml
git commit -m "chore: add docker-compose for AI service on shared network"
```

Правку `docker-compose.staging.yml` в `sfera_backend` коммитить и деплоить отдельно, в
том репозитории — не через этот шаг.

## Файлы

- Modify (в репозитории `sfera_backend`, не в `SFERA-AI`): `docker-compose.staging.yml`
- Create (в `SFERA-AI`): `docker-compose.yml`

## Критерии готовности (DoD)

- [ ] `ai_shared` сеть создана на VPS
- [ ] `db` пересоздан на новой сети, backend/scheduler работают без сбоев
- [ ] AI-сервис подключается к `db` по имени контейнера внутри `ai_shared`

## Как проверить

```bash
docker compose ps
docker compose logs backend --tail 50
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, подтверждение владельца перед прод-операцией>.
