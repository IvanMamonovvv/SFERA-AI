# Шаг E1-03 — Declarative Base + timestamp mixin

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1-01

## Цель

`Base`/`TimestampMixin` готовы — общий фундамент для всех будущих `ai_*`-моделей
(`created_at`/`updated_at` через `server_default`/`onupdate`).

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/test_db_base.py
from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class Dummy(TimestampMixin, Base):
    __tablename__ = "dummy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


def test_timestamp_mixin_has_created_and_updated(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    from sqlalchemy.orm import Session

    with Session(tmp_engine) as session:
        row = Dummy()
        session.add(row)
        session.commit()
        session.refresh(row)
        assert isinstance(row.created_at, datetime)
        assert isinstance(row.updated_at, datetime)
```

**Step 2: Добавить фикстуру `tmp_engine` (in-memory SQLite)**

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine


@pytest.fixture()
def tmp_engine():
    return create_engine("sqlite:///:memory:")
```

**Step 3: Запустить, убедиться что падает**

Run: `uv run pytest tests/test_db_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sfera_ai.db.base'`

**Step 4: Реализовать**

```python
# src/sfera_ai/db/base.py
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

**Step 5: Запустить, убедиться что проходит**

Run: `uv run pytest tests/test_db_base.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/sfera_ai/db tests/test_db_base.py tests/conftest.py
git commit -m "feat: add declarative Base and timestamp mixin for AI-owned tables"
```

## Файлы

- `src/sfera_ai/db/__init__.py` — создать
- `src/sfera_ai/db/base.py` — создать
- `tests/test_db_base.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/test_db_base.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/test_db_base.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — выполнено: `src/sfera_ai/db/base.py` (`Base`, `TimestampMixin`),
  `tests/conftest.py` (`tmp_engine` sqlite in-memory), `tests/test_db_base.py` зелёный.
  Коммит `ef4cc07`.
