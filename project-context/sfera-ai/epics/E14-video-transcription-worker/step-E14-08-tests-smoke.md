# Шаг E14-08 — Тесты и smoke

**Статус:** DONE
**Слой:** QA/Backend · **Зависит от:** параллельно с E14-01…06 (не откладывать в конец)
**Репозиторий:** `sfera_backend` — требует отдельного явного разрешения владельца перед
стартом (`CLAUDE.md`).
**Перед началом:** прочитай `project-context/PLATFORM_video-transcription-plan/step-09-tests-smoke.md`
(полный список кейсов, включая «пустое видео»).

## Цель

Очередь, воркер и крайние случаи покрыты тестами; ручной smoke-чеклист заведён.

## Где делать

Юнит/интеграционные тесты в `sfera_backend` (рядом с реализацией каждого шага). Smoke-пункты
— в `sfera_backend`-репозиторийном `06_TEST_CHECKLIST.md`.

## Файлы

- тесты рядом с `testchecks/services/transcription/`, `testchecks/management/commands/`
- `06_TEST_CHECKLIST.md` (в `sfera_backend`)

## Критерии готовности (DoD)

Полный список — в `step-09-tests-smoke.md`. Кратко:
- [x] Кейс «пустое видео» покрыт явно.
- [x] Пункты добавлены в `06_TEST_CHECKLIST.md`.

## Как отметить выполнение

1. Журнал в `step-09-tests-smoke.md`.
2. Статус здесь → `DONE`, обнови `01_STATE.md` внешнего плана.
3. Обнови `04_STATE.md` этого репозитория.

## Журнал

- `2026-09-09` — реализовано по явному разрешению владельца (код в `sfera_backend`).
  Новый `testchecks/tests/test_transcription_worker.py` (11 тестов: `claim_batch`,
  `reap_stale_jobs`, `_process_job` — успех/пустое видео/сбой+retry/FAILED после лимита
  попыток) закрывает единственный реально непокрытый кусок DoD — остальные пункты уже
  были закрыты шагами E14-01/05/07. `manage.py test` — весь backend 657 passed, 3
  skipped, регрессий нет. Раздел «Видео-транскрибация» добавлен в
  `FullSphera/project-context/06_TEST_CHECKLIST.md` (не `project-context2/` — проверено
  по ссылкам корневого `CLAUDE.md`). Ручной smoke-чеклист **заведён, не пройден живым
  видео** — нет запущенного воркера/реального видеофайла в этой сессии, тот же блокер,
  что на E14-02/04. Детали — журнал `step-09-tests-smoke.md` внешнего плана. Изменения в
  `sfera_backend` НЕ закоммичены.
