# Шаг E2-07 — Применить миграцию на реальном Postgres

**Статус:** DONE
**Слой:** DevOps · **Зависит от:** E2-03, E2-06

**⚠️ Пишет DDL в боевую БД платформы (создаёт таблицу `ai_candidate_profile` + FK на
`courses_application`/`headhunter_hhnegotiationrecord`). Не деструктивно для
существующих данных, но затрагивает прод — подтвердить перед запуском.**

## Цель

Таблица `ai_candidate_profile` реально создана на прод-Postgres, backfill прогнан на
реальных данных без дублей.

## Что сделать

**Step 1: Поднять туннель с `ai_owner`-credentials**

Run: `VPS_USER=<логин> ./scripts/tunnel-platform-db.sh`

**Step 2: Прогнать миграцию**

Run: `WRITE_DATABASE_URL=postgresql+psycopg://ai_owner:<pwd>@localhost:5433/<db> uv run alembic upgrade head`
Expected: `ai_candidate_profile` создана, лог alembic показывает `Running upgrade
0001 -> 0002`.

**Step 3: Прогнать backfill (E2-06) на реальных данных**

Expected: без исключений, без дублей (см. E2-06).

## Файлы

- нет новых файлов — прод-операция

## Критерии готовности (DoD)

- [x] Миграция применена на прод-Postgres без ошибок
- [x] Backfill прогнан на реальных данных без дублей

## Как проверить

```bash
uv run python -m sfera_ai.cli.backfill_candidate_profiles
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-26 — миграция 0002 (`ai_candidate_profile`) применена на прод-Postgres,
  backfill (E2-06) прогнан на реальных данных. Владелец дал явное разрешение на
  каждую отдельную прод-операцию по ходу (туннель, сброс паролей, GRANT).

  **Инциденты по пути (не связаны с самим кодом миграции/backfill):**
  1. Контейнер `sfera-staging-db-1` оказался отключён от сети `ai_shared`
     (подключался в E0-07, но слетело при пересоздании контейнера) — переподключил
     `docker network connect ai_shared sfera-staging-db-1` (владелец подтвердил).
     На этой сети у него нет DNS-алиаса `db` (только `sfera-staging-db-1`) —
     socat-прокси в `scripts/tunnel-platform-db.sh` жёстко ссылается на `db`;
     пересоздал прокси-контейнер вручную с целью `TCP:sfera-staging-db-1:5432`.
     Скрипт стоит поправить на будущее (не сделано в рамках этого шага).
  2. `.env` на машине разработчика содержал не реальные прод-креды, а
     локальные дефолты/плейсхолдеры (`postgres@localhost:5434/sfera_ai_dev`,
     часть строк не заполнена). Реальных паролей `ai_owner`/`ai_readonly` от
     E1-09/E0-04 под рукой не оказалось — сбросил обе роли через `ALTER ROLE
     ... PASSWORD` (root-доступ на VPS, подтверждено владельцем), новые пароли
     переданы владельцу для `.env`.
  3. Не хватало `GRANT REFERENCES` на `courses_application`,
     `headhunter_hhnegotiationrecord` для `ai_owner` (нужно для FK в миграции —
     тот же класс проблемы, что в E1-09) и `GRANT SELECT` на
     `headhunter_hhnegotiationrecord` для `ai_readonly` (таблица читается
     впервые с эпика E2, грант не выдавался). Оба гранта выданы (подтверждено
     владельцем).

  После починки: `alembic upgrade head` — `Running upgrade 0001 -> 0002`, без
  ошибок. Backfill — `OK: processed 3461 platform records, 0 platform writes`.
  Прод не пострадал — все изменения аддитивные (новая таблица, новые гранты,
  новые пароли служебных ролей AI-сервиса), данные платформы не менялись.
  Туннель и прокси-контейнер снесены после проверки.
