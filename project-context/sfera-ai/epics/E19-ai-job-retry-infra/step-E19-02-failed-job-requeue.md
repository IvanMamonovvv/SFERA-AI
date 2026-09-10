# Шаг E19-02 — авто-ретрай FAILED AIProcessingJob

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E19-01
**Перед началом:** прочитай `scheduler.py::run_tick`/`run_resume_retry` (готовый образец
паттерна для другой модели — `ResumeExtract`), `services/job_processing.py::process_batch`
(текущая выборка — только `status == PENDING`), partial unique index
`uq_processing_job_candidate_course_reason_open` (`candidate_profile_id, course_id, reason`,
только для `PENDING`/`PROCESSING` — найдено ревью-агентом 2026-09-10: при переводе FAILED
обратно в PENDING может столкнуться с уже существующей новой PENDING-джобой той же тройки,
если событие создало её пока старая лежала FAILED).

## Цель

Кандидат с `AIProcessingJob.status == FAILED` (например из-за отклонённого валидацией ответа
LLM, E20) реально пересчитывается позже автоматически, а не зависает навсегда — до
`attempts >= ai_processing_job_max_attempts` (E19-01).

## Что сделать

1. Решить (зафиксировать в журнале): расширить выборку `run_tick`/`process_batch` до
   `status IN (PENDING, FAILED) AND (retry_after IS NULL OR retry_after <= now()) AND attempts < max_attempts`,
   или завести отдельный cron-джоб `run_ai_job_retry` по образцу `run_resume_retry`
   (`scheduler.py`, интервал по аналогии — раз в 2 часа). Предпочтение — по образцу
   `step-E18-03-failed-resume-requeue.md` (уже согласованный владельцем прецедент для похожей
   задачи).
2. Реализовать выбранный вариант.
3. Убедиться, что джобы, исчерпавшие `attempts`, остаются `FAILED` навсегда — не подхватываются
   повторно.
4. Решить конфликт с `uq_processing_job_candidate_course_reason_open`: перед переводом FAILED
   → PENDING проверить, нет ли уже открытой (PENDING/PROCESSING) джобы той же тройки
   `(candidate_profile_id, course_id, reason)` — если есть, старую FAILED не трогать (новая
   джоба и так покроет пересчёт), не пытаться requeue вслепую и не падать на `IntegrityError`.

## Файлы

- `src/sfera_ai/scheduler.py` — либо новый cron, либо правка `run_tick`.
- `src/sfera_ai/services/job_processing.py` — выборка `process_batch`.

## Критерии готовности (DoD)

- [ ] FAILED-джоба с истёкшим `retry_after` и `attempts < max` попадает в обработку повторно.
- [ ] FAILED-джоба с `attempts >= max` НЕ попадает в обработку.
- [ ] FAILED-джоба той же тройки, что уже открытая PENDING/PROCESSING — не requeue-ится,
      `IntegrityError` не возникает (тест).
- [ ] `uv run pytest` — регрессий нет.

## Как проверить

```bash
uv run pytest tests/test_scheduler.py -k retry
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-10 — решение п.1: отдельный cron `run_ai_job_retry` (scheduler.py, `CronTrigger(hour="*/2", minute=30)`,
  офсет от `run_resume_retry` на 30 минут) по образцу step-E18-03, а не расширение `run_tick`/`process_batch`.
  Реализовано: `requeue_failed_jobs(session, *, max_attempts)` в `job_processing.py` — выборка
  `status=FAILED AND attempts<max_attempts AND (retry_after IS NULL OR retry_after<=now())`; для каждой джобы
  проверка конфликта с открытой (PENDING/PROCESSING) джобой той же тройки
  `(candidate_profile_id, course_id, reason)` — при конфликте не трогается (остаётся FAILED, IntegrityError
  не возникает); иначе `status → PENDING`, `retry_after → None` (реальный AI-вызов сделает следующий тик
  `process_batch`). Использует существующий `ai_processing_job_max_attempts` (E19-01), нового конфига не
  потребовалось. Тесты: `tests/services/test_job_processing.py` (3 новых — просроченный backoff → PENDING,
  attempts>=max не подхватывается, конфликт открытой джобы не requeue-ится). `uv run pytest` — 246 passed.
