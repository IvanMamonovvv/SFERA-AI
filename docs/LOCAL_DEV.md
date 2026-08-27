# Локальная разработка

## Подключение к БД платформы (read-only)

1. Убедиться, что read-only роль `ai_readonly` заведена на проде:
   ```sql
   CREATE ROLE ai_readonly LOGIN PASSWORD '<сгенерировать>';
   GRANT CONNECT ON DATABASE <имя_бд_backend> TO ai_readonly;
   GRANT USAGE ON SCHEMA public TO ai_readonly;
   GRANT SELECT ON courses_application, testchecks_answer, headhunter_hhnegotiationrecord,
     courses_course, courses_progress TO ai_readonly;
   -- Никаких GRANT INSERT/UPDATE/DELETE и никакого ALTER DEFAULT PRIVILEGES.
   ```
   Пароль — секрет, не коммитить. Список таблиц расширять по мере того как новые
   эпики реально начинают читать новые таблицы, не выдавать доступ заранее.
2. БД платформы не публикует порт на host VPS — только внутри docker-сети `ai_shared`
   (см. `project-context/sfera-ai/03_TDD.md`, раздел «Инфраструктура и сеть»).
   Скрипт сам поднимает временный socat-proxy контейнер на VPS внутри `ai_shared`
   и прокидывает его на localhost через `ssh -L`; данные для подключения к серверу
   (`VPS_HOST`/`VPS_USER`/`VPS_PASSWORD`) он берёт из `.env` (не коммитится) —
   один раз вписать туда, дальше просто:
   ```bash
   ./scripts/tunnel-platform-db.sh
   ```
   Держать терминал открытым, пока идёт работа с БД; `Ctrl+C` удаляет proxy-контейнер.
   Если имя контейнера БД на VPS изменится (пересоздание staging-стека) — переопределить
   `DB_CONTAINER` (по умолчанию `sfera-staging-db-1`).
3. Скопировать `.env.example` в `.env`, подставить пароль `ai_readonly` и имя БД, порт `5433`.
4. `uv run python -m sfera_ai.smoke_test <application_id>`
