# Деплой сервиса на VPS

> Эпик **E16** (`project-context/sfera-ai/05_EPICS.md`, `epics/E16-service-deployment/`).
> Найдено 2026-09-09: сервис ранее не имел постоянного процесса, разбирающего очередь
> `AIProcessingJob` — только API (FastAPI/uvicorn). Тик `run_tick` (`scheduler.py`, раз в
> 30 минут) нигде не запускался на проде/staging.

## Единственный инстанс планировщика — обязательное правило

`ai-scheduler` (тик очереди, платные LLM-вызовы) должен быть **ровно в одном экземпляре**.

- `build_scheduler()` (`src/sfera_ai/scheduler.py`) вызывается только из `if __name__ ==
  "__main__"` того же файла. **Не добавлять** повторный вызов в `api/app.py` (`lifespan`)
  или где-либо ещё — это вторая инициализация того же `BackgroundScheduler`, тики
  задвоятся внутри одного процесса.
- `docker-compose.yml` — сервис `ai-scheduler` без `deploy.replicas`/`--scale`. Деплой-скрипт
  (`scripts/deploy-ai-service.sh`) после запуска проверяет, что контейнер `ai-scheduler`
  ровно один, и падает с ошибкой, если это не так.
- Не поднимать `ai-scheduler` вручную `docker compose up -d --scale ai-scheduler=2` ни для
  какой цели (в т.ч. "на всякий случай для отказоустойчивости") — два процесса означают
  два независимых `CronTrigger`, тикающих по своим таймерам, что удваивает реальный
  AI-бюджет на курс. (Дедуп самих джоб на уровне БД — партиционный уникальный индекс
  `E5-07`/`SELECT ... FOR UPDATE SKIP LOCKED` в `process_batch` — не спасает от двойного
  порождения запросов к LLM в рамках одного и того же тика на разных процессах.)

## Состав сервиса

Один `docker-compose.yml`, два контейнера из одного образа (`Dockerfile`), разные команды:

| Контейнер | Команда | Роль |
|---|---|---|
| `ai-service` | `uvicorn sfera_ai.api.app:create_app --factory` | REST API для BFF-прокси `sfera_backend` |
| `ai-scheduler` | `python -m sfera_ai.scheduler` | Тик очереди раз в 30 минут + часовой requeue-cron + суточный PII-cron |

Оба — в общей внешней docker-сети `ai_shared` (та же, что и `sfera_backend`/`db` на VPS,
`03_TDD.md` → «Инфраструктура и сеть»).

## Первый деплой (сеть/роль ещё не заведены)

1. Убедиться, что внешняя сеть `ai_shared` создана на VPS (`docker network create ai_shared`,
   если ещё нет — обычно уже есть, см. `03_TDD.md`).
2. Убедиться, что роль `ai_readonly` на прод-Postgres создана и имеет нужные `GRANT SELECT`
   (`docs/LOCAL_DEV.md`).
3. На VPS: `git clone <репозиторий SFERA-AI>` в `/var/www/sfera-ai` (по аналогии с
   `/var/www/sphera-backend`).
4. `cp .env.example .env`, заполнить все переменные (см. «Переменные окружения» ниже).
5. Запустить `./scripts/deploy-ai-service.sh` — соберёт образ, поднимет оба контейнера,
   применит Alembic-миграции, проверит `/health` и единственность `ai-scheduler`.

## Обновление (день 2+)

```bash
./scripts/deploy-ai-service.sh
```

Скрипт сам: `git fetch/checkout/pull origin main` → `docker compose up -d --build` (оба
контейнера пересобираются и перезапускаются) → `alembic upgrade head` → healthcheck →
проверка единственности `ai-scheduler`. По образцу `sfera_backend/scripts/deploy-backend.sh`
и `SPHERA/scripts/deploy-frontend.sh` — тот же паттерн деплоя, что у бэкенда/фронтенда.

Переопределить ветку: `DEPLOY_BRANCH=feature-x ./scripts/deploy-ai-service.sh` (по умолчанию
`main`).

## Переменные окружения

В `.env` этого сервиса (полный список — `src/sfera_ai/config.py`):

- Уже существующие (не менялись эпиком E16): `platform_database_url`, `write_database_url`,
  `hh_backend_*`, `s3_*`, `openrouter_api_key`, `bff_shared_secret`.
- **Перед прод-запуском кнопки «Обработка кандидатов» (E15) явно выставить:**
  - `ai_processing_dry_run=False` — иначе реальный `fit_score` не считается, джобы просто
    закрываются `DONE` без AI-вызова.
  - `ai_processing_pilot_course_id` — `None` (без ограничения) или конкретный `course_id`
    (ограничить первый боевой прогон одним курсом) — решение владельца, не техническое.

В `.env` `sfera_backend` (другой репозиторий, правка требует отдельного разрешения на каждый
шаг по правилу проекта) — из `E15-07`:

- `SFERA_AI_SHARED_SECRET` — **обязан буквально совпадать** с `bff_shared_secret` этого
  сервиса, иначе прокси-эндпоинты `sfera_backend` получают 401 от SFERA-AI.
- `SFERA_AI_BASE_URL` — default `http://ai-service:8000` (docker DNS-имя контейнера
  `ai-service` внутри сети `ai_shared`).
- `SFERA_AI_REQUEST_TIMEOUT` — есть дефолт, обычно не трогать.

## Проверка после деплоя

```bash
docker compose -p sfera-ai ps                     # ai-service + ai-scheduler, оба Up
docker compose -p sfera-ai logs -f ai-scheduler    # "тик: поставлено N новых джоб" каждые ~30 мин
curl http://<host>:8000/health                     # {"status": "ok"}
```
