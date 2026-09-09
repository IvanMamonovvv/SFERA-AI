# Локальная разработка

## SSH-доступ к VPS (staging)

Один VPS хостит несколько сервисов сразу — не только SFERA-AI. Прямой доступ (не
туннель, а полноценный shell) настроен через алиас в `~/.ssh/config`:

```
Host sfera
    HostName 5.42.120.39
    User root
    Port 44122
    IdentityFile ~/.ssh/id_rsa
    IdentitiesOnly yes
```

Подключение: `ssh sfera`. Порт нестандартный — **44122**, не 22 (скрипты
`scripts/tunnel-*.sh` в `.env` до сих пор ссылаются на устаревший порт 22 — не
чинено, обходится ручным `ssh sfera`, см. `04_STATE.md` запись `2026-09-06`).

Есть второй алиас `sfera-ai` — тот же хост/порт, но под отдельным пользователем
`ai-agent` и своим ключом (`~/.ssh/sfera_ai`), используется скриптами-туннелями
(`tunnel-platform-db.sh` и т.п.), не для интерактивного захода.

**Расположение сервисов на VPS** — всё под `/var/www/`, backend платформы SFERA
(`sfera_backend`) лежит в `/var/www/sphera-backend`. Рядом в той же папке — другие,
не связанные с этим проектом сервисы (`sphera-frontend`, `SPHERA-TOOLS`,
`ParserResumeHH`, `sfera-operations-dashboard`, `html`) — трогать только то, что
явно относится к текущей задаче, не залезать в остальное без необходимости.

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
