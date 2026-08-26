# Шаг E0-04 — SSH-туннель для локальной разработки (документация + helper-скрипт)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** —
**Перед началом:** прод-Postgres не торчит наружу (`03_TDD.md`, раздел «Инфраструктура
и сеть»). Для локального smoke-теста нужен временный проброс порта через SSH на VPS
Timeweb.

## Предпосылки

**Read-only Postgres-роль для AI-сервиса.** На VPS (владелец или агент с явным
разрешением на прод-БД):
```sql
CREATE ROLE ai_readonly LOGIN PASSWORD '<сгенерировать>';
GRANT CONNECT ON DATABASE <имя_бд_backend> TO ai_readonly;
GRANT USAGE ON SCHEMA public TO ai_readonly;
GRANT SELECT ON courses_application, testchecks_answer, headhunter_hhnegotiationrecord,
  courses_course, courses_progress TO ai_readonly;
-- Никаких GRANT INSERT/UPDATE/DELETE и никакого ALTER DEFAULT PRIVILEGES — иначе новые
-- таблицы платформы автоматически станут доступны на запись.
```
Пароль — секрет, не коммитить. Список таблиц в `GRANT SELECT` — минимально необходимый
на момент E0 (`courses_application`, `testchecks_answer`); расширять по мере того как
новые эпики реально начинают читать новые таблицы, не выдавать доступ заранее.

## Цель

Есть скрипт и инструкция, позволяющие локально пробросить порт до `db` на VPS без
открытия Postgres в интернет.

## Что сделать

**Step 1: Написать скрипт туннеля**

```bash
#!/usr/bin/env bash
# scripts/tunnel-platform-db.sh
# Пробрасывает localhost:5433 -> db:5432 внутри docker-сети на VPS.
# Требует: SSH-доступ к прод-VPS (IP — в приватном .env/секретах, не в этом скрипте —
# см. docs/LOCAL_DEV.md), контейнер db слушает 5432 внутри compose-сети.
set -euo pipefail

VPS_HOST="${VPS_HOST:?set VPS_HOST}"
VPS_USER="${VPS_USER:?set VPS_USER}"
LOCAL_PORT="${LOCAL_PORT:-5433}"

ssh -N -L "${LOCAL_PORT}:localhost:5432" "${VPS_USER}@${VPS_HOST}"
```

Примечание: если `db` не публикует порт даже на `127.0.0.1` внутри VPS (по умолчанию не
публикует, см. `03_TDD.md`), туннель нужно тянуть до контейнера через `docker exec`/
`socat` внутри VPS, либо сначала выполнить E0-07 (проброс `127.0.0.1:5432` в
`docker-compose.staging.yml`). Уточнить точный путь при выполнении шага — это первый
пункт, который может потребовать решения на месте, не чисто механический.

**Step 2: `chmod +x`**

Run: `chmod +x scripts/tunnel-platform-db.sh`

**Step 3: Написать `docs/LOCAL_DEV.md`**

```markdown
# Локальная разработка

## Подключение к БД платформы (read-only)

1. Убедиться, что read-only роль `ai_readonly` заведена на проде (см. «Предпосылки»
   выше в этом файле).
2. В одном терминале: `VPS_HOST=<прод-IP, спросить у владельца> VPS_USER=<ssh-логин>
   ./scripts/tunnel-platform-db.sh`
3. Скопировать `.env.example` в `.env`, подставить пароль `ai_readonly` и имя БД, порт `5433`.
4. `uv run python -m sfera_ai.smoke_test <application_id>`
```

**Step 4: Commit**

```bash
git add scripts/tunnel-platform-db.sh docs/LOCAL_DEV.md
git commit -m "docs: add SSH tunnel script and local dev instructions"
```

## Файлы

- `scripts/tunnel-platform-db.sh` — создать
- `docs/LOCAL_DEV.md` — создать

## Критерии готовности (DoD)

- [x] Роль `ai_readonly` реально создана на проде (DDL из «Предпосылки»), не superuser и
      не совпадает с владельцем БД (`sfera_app`) — фактическая проверка на E0-05
      (write упал `permission denied`, подтверждено).
- [x] Скрипт исполняемый (`chmod +x`)
- [x] `docs/LOCAL_DEV.md` описывает полный путь до рабочего локального подключения

## Как проверить

```bash
VPS_HOST=<прод-IP> VPS_USER=<логин> ./scripts/tunnel-platform-db.sh
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — реализованы `scripts/tunnel-platform-db.sh` и `docs/LOCAL_DEV.md`.
  Т.к. `03_TDD.md` фиксирует выбор общей docker-сети `ai_shared` (без публикации `db`
  на host VPS), туннель сделан в два прыжка: временный socat-proxy контейнер в сети
  `ai_shared` на VPS (публикует `db:5432` только на `127.0.0.1` VPS) + `ssh -L` с
  локальной машины поверх него; удаляется по выходу (trap). Владелец подтвердил этот
  вариант вместо простого `ssh -L` (был бы возможен только после E0-07). Коммит
  `d6a140e`.
- `2026-08-26` — роль `ai_readonly` создана на проде (владелец дал явное разрешение,
  подтвердил, что роль ранее не создавалась). DDL из «Предпосылки» выполнен без
  изменений: `LOGIN`, `CONNECT` на `sfera_db`, `USAGE` на `public`, `SELECT` только на
  `courses_application`/`testchecks_answer`. Пароль сгенерирован (`openssl rand`),
  передан владельцу отдельно, в git не попал. Перед изменением схемы снят полный
  `pg_dump` бэкап `sfera_db` (детали — журнал `step-E0-05-smoke-test.md`). Реальный
  прогон smoke-теста подтвердил write-запрет — см. журнал E0-05.
