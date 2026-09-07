# Шаг E14-05 — Отдать транскрипт/summary в API карточки кандидата

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E14-04 (нечего отдавать, пока воркер не пишет DONE)
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца перед
стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-06-api-expose.md`
(структура поля, RBAC, OpenAPI, DoD).

## Цель

В ответе API карточки кандидата для видеовизитки — статус обработки, транскрипт, summary.

## Где делать

Сериализатор карточки кандидата в `sfera_backend/testchecks/`/`courses/` (тот, что кормит
HR-карточку — уточнить в `02_CONTEXT.md` внешнего плана). Добавить вложенный объект из
`answer.transcription_job` (OneToOne). RBAC — только HR/Admin.

## Файлы

- сериализатор карточки кандидата (найти при реализации)
- OpenAPI: `python manage.py spectacular` + `03_API.md`

## Критерии готовности (DoD)

Полный список — в `step-06-api-expose.md`. Кратко:
- [x] GET карточки кандидата возвращает `transcription` для видеоответов (без `verdict`).
- [x] Кандидат/чужая роль поле не получают.
- [x] OpenAPI обновлён; `03_API.md` в репозитории `sfera_backend` не найден — пункт пропущен (см. журнал).

## Как отметить выполнение

1. Журнал в `step-06-api-expose.md`.
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- 2026-09-07: реализовано в `sfera_backend` с явного разрешения владельца
  (правка чужого репозитория). Подробности — журнал `step-06-api-expose.md`
  внешнего плана (`project-context/PLATFORM_video-transcription-plan/`).
  Кратко: поле `transcription` (`status`/`summary`/`transcript`/`isEmpty`)
  добавлено в `CandidateCourseAnswersSerializer`
  (`testchecks/serializers.py`), эндпоинт `GET
  /api/v1/courses/{course_uuid}/candidates/{candidate_id}/answers/`. RBAC —
  без изменений, эндпоинт и так HR/Admin-only. Новые тесты
  `test_candidate_course_answers_transcription.py`, полный прогон
  `testchecks`+`courses` 221/221. `01_STATE.md` внешнего плана не трогал —
  правки docs в `FullSphera/project-context` (вне `sfera_backend`, вне
  выданного разрешения) не входили в scope этой сессии; владельцу стоит
  обновить его отдельно или дать отдельное разрешение.
