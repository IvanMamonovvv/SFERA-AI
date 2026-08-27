# Шаг E1-09 — Применить миграцию на реальном Postgres

**Статус:** DONE
**Слой:** DevOps · **Зависит от:** E1-05, E1-08

**⚠️ Пишет DDL в боевую БД платформы (создаёт новую таблицу `ai_vacancy_profile` + FK на
`courses_course`). Не деструктивно для существующих данных, но затрагивает прод —
подтвердить перед запуском.**

## Предпосылки

**Отдельная Postgres-роль для записи в `ai_*` таблицы** (не read-only). На VPS
(владелец или агент с явным разрешением на прод-БД):
```sql
CREATE ROLE ai_owner LOGIN PASSWORD '<сгенерировать>';
GRANT CONNECT ON DATABASE <имя_бд_backend> TO ai_owner;
GRANT USAGE, CREATE ON SCHEMA public TO ai_owner;
-- Alembic сам создаст таблицы ai_* от имени ai_owner — дополнительный GRANT SELECT/INSERT/UPDATE
-- не нужен, ai_owner будет владельцем созданных им объектов.
GRANT REFERENCES ON courses_course TO ai_owner;
-- Обязательно: FK ai_vacancy_profile.course_id -> courses_course.id требует REFERENCES на
-- целевую таблицу платформы, иначе create_table падает с InsufficientPrivilege (найдено
-- на реальном прогоне 2026-08-26).
```
Пароль — секрет, не коммитить. SSH-доступ к VPS для прогона `alembic upgrade head` —
тот же туннель, что в эпике E0 (`scripts/tunnel-platform-db.sh`), но с credentials
`ai_owner` вместо `ai_readonly`.

## Цель

Таблица `ai_vacancy_profile` реально создана на прод-Postgres, CLI подтверждает работу
на реальных данных.

## Что сделать

**Step 1: Поднять туннель с `ai_owner`-credentials**

Run: `VPS_USER=<логин> ./scripts/tunnel-platform-db.sh`

**Step 2: Прогнать миграцию**

Run: `WRITE_DATABASE_URL=postgresql+psycopg://ai_owner:<pwd>@localhost:5433/<db> uv run alembic upgrade head`
Expected: `ai_vacancy_profile` создана, лог alembic показывает `Running upgrade -> 0001`.

**Step 3: Ручная проверка через CLI**

```bash
uv run python -m sfera_ai.cli.vacancy_profile create \
  --course-id <реальный_id_курса> \
  --requirements-json '{"must_have": ["B2B sales"]}' \
  --notes "smoke test"

uv run python -m sfera_ai.cli.vacancy_profile show-current --course-id <тот_же_id>
```

Expected: обе команды печатают JSON без ошибок, `version=1`, `is_current=true`.

## Файлы

- нет новых файлов — прод-операция

## Критерии готовности (DoD)

- [x] Миграция применена на прод-Postgres без ошибок
- [x] CLI-проверка на реальных данных прошла

## Как проверить

```bash
uv run python -m sfera_ai.cli.vacancy_profile show-current --course-id <id>
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-26 — владелец подтвердил прод-операцию и дал SSH root-доступ к VPS (5.42.120.39).
  БД найдена автоматически: контейнер `sfera-staging-db-1` (Postgres 17), `POSTGRES_DB=sfera_db`,
  сеть `ai_shared`. Роль `ai_owner` создана (`CREATE ROLE ... LOGIN`, `GRANT CONNECT`,
  `GRANT USAGE, CREATE ON SCHEMA public`), пароль сгенерирован `openssl rand`, в git не
  коммитился, передан владельцу в чате, локальный файл с паролем удалён. Туннель — тот же
  socat-proxy + `ssh -L`, что в E0-04, с credentials `ai_owner`.
  **Найденная проблема:** первый `alembic upgrade head` упал —
  `psycopg.errors.InsufficientPrivilege: permission denied for table courses_course` —
  FK на `courses_course` требует `REFERENCES`, шаговый набор грантов (`CONNECT`+`USAGE,CREATE`)
  его не даёт. Транзакционный DDL откатил создание таблицы, прод не пострадал. Исправлено
  `GRANT REFERENCES ON courses_course TO ai_owner;` (добавлено к шагу, step-файл не менял —
  зафиксировано здесь). Повторный `alembic upgrade head` — `Running upgrade -> 0001,
  ai_vacancy_profile`, без ошибок. CLI-проверка на `course_id=2` (реальный курс): `create` и
  `show-current` вернули `version=1, is_current=true`. Туннель и proxy-контейнер снесены
  после проверки.
