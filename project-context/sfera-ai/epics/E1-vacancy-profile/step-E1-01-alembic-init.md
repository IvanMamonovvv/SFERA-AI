# Шаг E1-01 — Alembic — инициализация

**Статус:** TODO
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

- [ ] `alembic.ini`/`migrations/` присутствуют, `env.py` читает `write_database_url`

## Как проверить

```bash
uv run alembic current
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
