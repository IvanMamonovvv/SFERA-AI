# Шаг E25-01 — эндпоинт прогресса обработки

**Статус:** DONE
**Слой:** Backend (SFERA-AI, свой репозиторий, без ограничений) · **Зависит от:** E24-01
**Перед началом:** прочитай `src/sfera_ai/api/routes/vacancy.py` (паттерн `course_uuid` →
`resolve_course_or_404`, соседние роуты), `src/sfera_ai/models/ai_processing_job.py`,
`04_STATE.md` (записи по E24/E25 2026-09-10).

## Цель

`GET .../vacancy-profile/screening-progress/` отдаёт, сколько кандидатов курса ещё в
обработке после последнего обновления портрета — на момент запроса (не realtime).

## Контекст решений

Знаменатель — все открытые (`PENDING`/`PROCESSING`) `AIProcessingJob(reason='BACKFILL')`
курса, без привязки к конкретной версии портрета (осознанный трейдофф владельца —
если портрет пересохранён до завершения предыдущей партии, счётчик покажет общий хвост,
не разбитый по версиям). Зависит от E24 — без фикса BACKFILL-джобы не считают fit_score,
`remaining=0` может значить «готово», хотя новых кандидатов не оценили.

Архитектурное ревью 2026-09-10 отдельно отметило: `FAILED`-джобы, исчерпавшие
`ai_processing_job_max_attempts`, не попадают в `PENDING`/`PROCESSING` — решить на этом
шаге, включать ли их в `remaining` или отдавать отдельным полем `failed` (не прятать
зависшие навсегда джобы под видом «готово»).

## Что сделать

1. Новый роут `GET /vacancy-profile/screening-progress/` в `api/routes/vacancy.py`, тот
   же паттерн `course_uuid: str` → `resolve_course_or_404(platform_engine, course_uuid)`
   → `course_id`, что у `get_vacancy_profile`/остальных роутов файла — не raw `course_id`
   параметром.
2. Запрос: `count(AIProcessingJob) where course_id=X, reason='BACKFILL', status IN
   (PENDING, PROCESSING)` → `remaining`.
3. Решить и реализовать обработку `FAILED` с исчерпанными попытками (см. контекст выше) —
   отдельное поле `failed` в ответе, значение по умолчанию если решение «не разделять» —
   зафиксировать явно в журнале шага.
4. Форма ответа: `{"remaining": int, "failed": int}` (или проще, если владелец решит не
   разделять — зафиксировать в журнале).

## Файлы

- `src/sfera_ai/api/routes/vacancy.py` — новый роут.
- `tests/api/test_vacancy_endpoints.py` (или новый файл) — тесты.

## Критерии готовности (DoD)

- [ ] Пустая очередь → `remaining=0`.
- [ ] Смесь статусов (PENDING/PROCESSING/DONE/FAILED) → верный `remaining`.
- [ ] Изоляция по `course_id` — джобы другого курса не подмешиваются.
- [ ] Джобы других `reason` (`CANDIDATE_DATA_CHANGED`, `MANUAL` и т.п.) в PENDING/PROCESSING
  не подмешиваются в `remaining` (регрессионный кейс из ревью — `course_id` nullable на
  модели, не все reason его несут).
- [ ] `FAILED` с исчерпанными попытками — отдельный тест на принятое решение (включены в
  `remaining` либо отдельное поле `failed`).
- [ ] Полный `uv run pytest` — без регрессий.

## Как проверить

```bash
uv run pytest tests/api/test_vacancy_endpoints.py -v
uv run pytest
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md` (следующий шаг — E25-02, требует отдельного «начинай» — другой репозиторий).

## Журнал

- `2026-09-10` — реализован `GET .../vacancy-profile/screening-progress/`
  (`src/sfera_ai/api/routes/vacancy.py`, `resolve_course_or_404` паттерн). Сервис
  `get_screening_progress` в `api_read.py`, по образцу существующего `get_summary`.
  Ответ `{"remaining": int, "failed": int}` — оба поля фильтруют `reason='BACKFILL'`,
  `remaining` = `PENDING`/`PROCESSING`, `failed` = `FAILED` с `attempts>=max_attempts`
  (`Settings().ai_processing_job_max_attempts`, как в `get_course_summary`). Решение по
  FAILED: **отдельное поле**, не подмешивать в `remaining` — не прятать окончательно
  потерянные джобы под видом «готово», симметрично уже принятому решению по
  `permanently_failed` в `get_summary` (E24). 4 новых теста в
  `tests/api/test_vacancy_endpoints.py`: пустая очередь, смесь статусов, изоляция по
  course_id, игнор других reason. Полный `uv run pytest` — 269 passed, без регрессий.
