# STATE — где мы остановились

> **Единственный источник правды о прогрессе.** Обновляй после каждого шага.
> Новый чат: читай сверху вниз, бери первый шаг со статусом `TODO`.

**Проект/фича:** SFERA-AI — AI-анализ кандидатов, единственный инструмент этого репозитория
**Последнее обновление:** `2026-08-26` — эпик E1 продолжен: `step-E1-06-write-session.md`
выполнен (`make_write_engine`/`make_session_factory`). Следующий шаг — `step-E1-07`
(см. `05_EPICS.md`).

## Внешние гейты / блокеры

Блокеров нет. Роль `ai_readonly` создана на прод-Postgres 2026-08-26 (владелец дал явное
разрешение), см. журнал `step-E0-04-ssh-tunnel.md` и `step-E0-05-smoke-test.md`.

6 открытых вопросов (`02_CONTEXT.md`) — ни один не блокирует старт разработки,
решаются по ходу, на своих шагах реализации.

## Текущий следующий шаг

Эпик E0 (bootstrap) полностью завершён, включая реальный прогон на проде. Следующий
шаг — эпик **E1** (`VacancyProfile`), см. `05_EPICS.md`.

**Не начинать без явного «начинай»/«приступай» от владельца** — план и код разделены
явным согласованием (правило проекта).

## Доска статусов

| Эпик/# | Шаг | Статус | Завершён |
|---|---|---|---|
| — | Архитектура (единый `ARCHITECTURE.md`, до реструктуризации) | DONE | 2026-08-21 |
| — | Решение об отдельном сервисе/репозитории | DONE | 2026-08-25 |
| — | Реструктуризация плана в PRD/CONTEXT/TDD/EPICS/STATE | DONE | 2026-08-25 |
| E0-01 | Bootstrap сервиса + reflection smoke-test (scaffold, env-config, reflection, tunnel, smoke-test код, Dockerfile, shared docker-сеть, роль `ai_readonly` создана, прогон на проде подтверждён) | DONE | 2026-08-26 |
| E1-01 | `VacancyProfile` модель + CRUD | TODO | — |
| E2-01 | `CandidateProfile` identity resolver | TODO | — |
| E3-01 | `ResumeExtract` пайплайн | TODO | — |
| E4-01 | Интеграция с `TranscriptionJob` | TODO | — |
| E5-01 | `AIProcessingJob` + очередь (dry-run) | TODO | — |
| E6-01 | Fit scoring | TODO | — |
| E7-01 | Vacancy Feedback/Memory workflow | TODO | — |
| E8-01 | Read API | TODO | — |
| E9-01 | Export | TODO | — |

## Журнал (дополнять, не стирать)

- `2026-08-26` — шаг `step-E1-06-write-session.md` выполнен: `src/sfera_ai/db/session.py`
  (`make_session_factory`, `make_write_engine`) по шагу без изменений. `uv run pytest`
  — 7 passed, регрессий нет.
- `2026-08-26` — шаг `step-E1-05-alembic-revision-0001.md` выполнен: ревизия
  `migrations/versions/0001_ai_vacancy_profile.py` — `upgrade` создаёт `ai_vacancy_profile`
  с FK `course_id → courses_course.id` (`ondelete='CASCADE'`) и partial unique index
  `uq_vacancy_profile_course_current` (гарантия ровно одного `is_current=True` на course).
  `revision id` заменён с автосгенерированного hash на `0001`. Синтаксическая проверка на
  SQLite не сработала (`env.py` игнорирует `-x`, всегда берёт `write_database_url`,
  порт 5434 из E1-01 уже снесён) — использован запасной путь из шага, `alembic upgrade
  head --sql` — DDL сгенерирован и проверен визуально, без ошибок. Реальное применение
  на прод — отдельно на E1-09, с подтверждением владельца.
- `2026-08-26` — шаг `step-E1-04-vacancy-profile-model.md` выполнен: модель `VacancyProfile`
  (`src/sfera_ai/models/vacancy_profile.py`) — поля по TDD, `UniqueConstraint(course_id,
  version)`, `course_id` — простой `Mapped[int]` без `ForeignKey` (FK-констрейнт будет в
  Alembic-миграции E1-05 через raw DDL). Тест шага скорректирован: добавлен `updated_at` в
  ожидаемые columns (`TimestampMixin` даёт `created_at`+`updated_at` вместе, отдельного
  created_at-only варианта нет) — решение согласовано с владельцем. `uv run pytest` — 6
  passed, регрессий нет.
- `2026-08-26` — эпик E1 начат: `step-E1-02-write-database-url.md` и
  `step-E1-03-declarative-base.md` выполнены первыми (`step-E1-01-alembic-init.md`
  фактически зависит от них), затем `step-E1-01-alembic-init.md` (код). `Settings`
  получил `write_database_url`, добавлены `sfera_ai/db/base.py` (`Base`,
  `TimestampMixin`), alembic инициализирован (`env.py` читает `Settings`/`Base`).
  Коммиты `7586075`, `ef4cc07`, `ac26c0a`. `.env.example` не обновлён — под глобальным
  запретом чтения/правки агента, владелец добавит `WRITE_DATABASE_URL` сам. Проверка
  `uv run alembic current` пройдена на разовом локальном Postgres (Docker, порт 5434,
  снесён после теста) — не прод. Шаги `E1-01`/`E1-02`/`E1-03` отмечены `DONE` в своих
  step-файлах. Реальный `WRITE_DATABASE_URL` для прода (роль `ai_owner`) — на шаге
  `E1-09`, отдельная прод-операция с явным разрешением владельца.
- `2026-08-26` — реальный прогон E0-04/E0-05 на проде выполнен (владелец дал явное
  разрешение на прод-операцию). Перед изменением схемы снят полный `pg_dump -Fc` бэкап
  `sfera_db` (сохранён локально в `.../scratchpad/backups/`, временная копия на VPS
  удалена). Роль `ai_readonly` создана строго по DDL из `step-E0-04-ssh-tunnel.md`
  (её не было — подтвердил владелец), пароль сгенерирован `openssl rand`, отдан
  владельцу, в git не коммитился. Туннель — временный socat-proxy контейнер в сети
  `ai_shared` на VPS + `ssh -L` с локальной машины (снесён по завершении). Smoke-test
  на `application_id=1`: `OK: read Application id=1`, `OK: write correctly rejected
  (read-only role confirmed)`. Прямой `psql` от `ai_readonly` подтвердил то же: SELECT
  проходит, INSERT — `permission denied for table courses_application`. Прод не
  пострадал, ничего лишнего не удалено/не изменено кроме создания роли. Детали — в
  журналах `step-E0-04-ssh-tunnel.md` и `step-E0-05-smoke-test.md`.
- `2026-08-26` — шаг `step-E0-08-state-update.md` выполнен: эпик E0 (bootstrap)
  реализован — uv-проект, env-конфиг, reflection, smoke-test, Dockerfile, общая
  docker-сеть. `E0-01` в доске статусов отмечен `DONE`. Текущий следующий шаг —
  эпик E1 (`VacancyProfile`).
- `2026-08-26` — шаг `step-E0-07-shared-docker-network.md` выполнен. Владелец дал
  SSH-доступ к VPS и подтвердил прод-операцию отдельно от общего согласия 2026-08-25.
  На VPS: `docker network create ai_shared`, `db` backend'а подключён к ней (правка
  `docker-compose.staging.yml` в `sfera_backend`, коммит `e22bf9b`, запушено в
  `origin/main` после rebase на чужой коммит `edfc20f`). **Инцидент:** после
  пересоздания `db` контейнер `scheduler` не восстановил закэшированное Django DB-
  соединение (`OperationalError: server closed the connection unexpectedly` каждые
  15-30с) — DNS и свежие соединения работали нормально, проблема только в уже открытом
  соединении долгоживущего процесса; исправлено `docker compose restart scheduler`,
  дальше без ошибок. `backend`/`gateway` не пострадали (HTTP 200 всё время). Сетевая
  связность подтверждена: `pg_isready -h db` из контейнера на `ai_shared` → OK.
  `docker-compose.yml` AI-сервиса создан в `SFERA-AI`, коммит `df01000`. Полный разбор
  инцидента — в журнале `step-E0-07-shared-docker-network.md`.
- `2026-08-26` — шаг `step-E0-06-dockerfile.md` выполнен: `Dockerfile` (multi-stage, uv)
  + `.dockerignore` созданы. При сборке всплыл баг: `pyproject.toml` объявляет
  `readme = "README.md"`, но README.md не копировался до финального `uv sync --frozen
  --no-dev`, сборка падала на `Building sfera-ai @ file:///app` с `failed to open file
  /app/README.md`. Исправлено — README.md добавлен в первый `COPY`. После фикса
  `docker build -t sfera-ai:bootstrap .` проходит без ошибок. Коммит `99908c2`.
- `2026-08-26` — шаг `step-E0-05-smoke-test.md` выполнен частично: `src/sfera_ai/smoke_test.py`
  реализован (читает `Application` по id, проверяет что write через `ai_readonly` падает
  с `DBAPIError`). Коммит `721dc6f`. **Не выполнено:** ручной прогон на реальном проде —
  на вопрос о статусе роли `ai_readonly` владелец ответил «без понятия», решено
  реализовать код и отложить прогон до момента, когда роль/туннель будут подтверждены.
- `2026-08-26` — шаг `step-E0-04-ssh-tunnel.md` выполнен частично: `scripts/tunnel-platform-db.sh`
  и `docs/LOCAL_DEV.md` готовы. Т.к. `03_TDD.md` фиксирует общую docker-сеть `ai_shared`
  без публикации `db` на host VPS, туннель — в два прыжка: временный socat-proxy
  контейнер в `ai_shared` на VPS + `ssh -L` поверх него (владелец подтвердил вариант).
  Коммит `d6a140e`. **Не сделано:** создание роли `ai_readonly` на прод-Postgres (DDL
  в step-файле) — вне доступа агента, требует владельца перед стартом E0-05.
- `2026-08-26` — шаг `step-E0-03-reflection-module.md` выполнен: `reflect_platform_tables`
  (SQLAlchemy automap, `MetaData.reflect(only=[...])`) ограничен переданным списком
  таблиц, тест `tests/test_platform_db.py` зелёный (sqlite in-memory, без реальной БД).
  Коммит `4cbcfb4` (смешан с docs-правками предыдущего шага — не критично).
- `2026-08-26` — шаг `step-E0-02-env-config.md` выполнен: `Settings` (pydantic-settings)
  читает `PLATFORM_DATABASE_URL` из окружения/`.env`, тест `tests/test_config.py`
  зелёный, `.env.example` создан (плейсхолдеры, без реального пароля). Коммит `5522817`.
- `2026-08-26` — шаг `step-E0-01-project-scaffold.md` выполнен: uv установлен (brew,
  0.12.6), `uv init --package` (src-layout), добавлены sqlalchemy/psycopg[binary]/
  pydantic-settings + dev pytest, `uv.lock` создан, `py.typed`/`tests/__init__.py`
  добавлены. `uv run python -c "import sfera_ai"` проходит. Коммит `40073bf`.
- `2026-08-25` — репозиторий создан, архитектура и справочные материалы перенесены из
  `FullSphera` (единый `ARCHITECTURE.md`, `PLATFORM_AUDIT_REFERENCE.md`,
  `PLATFORM_video-transcription-plan/`).
- `2026-08-25` — по образцу монорепо `SFERA-Tools` (`project-context/<tool>/` +
  шаблон PRD→CONTEXT→TDD→EPICS→STATE) реструктурирован план: единый `ARCHITECTURE.md`
  разобран на `project-context/sfera-ai/{00_START_HERE,01_PRD,02_CONTEXT,03_TDD,05_EPICS,04_STATE}.md`
  + `step-TEMPLATE.md`. Старые `ARCHITECTURE.md`/`00_STATE.md` в корне `project-context/`
  удалены — содержимое полностью перенесено, потерь нет.
