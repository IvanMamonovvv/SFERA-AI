# Шаг E15-04 — `POST vacancy-profile/` запускает полный скрининг курса

**Статус:** DONE
**Слой:** Backend (SFERA-AI) · **Зависит от:** E15-02
**Перед началом:** прочитай `docs/superpowers/specs/2026-09-08-candidate-screening-modal-design.md`
(раздел «Поток», п.3); `src/sfera_ai/api/routes/vacancy.py` (существующий
`POST .../vacancy-profile/`, E8-04).

## Цель

Сохранение новой версии портрета вакансии дополнительно ставит полный скрининг курса
в очередь — асинхронно, не блокируя ответ.

## Что сделать

1. После `create_vacancy_profile_version` (уже вызывает `enqueue_fit_recalc_for_course`)
   — добавить постановку `enqueue_full_screening_for_course` (E15-02).
2. Выполнить асинхронно: сама постановка джоб не должна выполняться в теле текущего
   HTTP-запроса на курсах с большим числом кандидатов (архитектурное ревью 2026-09-08 —
   реальный масштаб демо-должностей до 500 кандидатов). Варианты реализации — решить на
   этом шаге: fire-and-forget задача, отдельная лёгкая «мета-джоба» на очереди,
   background task FastAPI — что дешевле встроить в текущий стек.
3. Ответ `POST vacancy-profile/` не должен ждать завершения постановки джоб по всем
   кандидатам курса.

## Файлы

- `src/sfera_ai/api/routes/vacancy.py` — обработчик `POST .../vacancy-profile/`.

## Критерии готовности (DoD)

- [x] Новая версия портрета → и `enqueue_fit_recalc_for_course`, и
      `enqueue_full_screening_for_course` вызваны.
- [x] Замер: время ответа `POST` не зависит линейно от числа кандидатов курса (тест на
      курсе с большим числом кандидатов — мок задержки в постановке одной джобы,
      подтвердить что ответ не блокируется).
- [x] `uv run pytest` — весь сьют зелёный.

## Как проверить

```bash
uv run pytest tests/api/test_vacancy_endpoints.py -k full_screening
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-09-09 — реализовано. `create_vacancy_profile` (`src/sfera_ai/api/routes/vacancy.py`)
  после `create_vacancy_profile_version` запускает `_run_full_screening_background` в
  отдельном `threading.Thread` (не FastAPI `BackgroundTasks` — те выполняются до отправки
  ответа ASGI-клиенту и фактически блокируют его так же, как прямой вызов в теле запроса,
  что делает заявленный DoD-тест неверифицируемым под `TestClient`). Фоновая функция
  открывает свою `Session` (через `sessionmaker(bind=app.state.engine)`) и свой
  `platform_base` (`reflect_platform_tables(..., tables=IDENTITY_RESOLVER_TABLES)` —
  `courses_application` + `headhunter_hhnegotiationrecord`, минимальный набор для
  `resolve_or_create_candidate_profile`), т.к. request-scoped ресурсы закрываются сразу
  после ответа. Тесты — `tests/api/test_vacancy_endpoints.py`: джобы реально ставятся в
  фоне (poll с таймаутом) и мок задержки в `enqueue_full_screening_for_course` подтверждает,
  что ответ `POST` не блокируется. `uv run pytest` — 202 passed.
