FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations
RUN uv sync --frozen --no-dev

# step-E8-01-framework-scaffold.md — реальный entrypoint: FastAPI-приложение через
# uvicorn factory-режим (create_app() не вызывается на импорте модуля — см. api/app.py).
CMD ["uv", "run", "uvicorn", "sfera_ai.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
