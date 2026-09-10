# Шаг E19-01 — лимит попыток для AIProcessingJob

**Статус:** DONE
**Слой:** Backend · **Зависит от:** нет
**Перед началом:** прочитай `config.py::resume_extract_max_attempts` (готовый образец для
`ResumeExtract`), `models/ai_processing_job.py` (колонки `attempts`/`retry_after` + индекс
`ix_processing_job_status_retry_after` уже есть — миграция не нужна, проверено ревью-агентом
2026-09-10), `services/job_processing.py::process_batch` (текущая логика `attempts`/
`retry_after` — уже пишутся при исключении, подтверждено чтением кода) и
`services/job_processing.py::requeue_stuck_jobs` (строки ~169-171 — тоже инкрементирует
`attempts`, но БЕЗ проверки потолка, отдельный источник бесконечного ретрая зависших джоб,
найдено ревью-агентом 2026-09-10).

## Цель

`AIProcessingJob` получает настраиваемый потолок попыток (`ai_processing_job_max_attempts`) —
после него FAILED остаётся окончательным статусом, не ретраится бесконечно.

## Что сделать

1. `config.py` — новое поле `ai_processing_job_max_attempts: int = 5` (по образцу
   `resume_extract_max_attempts`).
2. Проверить, что `process_batch` при провале уже инкрементирует `attempts` и пишет
   `retry_after` — подтверждено (job_processing.py:145-149). Если найдётся расхождение —
   поправить.
3. `requeue_stuck_jobs` — добавить проверку потолка `attempts < ai_processing_job_max_attempts`
   перед requeue зависшей (PROCESSING) джобы; джоба, исчерпавшая попытки, переводится в
   `FAILED` вместо очередного requeue в `PENDING`.
4. Не менять здесь выборку `run_tick`/`process_batch` под FAILED (это E19-02) — только конфиг
   и потолок для `requeue_stuck_jobs`.

## Файлы

- `src/sfera_ai/config.py` — новая настройка.
- `src/sfera_ai/services/job_processing.py` — проверка/фикс инкремента `attempts`.

## Критерии готовности (DoD)

- [ ] `Settings().ai_processing_job_max_attempts == 5` по умолчанию.
- [ ] Провал `process_batch` инкрементирует `attempts` и выставляет `retry_after` (тест).
- [ ] Зависшая джоба с `attempts >= max_attempts` в `requeue_stuck_jobs` переводится в
      `FAILED`, не requeue-ится повторно в `PENDING` (тест).
- [ ] `uv run pytest` — регрессий нет.

## Как проверить

```bash
uv run pytest tests/services/test_job_processing.py -k attempts
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-09-10` — реализовано. `config.py::ai_processing_job_max_attempts=5` (по образцу
  `resume_extract_max_attempts`). `process_batch` уже инкрементировал `attempts`/
  `retry_after` при провале (job_processing.py:144-149) — подтверждено, без изменений.
  `requeue_stuck_jobs` — новый обязательный keyword-параметр `max_attempts`: после
  инкремента `attempts` джоба с `attempts >= max_attempts` идёт в `FAILED`
  (+`finished_at`), иначе как раньше в `PENDING`. `scheduler.py::run_requeue_stuck`
  передаёт `settings.ai_processing_job_max_attempts`. Обновлены 2 существующих теста
  (добавлен `max_attempts=5` в вызов) + новый `test_stuck_job_exhausted_attempts_marked_failed_not_requeued`.
  `uv run pytest` — 243 passed (1 неродственный флаки-тест
  `test_post_vacancy_profile_enqueues_full_screening_in_background` — race в фоновом
  потоке, прошёл при повторном прогоне в одиночку). Не закоммичено.
