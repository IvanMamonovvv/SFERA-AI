# Шаг E8-04 — `vacancy-profile`/`feedback` CRUD + approve

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E8-01, E1, E7

## Цель

`GET/POST .../vacancy-profile/`, `GET/POST .../feedback/`,
`POST .../feedback/{id}/approve/` работают по контракту TDD.

## Что сделать

1. `vacancy-profile/` GET — текущая `is_current` версия; POST — создаёт новую версию
   (переиспользует versioning-сервис из E1, не пишет вторую реализацию).
2. `feedback/` GET — список по `course`; POST — создаёт `VacancyFeedback`, триггерит
   E7-02 интерпретацию.
3. `feedback/{id}/approve/` — вызывает `approve_feedback` (E7-03) + триггер пересчёта
   (E7-04).
4. Валидация входных данных (Pydantic-схемы), понятные 400 на некорректный ввод.

## Файлы

- `src/sfera_ai/api/routes/vacancy.py`
- `tests/api/test_vacancy_endpoints.py`

## Критерии готовности (DoD)

- [x] Все три эндпоинта покрыты тестами
- [x] POST `vacancy-profile/` не переиспользует чужую логику — вызывает существующий
      сервис E1, не дублирует versioning

## Как проверить

```bash
uv run pytest tests/api/test_vacancy_endpoints.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-28` — выполнено: `src/sfera_ai/api/routes/vacancy.py` — `GET/POST
  vacancy-profile/` (POST вызывает `create_vacancy_profile_version` из E1,
  versioning не дублируется), `GET/POST feedback/` (POST синхронно вызывает
  `interpret_feedback` из E7-02, ошибка провайдера не роняет создание — `applied`
  остаётся пустым/False), `POST feedback/{id}/approve/` (вызывает `approve_feedback`
  из E7-03, который сам триггерит пересчёт E7-04 через `enqueue_fit_recalc_for_course`
  — отдельного вызова в роуте не нужно). Повторный approve уже применённого фидбека
  (`FeedbackAlreadyAppliedError`) → 409; неизвестный `feedback_id`/чужой `course` → 404.
  Валидация тела — Pydantic-модели (`VacancyProfileCreate`, `VacancyFeedbackCreate` с
  `Literal` для `sentiment`, `FeedbackApproveRequest`), некорректный ввод → стандартный
  FastAPI 422 с деталями по полям.
  Заодно вынес общие FastAPI-зависимости (`get_session`, `get_platform_engine`,
  `resolve_course_or_404`) из `routes/candidates.py` в новый `src/sfera_ai/api/deps.py`
  (иначе пришлось бы дублировать их в `vacancy.py` — не бизнес-логика, чистое
  дублирование), плюс `get_llm_client`; `candidates.py` переведён на общий модуль без
  изменения поведения. `create_app()` (`api/app.py`) — добавлен `llm_client_factory`
  (по умолчанию собирает `OpenRouterClient` из `Settings`, как в `scheduler.py`),
  `app.state.llm_client` доступен эндпоинтам через `Depends`.
  Тесты — `tests/api/test_vacancy_endpoints.py` (14, TestClient + sqlite in-memory,
  `_StubLLMClient` вместо реального OpenRouter-вызова). TDD: тесты написаны и
  прогнаны RED (404 — роутов не было) до реализации. `uv run pytest` — 156 passed,
  регрессий нет.
