# Шаг E5-04 — APScheduler процесс + `process_batch` (dry-run)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E5-03
**Перед началом:** прочитай `03_TDD.md` раздел «6. Processing Queue» (готовый код
скелета `scheduler.py`/`process_batch`), «8. Что НЕ ломаем» (не трогать
`core/scheduler.py` backend'а).

## Цель

Свой `BackgroundScheduler` в своём контейнере тикает по `CronTrigger` 3 раза в день
(08:00/15:00/19:00), забирает `PENDING`-джобы `select_for_update(skip_locked=True)`, но
реальные AI-вызовы **выключены флагом** (dry-run) — джоба помечается `DONE` без вызова,
тик быстрый при пустой очереди.

## Что сделать

1. `ai_service/scheduler.py` по скелету из TDD.
2. `process_batch(limit)` — `SELECT ... FOR UPDATE SKIP LOCKED`, `ThreadPoolExecutor`
   на партии, try/except на джобу (одна упавшая не блокирует остальные).
3. Флаг `AI_PROCESSING_DRY_RUN=true` — при включении `process_batch` вызывает только
   change detection (E5-02) заново (идемпотентность), не вызывает LLM, ставит `DONE`.
4. Backoff при `FAILED`: `retry_after = now + backoff(attempts)`.

## Файлы

- `src/sfera_ai/scheduler.py`
- `src/sfera_ai/services/job_processing.py`
- `tests/services/test_job_processing.py` — партия из N джоб, одна намеренно ломается

## Критерии готовности (DoD)

- [x] Пустая очередь — тик не тратит AI-бюджет (нет вызовов LLM в тесте)
- [x] Упавшая джоба не блокирует остальные в партии
- [x] Dry-run флаг подтверждён — ни один реальный AI-вызов не уходит

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-27` — реализовано:
  - `src/sfera_ai/services/job_processing.py` — `process_batch(session, platform_base,
    *, limit, dry_run)`: `SELECT ... FOR UPDATE SKIP LOCKED` (SQLite в тестах игнорирует
    locking-клаузу без ошибки, проверено), каждая джоба — свой try/except. Перед закрытием
    джобы — `_still_relevant` (для `CANDIDATE_DATA_CHANGED` заново `needs_profile_rebuild`
    из E5-02, чистое чтение, без AI). `dry_run=True` → `DONE` без реального вызова;
    `dry_run=False` → пока `NotImplementedError` (реальный AI-клиент — задача E6/E7, не
    этого шага) — джоба уходит в `FAILED` с `attempts+=1`/`retry_after=now+backoff(attempts)`.
    `backoff(attempts)` — экспонента 5/10/20/40... минут.
  - `src/sfera_ai/scheduler.py` — `run_tick(settings)` (detection E5-03 + `process_batch`
    в одном вызове, свой write engine + platform engine) и `build_scheduler()`
    (`BackgroundScheduler`, `CronTrigger(hour='8,15,19')`, `max_instances=1`) по скелету
    из `03_TDD.md`. Не тестируется юнит-тестами (обвязка APScheduler, не бизнес-логика) —
    только `import` проверен.
  - `Settings.ai_processing_dry_run` (default `True`) и `Settings.ai_analysis_max_concurrent_jobs`
    (default `5`) — новые поля в `src/sfera_ai/config.py`.
  - Зависимость `apscheduler==3.11.3` добавлена (`uv add apscheduler`).

  Тесты `tests/services/test_job_processing.py` — 5 (пустая очередь, dry-run → DONE,
  dry-run выключен → FAILED без тихого прохождения, упавшая джоба не блокирует
  остальные в партии, экспонента backoff). Полный сьют `uv run pytest` — 77 passed,
  регрессий нет. Дальше — `step-E5-05-stuck-jobs.md`.
