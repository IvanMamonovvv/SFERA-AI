# Шаг E0-06 — Dockerfile

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E0-01, E0-05

## Цель

Multi-stage `Dockerfile` собирается без ошибок, контейнер запускает smoke-test.

## Что сделать

**Step 1: `.dockerignore`**

```
.venv/
.git/
__pycache__/
*.egg-info/
.env
docs/
```

**Step 2: Dockerfile (multi-stage, uv)**

```dockerfile
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
RUN uv sync --frozen --no-dev

# Временный CMD для bootstrap-этапа — smoke_test.main() требует application_id аргументом,
# `docker run` без --entrypoint упадёт. Заменяется реальным entrypoint в E8 (05_EPICS.md).
CMD ["uv", "run", "python", "-m", "sfera_ai.smoke_test"]
```

**Step 3: Проверить сборку**

Run: `docker build -t sfera-ai:bootstrap .`
Expected: сборка проходит без ошибок.

**Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "chore: add Dockerfile for AI service"
```

## Файлы

- `Dockerfile` — создать
- `.dockerignore` — создать

## Критерии готовности (DoD)

- [ ] `docker build` проходит без ошибок

## Как проверить

```bash
docker build -t sfera-ai:bootstrap .
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
