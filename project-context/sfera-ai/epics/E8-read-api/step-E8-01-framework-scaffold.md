# Шаг E8-01 — веб-слой сервиса (каркас)

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E0
**Перед началом:** прочитай `03_TDD.md» «3. API / контракты» (полный список
эндпоинтов), `02_CONTEXT.md` (решение про BFF-прокси у фронтенда).

## Цель

Выбран веб-фреймворк (FastAPI — естественный выбор при SQLAlchemy/Pydantic-стеке, но
зафиксировать явно), каркас поднимается, health-check отвечает.

## Что сделать

1. Выбрать и подключить фреймворк, зафиксировать выбор в журнале шага (обоснование:
   существующий стек — SQLAlchemy, `uv`, никакого Django).
2. Роутер-каркас под неймспейс `/api/v1/courses/{course_uuid}/ai-analysis/...` по
   контракту TDD.
3. `/health` эндпоинт, подключение к БД проверяется на старте (переиспользует E0).
4. Auth — согласовать со владельцем схему (BFF-прокси уже разграничивает доступ на
   уровне `SPHERA`, но сервис не должен быть открыт в интернет без проверки — минимум
   shared-secret заголовок между BFF и AI-сервисом).

## Файлы

- `src/sfera_ai/api/app.py` — точка входа
- `src/sfera_ai/api/routes/__init__.py`
- `tests/api/test_health.py`

## Критерии готовности (DoD)

- [x] Сервер стартует, `/health` отвечает 200
- [x] Auth-заголовок между BFF и сервисом согласован и реализован (не открытый эндпоинт)

## Как проверить

```bash
uv run uvicorn sfera_ai.api.app:app --reload
curl localhost:8000/health
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-28` — выполнено: фреймворк **FastAPI** (`fastapi==0.141.1` + `uvicorn[standard]`) —
  естественный выбор при существующем SQLAlchemy/Pydantic-стеке, Django в проекте нет.
  `src/sfera_ai/api/app.py` — `create_app(*, engine_factory, bff_shared_secret=None)`,
  `/health` открывает соединение через переданный движок и делает `SELECT 1` (реальный
  сбой БД → 500, не тихий 200). **Важно:** `app = create_app()` НЕ вызывается на уровне
  модуля — иначе `Settings()` дёргалась бы при любом импорте модуля (в т.ч. в тестах) и
  падала без полного `.env`. Вместо этого uvicorn запускается в **factory-режиме**
  (`uvicorn sfera_ai.api.app:create_app --factory`), `Settings()` вызывается только при
  реальном старте сервера. `src/sfera_ai/api/routes/__init__.py` — пустой `APIRouter`
  с префиксом `/api/v1/courses/{course_uuid}/ai-analysis` по контракту `03_TDD.md`
  «3. API / контракты» — эндпоинты добавляются следующими шагами эпика E8.
  Auth — решение по варианту, который сам step предлагал минимумом: shared-secret
  заголовок `X-BFF-Shared-Secret` (`src/sfera_ai/api/auth.py`,
  `make_bff_secret_dependency`), сверяется с новым полем `Settings.bff_shared_secret`,
  навешан как `dependencies=[...]` на весь `api_v1_router` (не на `/health` — health
  должен быть доступен инфраструктуре без секрета). `.env`/`.env.example` — под
  глобальным запретом чтения/правки агента (секреты), владелец должен сам вписать
  `BFF_SHARED_SECRET=<random>`. `Dockerfile` CMD заменён с временного `smoke_test` на
  `uvicorn sfera_ai.api.app:create_app --factory --host 0.0.0.0 --port 8000`.
  Тесты — `tests/api/test_health.py` (2, TestClient + sqlite in-memory engine) и
  `tests/api/test_auth.py` (3, юнит-тест dependency — роутер пока пуст, интеграционно
  через реальный защищённый эндпоинт проверить нечем до следующих шагов E8). Ручная
  проверка — `uvicorn ... --factory` поднят локально, `curl localhost:8123/health` →
  `{"status":"ok"}`, HTTP 200. Владелец добавил `BFF_SHARED_SECRET` в `.env`
  (2026-08-28) — `uv run pytest` — 133 passed, регрессий нет.

  **Открытый пункт вне scope этого шага:** подключение к BFF-прокси SPHERA
  (`SPHERA/src/app/api/proxy/[[...path]]/route.ts`) ещё не сделано — существующий
  прокси проксирует только к `sfera_backend`, про AI-сервис/`X-BFF-Shared-Secret`
  там ничего нет. Отдельная задача во фронтенд-репозитории, другой репозиторий,
  правки — с явного разрешения владельца.
