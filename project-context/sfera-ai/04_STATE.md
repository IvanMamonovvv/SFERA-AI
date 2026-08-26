# STATE — где мы остановились

> **Единственный источник правды о прогрессе.** Обновляй после каждого шага.
> Новый чат: читай сверху вниз, бери первый шаг со статусом `TODO`.

**Проект/фича:** SFERA-AI — AI-анализ кандидатов, единственный инструмент этого репозитория
**Последнее обновление:** `2026-08-26` — эпик E0, шаг `step-E0-03-reflection-module.md`
выполнен: `reflect_platform_tables` (SQLAlchemy automap, ограничен `only=[...]`) готов,
тест зелёный.

## Внешние гейты / блокеры

Нет активных блокеров. 6 открытых вопросов (`02_CONTEXT.md`) — ни один не блокирует
старт разработки, решаются по ходу, на своих шагах реализации.

## Текущий следующий шаг

`epics/E0-service-bootstrap/step-E0-04-ssh-tunnel.md` (см. `05_EPICS.md`, эпик E0) —
шаг 4 из 8 подробного task-by-task разбора эпика E0 (bootstrap сервиса, `Dockerfile`,
подключение к БД через SQLAlchemy `automap` reflection на 2-3 таблицах платформы,
smoke-test чтения одной реальной записи `Application`; ничего не пишется, только
чтение). Шаги 1-3 (`step-E0-01-project-scaffold.md`, `step-E0-02-env-config.md`,
`step-E0-03-reflection-module.md`) выполнены.

**Не начинать без явного «начинай»/«приступай» от владельца** — план и код разделены
явным согласованием (правило проекта).

## Доска статусов

| Эпик/# | Шаг | Статус | Завершён |
|---|---|---|---|
| — | Архитектура (единый `ARCHITECTURE.md`, до реструктуризации) | DONE | 2026-08-21 |
| — | Решение об отдельном сервисе/репозитории | DONE | 2026-08-25 |
| — | Реструктуризация плана в PRD/CONTEXT/TDD/EPICS/STATE | DONE | 2026-08-25 |
| E0-01 | Bootstrap сервиса + reflection smoke-test (шаги 1-3/8: scaffold, env-config, reflection — DONE) | TODO | — |
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
