# Шаг E0-02 — Env-конфиг (pydantic-settings)

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E0-01

## Цель

`Settings` читает `PLATFORM_DATABASE_URL` из окружения/`.env`.

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/test_config.py
import os

from sfera_ai.config import Settings


def test_settings_reads_platform_database_url(monkeypatch):
    monkeypatch.setenv("PLATFORM_DATABASE_URL", "postgresql+psycopg://ai_readonly:secret@localhost:5433/sfera")
    settings = Settings()
    assert settings.platform_database_url == "postgresql+psycopg://ai_readonly:secret@localhost:5433/sfera"
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sfera_ai.config'`

**Step 3: Реализовать `Settings`**

```python
# src/sfera_ai/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    platform_database_url: str
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Создать `.env.example` (без реального пароля)**

```
# Read-only подключение к Postgres платформы SFERA (роль ai_readonly).
# Локально — через SSH-туннель, см. epics/E0-service-bootstrap/step-E0-04-ssh-tunnel.md.
PLATFORM_DATABASE_URL=postgresql+psycopg://ai_readonly:CHANGE_ME@localhost:5433/CHANGE_ME
```

**Step 6: Commit**

```bash
git add src/sfera_ai/config.py .env.example tests/test_config.py
git commit -m "feat: add env-based settings for platform DB connection"
```

## Файлы

- `src/sfera_ai/config.py` — создать
- `.env.example` — создать
- `tests/test_config.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/test_config.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/test_config.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
