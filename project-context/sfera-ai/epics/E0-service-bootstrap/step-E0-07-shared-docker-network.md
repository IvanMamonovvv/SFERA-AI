# Шаг E0-07 — Общая docker-сеть с backend

**Статус:** DONE
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

- [x] `ai_shared` сеть создана на VPS
- [x] `db` пересоздан на новой сети, backend/scheduler работают без сбоев
- [x] AI-сервис подключается к `db` по имени контейнера внутри `ai_shared`

## Как проверить

```bash
docker compose ps
docker compose logs backend --tail 50
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — владелец подтвердил прод-операцию ещё раз (сверх согласия 2026-08-25),
  дал SSH-доступ (root@VPS). Выполнено на VPS: `docker network create ai_shared`,
  правка `docker-compose.staging.yml` (сервис `db` → сети `default` + `ai_shared`,
  добавлен внешний `network: ai_shared`), `docker compose up -d db` — `db` пересоздан.
  Коммит в `sfera_backend` (репозиторий `FilinCold/sphera_backend`, ветка `main`)
  `e22bf9b`. **Инцидент по ходу:** после пересоздания `db` контейнер `scheduler`
  (APScheduler, долгоживущий процесс) не смог восстановить persistent DB-соединение —
  ошибки `OperationalError: server closed the connection unexpectedly` каждые 15-30с
  (сначала `Temporary failure in name resolution` в первые секунды, затем устойчиво
  эта ошибка). Проверка показала: DNS резолвит `db` правильно, свежее psycopg2-соединение
  из того же контейнера работает нормально (`SELECT 1` — OK) — проблема именно в
  закэшированном Django-соединении уже запущенного процесса. Исправлено рестартом
  контейнера `scheduler` (`docker compose restart scheduler`); после рестарта ошибок
  нет, jobs выполняются штатно. `backend`/`gateway` не перезапускались, не пострадали
  (HTTP 200 на `/api/v1/docs/` в течение всей операции — короткоживущие соединения per-request).
  Проверка сети: `docker run --rm --network ai_shared postgres:17 pg_isready -h db -p 5432`
  → `accepting connections`. В `SFERA-AI` создан `docker-compose.yml` для AI-сервиса
  на сети `ai_shared`, коммит `df01000`.
