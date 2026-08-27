# Шаг E5-05 — зависшие `PROCESSING` джобы

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E5-04
**Перед началом:** прочитай `03_TDD.md` «6. Processing Queue» → «Зависшие PROCESSING»,
«Failure Scenarios» → «Job завис».

## Цель

Отдельный cron (раз в час) переводит `PROCESSING`-джобы старше N часов обратно в
`PENDING` (не `FAILED`) с инкрементом `attempts`; рестарт контейнера не теряет джобы
(БД-очередь, не in-memory).

## Что сделать

1. Функция `requeue_stuck_jobs(threshold_hours)` — `UPDATE ... WHERE status=PROCESSING
   AND started_at < now() - threshold`.
2. Регистрация как отдельный периодический job в том же `BackgroundScheduler` (интервал
   час, отдельно от 15-секундного тика).

## Файлы

- `src/sfera_ai/services/job_processing.py` — расширение
- `tests/services/test_job_processing.py` — расширение (зависшая джоба → назад в
  PENDING, свежая PROCESSING — не трогается)

## Критерии готовности (DoD)

- [x] Зависшая джоба (started_at старше порога) → `PENDING`, `attempts+1`
- [x] Свежая `PROCESSING` не трогается

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -v -k stuck
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E5
   → DONE, следующий — E6).

## Журнал

- `2026-08-27` — реализовано: `requeue_stuck_jobs(session, threshold_hours)` в
  `src/sfera_ai/services/job_processing.py` — `UPDATE ... WHERE status=PROCESSING AND
  started_at < now()-threshold`, `attempts += 1`, `started_at = None` (не `FAILED` —
  не вина джобы, следующий тик `process_batch` подхватит её снова). Зарегистрирован
  как отдельный часовой job в `build_scheduler()` (`src/sfera_ai/scheduler.py`,
  `run_requeue_stuck`, `CronTrigger(minute=0)`, отдельно от 3-разового тика).
  Новая настройка `Settings.ai_stuck_job_threshold_hours` (default `2`) в `config.py`.
  Тесты `tests/services/test_job_processing.py` — +2 (зависшая → `PENDING`+`attempts+1`,
  свежая `PROCESSING` не трогается). Полный сьют `uv run pytest` — 79 passed, регрессий
  нет. **Инструкция шага «эпик E5 → DONE» неточна** — в `05_EPICS.md`/каталоге шагов ещё
  есть `step-E5-06-hh-lead-pii-ttl.md` и `step-E5-07-merge-detection.md` (TODO), эпик E5
  не завершён. Дальше — `step-E5-06-hh-lead-pii-ttl.md`.
