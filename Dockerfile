FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
RUN uv sync --frozen --no-dev

# Временный CMD для bootstrap-этапа — smoke_test.main() требует application_id аргументом,
# `docker run` без --entrypoint упадёт. Заменяется реальным entrypoint в E8 (05_EPICS.md).
CMD ["uv", "run", "python", "-m", "sfera_ai.smoke_test"]
