# Шаг E1-01 — Alembic — инициализация

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E0 (весь эпик)

## Цель

Alembic инициализирован, `env.py` читает URL из `Settings` и метаданные из `Base`.

## Что сделать

**Step 1: Добавить зависимость**

Run: `uv add "alembic>=1.13"`

**Step 2: Инициализировать**

Run: `uv run alembic init migrations`

**Step 3: Настроить `migrations/env.py` на чтение URL из Settings и метаданные из `Base`**

```python
# migrations/env.py — заменить блок конфигурации на:
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sfera_ai.config import Settings
from sfera_ai.db.base import Base

config.set_main_option("sqlalchemy.url", Settings().write_database_url)
target_metadata = Base.metadata
```

(Оставить остальной сгенерированный boilerplate `env.py` как есть —
`run_migrations_offline`/`run_migrations_online`.)

**Step 4: Commit**

```bash
git add alembic.ini migrations pyproject.toml uv.lock
git commit -m "chore: initialize Alembic for AI-owned tables"
```

## Файлы

- `alembic.ini` — создать
- `migrations/env.py` — создать
- `migrations/script.py.mako` — создать
- `pyproject.toml` — изменить (добавить зависимость `alembic`)

## Критерии готовности (DoD)

- [x] `alembic.ini`/`migrations/` присутствуют, `env.py` читает `write_database_url`

## Как проверить

```bash
uv run alembic current
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — выполнено с отклонением от порядка: `write_database_url` (E1-02) и
  `Base`/`TimestampMixin` (E1-03) реализованы первыми — E1-01 фактически от них зависит,
  а не наоборот (в step-файлах эпика указано обратное). `uv add alembic`,
  `alembic init migrations`, `env.py` настроен на `Settings().write_database_url` и
  `Base.metadata`. Коммит `ac26c0a`. **Не сделано:** `uv run alembic current` падает —
  `Settings()` требует оба URL из реального `.env`, файл под глобальным запретом
  чтения/правки, владелец добавит значения сам и подтвердит прогон.
- `2026-08-26` — DoD закрыт: владелец добавил в `.env` `WRITE_DATABASE_URL` на разовый
  локальный Postgres в Docker (`postgres:16`, порт 5434, только для проверки — не прод,
  контейнер снесён после теста). `uv run alembic current` прошёл, подключился, версии
  нет (миграций пока нет — ожидаемо). Реальный `WRITE_DATABASE_URL` для прода появится
  на шаге `step-E1-09-apply-migration-prod.md` (роль `ai_owner` ещё не создана).
