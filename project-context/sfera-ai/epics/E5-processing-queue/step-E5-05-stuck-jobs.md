# Шаг E5-05 — зависшие `PROCESSING` джобы

**Статус:** TODO
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

- [ ] Зависшая джоба (started_at старше порога) → `PENDING`, `attempts+1`
- [ ] Свежая `PROCESSING` не трогается

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -v -k stuck
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (эпик E5
   → DONE, следующий — E6).

## Журнал

- `YYYY-MM-DD` — <что сделано>.
