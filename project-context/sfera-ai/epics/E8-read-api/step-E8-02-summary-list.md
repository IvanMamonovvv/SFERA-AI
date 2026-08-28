# Шаг E8-02 — `summary` и `candidates` (список)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E8-01, E1, E2, E6

## Цель

`GET .../ai-analysis/summary/` и `GET .../ai-analysis/candidates/` отдают данные по
контракту TDD.

## Что сделать

1. `summary/` — агрегат: всего/обработано/в очереди/ошибки (по `AIProcessingJob.status`
   + `CandidateVacancyAnalysis` наличие для `course`).
2. `candidates/` — список: `candidate_profile_id`, `fit_score`, `confidence`,
   `data_completeness`, `recommendation`, `fit_delta` (текущий vs предыдущий
   `is_current`), `demo_progress` (источник — reflection на `Progress`, если нужно).
3. Пагинация — решить схему (offset/cursor), зафиксировать в журнале.

## Файлы

- `src/sfera_ai/api/routes/candidates.py`
- `src/sfera_ai/services/api_read.py` — сервисный слой чтения (не размазывать SQL по
  роутам)
- `tests/api/test_candidates_list.py`

## Критерии готовности (DoD)

- [x] Оба эндпоинта покрыты тестами (пустой course, course с данными)
- [x] `fit_delta` считается корректно (сравнение двух последних версий)

## Как проверить

```bash
uv run pytest tests/api/test_candidates_list.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-28` — выполнено. `src/sfera_ai/services/api_read.py`:
  `resolve_course_id(platform_base, course_uuid)` — {course_uuid} из URL это
  `Course.course_uuid` платформы, `course_id` в `ai_*` таблицах — `Course.id` (PK),
  резолвится reflection'ом (`platform_db.API_READ_TABLES` — `courses_course` +
  `courses_application` + `courses_progress`, один reflect на запрос для обоих
  эндпоинтов). Неизвестный `course_uuid` → 404 (владелец подтвердил).
  `get_summary(session, course_id)` — total/processed/queued/errors: **total** —
  кандидаты, хоть раз затронутые `AIProcessingJob` или `CandidateVacancyAnalysis` для
  этого `course_id` (union, без похода в платформенные `Application` — буквально по
  формулировке шага «по `AIProcessingJob.status` + `CandidateVacancyAnalysis` наличие
  для course»); **processed** — distinct `candidate_profile_id` с
  `CandidateVacancyAnalysis.is_current=True`; **queued** — `AIProcessingJob` в
  `PENDING`/`PROCESSING`; **errors** — `AIProcessingJob.status=FAILED`.
  `list_candidates(session, platform_base, course_id, *, limit, offset)` — список по
  текущей версии `CandidateVacancyAnalysis`, поля контракта: `candidate_profile_id`,
  `fit_score`, `confidence`, `data_completeness` (снепшот-int с самого анализа, не
  `CandidateProfile.data_completeness`), `recommendation`, `fit_delta` (текущий
  `fit_score` минус `fit_score` версии `version - 1` того же
  candidate_profile+course — append-only версии без пропусков, см. 03_TDD.md), сортировка
  по `candidate_profile_id` (стабильна, соответствует offset-пагинации DRF-стиля
  платформы, владелец подтвердил).
  **demo_progress** — своя копия формулы `completed_lessons/total_lessons*100`
  (`Progress`, `courses_progress`) прямо в AI-сервисе — владелец осознанно принял третью
  копию (после `CourseCandidatesBaseSerializer.get_progress` и
  `candidates_archive_service.py` в `sfera_backend`, см. `PLATFORM_AUDIT_REFERENCE.md`
  разделы 7/12), т.к. AI-сервис не может импортировать Django-код платформы — читает
  только read-only reflection. Посчитано батчем на страницу (`CandidateProfile.id →
  application_id → Application.candidate_id → Progress` по `course_id`), не по одному
  reflect-запросу на кандидата.
  **Пагинация** — offset/limit (owner: соответствует стилю остального API платформы),
  `Query(limit, ge=1, le=200, default=50)` / `Query(offset, ge=0, default=0)`, ответ
  `{"items": [...], "total": int, "limit": int, "offset": int}`.
  Роуты — `src/sfera_ai/api/routes/candidates.py` (`GET /summary/`, `GET /candidates/`),
  подключены в `routes/__init__.py` (`router.include_router(candidates.router)`).
  `create_app()` (`api/app.py`) получил новый параметр `platform_engine_factory`
  (по аналогии с `engine_factory`) — `app.state.platform_engine`, dispose в lifespan.
  Тесты — `tests/api/test_candidates_list.py` (7: summary — пусто/с данными/404
  неизвестный course/401 без секрета; candidates — пусто/полный контракт с
  fit_delta+demo_progress/пагинация). SQLite `:memory:` под `TestClient` требует
  `StaticPool` + `check_same_thread=False` — без этого запись из тестового потока и
  чтение из anyio-воркер-потока FastAPI бьются о разные sqlite-коннекшены
  (`SingletonThreadPool` по умолчанию). `uv run pytest` — 140 passed, регрессий нет.
