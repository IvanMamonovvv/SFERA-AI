# Шаг E0-03 — Reflection-модуль (automap на 2-3 таблицах)

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E0-02
**Перед началом:** reflection нужно ограничить конкретными таблицами
(`courses_application`, `testchecks_answer`) через `only=[...]`, иначе automap
попытается отразить всю схему платформы (десятки таблиц, лишняя нагрузка и риск
зацепить то, что не нужно).

## Цель

`reflect_platform_tables(engine, tables=...)` строит `AutomapBase`, ограниченный
переданным списком таблиц.

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/test_platform_db.py
from sqlalchemy import create_engine

from sfera_ai.platform_db import reflect_platform_tables

PLATFORM_TABLES = ("courses_application", "testchecks_answer")


def test_reflect_platform_tables_exposes_only_listed_tables():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE unrelated_table (id INTEGER PRIMARY KEY)")

    base = reflect_platform_tables(engine, tables=PLATFORM_TABLES)

    assert set(base.classes.keys()) == {"courses_application", "testchecks_answer"}
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/test_platform_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sfera_ai.platform_db'`

**Step 3: Реализовать `reflect_platform_tables`**

```python
# src/sfera_ai/platform_db.py
from collections.abc import Sequence

from sqlalchemy import Engine, MetaData
from sqlalchemy.ext.automap import AutomapBase, automap_base


def reflect_platform_tables(engine: Engine, *, tables: Sequence[str]) -> AutomapBase:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=tables)
    base = automap_base(metadata=metadata)
    base.prepare()
    return base
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/test_platform_db.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/platform_db.py tests/test_platform_db.py
git commit -m "feat: add scoped SQLAlchemy automap reflection for platform tables"
```

## Файлы

- `src/sfera_ai/platform_db.py` — создать
- `tests/test_platform_db.py` — тест (unit, без реальной БД, только mock-engine)

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/test_platform_db.py -v` зелёный
- [ ] Reflection не захватывает таблицы вне переданного списка

## Как проверить

```bash
uv run pytest tests/test_platform_db.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
