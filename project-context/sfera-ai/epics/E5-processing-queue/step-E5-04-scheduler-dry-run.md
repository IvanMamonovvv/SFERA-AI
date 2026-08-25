# Шаг E5-04 — APScheduler процесс + `process_batch` (dry-run)

**Статус:** TODO
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

- [ ] Пустая очередь — тик не тратит AI-бюджет (нет вызовов LLM в тесте)
- [ ] Упавшая джоба не блокирует остальные в партии
- [ ] Dry-run флаг подтверждён — ни один реальный AI-вызов не уходит

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
