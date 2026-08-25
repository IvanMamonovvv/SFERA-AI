# CLAUDE.md — SFERA-AI

> Claude Code читает этот файл автоматически при каждом новом окне в этом репозитории.
> Держи его сжатым (навигатор, не свод знаний). Детали — в `project-context/`, не дублировать сюда.

## Что за проект

Отдельный сервис (отдельный git-репозиторий, отдельный деплой) AI-анализа кандидатов для SFERA
(основной продукт — `/Documents/projects/FullSphera/`). Читает данные платформы (кандидаты, ответы,
резюме, видео) напрямую из той же PostgreSQL, что использует `sfera_backend` — **без Django ORM**,
через SQLAlchemy reflection. Пишет только в свои собственные таблицы (`ai_*`). Не меняет и не
имеет доступа на запись к таблицам платформы.

**Полный план — [`project-context/sfera-ai/00_START_HERE.md`](project-context/sfera-ai/00_START_HERE.md).
Прочитай его первой, прежде чем писать код.** Структура папки — по образцу монорепо `SFERA-Tools`
(`project-context/<инструмент>/` + шаблон PRD→CONTEXT→TDD→EPICS→STATE), даже если здесь всего один
инструмент. Внутри: PRD (что/зачем), CONTEXT (согласованная модель, решения владельца), TDD
(домен-модель на 7 таблиц, ER-схема, identity-модель, change detection, очередь задач, privacy-каскад),
EPICS (карта эпиков E0–E9) и STATE (текущий прогресс).

**Технический контекст платформы SFERA** (что там реально есть в коде, на что можно опираться при
чтении через reflection) — [`project-context/PLATFORM_AUDIT_REFERENCE.md`](project-context/PLATFORM_AUDIT_REFERENCE.md).
Это снепшот аудита от 2026-08-21 — при расхождении с реальностью проверяй актуальный код
`FullSphera/sfera_backend/` (тот же git worktree или соседняя папка на диске).

**План транскрибации видео** (`TranscriptionJob` — внешний источник для видео-фактов, раздел
«Video Pipeline» `03_TDD.md`) — ещё не реализован в `sfera_backend`, но согласован:
[`project-context/PLATFORM_video-transcription-plan/`](project-context/PLATFORM_video-transcription-plan/).
Проверять актуальность реализации в `FullSphera` перед тем как полагаться на конкретные названия
таблиц/полей оттуда.

## CodeGraph

В репозитории есть `.codegraph/` — индекс кода. Перед grep/чтением файлов по одному
использовать `codegraph explore "<вопрос>"` (или MCP `codegraph_explore` в Claude Code).
Переиндексировать после структурных изменений: `codegraph sync`.

## Структура репозитория

```
SFERA-AI/
  CLAUDE.md                          ← ты здесь
  project-context/
    sfera-ai/                        ← план ЕДИНСТВЕННОГО инструмента (см. SFERA-Tools для образца)
      00_START_HERE.md               ← точка входа, порядок чтения
      01_PRD.md                      ← что и зачем (Socratic Gate не пройден, есть TODO)
      02_CONTEXT.md                  ← согласованная модель, решения владельца, edge cases
      03_TDD.md                      ← как реализуем: сущности, API, слои, риски
      05_EPICS.md                    ← карта эпиков E0–E9
      04_STATE.md                    ← текущий статус (единственный источник правды по прогрессу)
      step-TEMPLATE.md               ← шаблон шага
      epics/E{n}-<slug>/step-*.md    ← шаг-файлы всех эпиков E0–E9 (для E0-E2 — полный
                                        task-by-task разбор с кодом, executing-plans)
    PLATFORM_AUDIT_REFERENCE.md      ← снепшот аудита платформы SFERA (read-only контекст)
    PLATFORM_video-transcription-plan/  ← план внешнего источника видео-фактов (не наш код)
  <app-код появится с эпика E0 — см. 05_EPICS.md>
```

## 🎯 Активный план (что продолжать)

Статус — [`project-context/sfera-ai/04_STATE.md`](project-context/sfera-ai/04_STATE.md). Следующий
шаг — эпик **E0** (`05_EPICS.md`): bootstrap сервиса, подключение к БД, reflection-smoke-test.

## 🔒 Правила (перенесены из FullSphera, актуальны и здесь)

- План + критическая оценка → согласование → код. Без явного одобрения владельца — не реализовывать.
- Не менять `sfera_backend`/`SPHERA` (другой репозиторий) без отдельного явного разрешения на каждую
  конкретную правку (единственное согласованное исключение на сейчас — `docker-compose.staging.yml`,
  общая docker-сеть, раздел «Инфраструктура и сеть» `03_TDD.md`).
- Доступ к БД платформы — **только read-only** отдельным Postgres-пользователем. Ни при
  каких обстоятельствах не писать в таблицы `courses_*`/`testchecks_*`/`users_*`/`headhunter_*`.
- Один факт — один файл. Прогресс — только в `project-context/sfera-ai/04_STATE.md`, не дублировать по коду.
- Владелец — не профессиональный разработчик (тот же человек, что ведёт `FullSphera`). Объяснять
  решения простым языком, не лить код без согласования.
