# STATE — где мы остановились

> **Единственный источник правды о прогрессе.** Обновляй после каждого шага.
> Новый чат: читай сверху вниз, бери первый шаг со статусом `TODO`.

**Проект/фича:** SFERA-AI — AI-анализ кандидатов, единственный инструмент этого репозитория
**Последнее обновление:** `2026-08-25` — репозиторий создан, архитектура и справочные
материалы перенесены из `FullSphera`, план реорганизован в структуру
`project-context/sfera-ai/` (PRD/CONTEXT/TDD/EPICS/STATE) по образцу `SFERA-Tools`.

## Внешние гейты / блокеры

Нет активных блокеров. 6 открытых вопросов (`02_CONTEXT.md`) — ни один не блокирует
старт разработки, решаются по ходу, на своих шагах реализации.

## Текущий следующий шаг

`epics/E0-service-bootstrap/step-E0-01-project-scaffold.md` (см. `05_EPICS.md`, эпик
E0) — первый шаг подробного task-by-task разбора: bootstrap сервиса, минимальный
Python-проект, `Dockerfile`, подключение к БД (SQLAlchemy `automap` reflection на 2-3
таблицах платформы), smoke-test чтения одной реальной записи `Application`. Ничего не
пишется, только чтение.

**Не начинать без явного «начинай»/«приступай» от владельца** — план и код разделены
явным согласованием (правило проекта).

## Доска статусов

| Эпик/# | Шаг | Статус | Завершён |
|---|---|---|---|
| — | Архитектура (единый `ARCHITECTURE.md`, до реструктуризации) | DONE | 2026-08-21 |
| — | Решение об отдельном сервисе/репозитории | DONE | 2026-08-25 |
| — | Реструктуризация плана в PRD/CONTEXT/TDD/EPICS/STATE | DONE | 2026-08-25 |
| E0-01 | Bootstrap сервиса + reflection smoke-test | TODO | — |
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

- `2026-08-25` — репозиторий создан, архитектура и справочные материалы перенесены из
  `FullSphera` (единый `ARCHITECTURE.md`, `PLATFORM_AUDIT_REFERENCE.md`,
  `PLATFORM_video-transcription-plan/`).
- `2026-08-25` — по образцу монорепо `SFERA-Tools` (`project-context/<tool>/` +
  шаблон PRD→CONTEXT→TDD→EPICS→STATE) реструктурирован план: единый `ARCHITECTURE.md`
  разобран на `project-context/sfera-ai/{00_START_HERE,01_PRD,02_CONTEXT,03_TDD,05_EPICS,04_STATE}.md`
  + `step-TEMPLATE.md`. Старые `ARCHITECTURE.md`/`00_STATE.md` в корне `project-context/`
  удалены — содержимое полностью перенесено, потерь нет.
