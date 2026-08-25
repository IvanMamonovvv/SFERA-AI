# Шаг E1-06 — Write-сессия

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E1-02

## Цель

`make_write_engine`/`make_session_factory` дают рабочую сессию к БД по
`write_database_url`.

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/test_db_session.py
from sqlalchemy.orm import Session

from sfera_ai.db.session import make_session_factory


def test_make_session_factory_returns_working_session(tmp_engine):
    factory = make_session_factory(tmp_engine)
    with factory() as session:
        assert isinstance(session, Session)
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/test_db_session.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать**

```python
# src/sfera_ai/db/session.py
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from sfera_ai.config import Settings


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_write_engine(settings: Settings | None = None) -> Engine:
    settings = settings or Settings()
    return create_engine(settings.write_database_url)
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/test_db_session.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/db/session.py tests/test_db_session.py
git commit -m "feat: add write session factory for AI-owned tables"
```

## Файлы

- `src/sfera_ai/db/session.py` — создать
- `tests/test_db_session.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/test_db_session.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/test_db_session.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
