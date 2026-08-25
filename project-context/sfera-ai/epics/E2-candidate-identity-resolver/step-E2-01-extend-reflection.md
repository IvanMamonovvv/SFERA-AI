# Шаг E2-01 — Расширить reflection-набор платформенных таблиц

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E0 (`platform_db.py`), E1 (Alembic-паттерн)
**Перед началом:** резолверу identity нужна ещё `headhunter_hhnegotiationrecord` (для
проверки обратной связи `application` при защите от гонки).

## Цель

`reflect_platform_tables` умеет отражать `headhunter_hhnegotiationrecord`, добавлена
именованная константа набора таблиц для эпика E2.

## Что сделать

**Step 1: Расширить падающий тест**

```python
# добавить в tests/test_platform_db.py
def test_reflect_platform_tables_includes_hh_negotiation_record():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql("CREATE TABLE testchecks_answer (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, application_id INTEGER)"
        )

    base = reflect_platform_tables(
        engine, tables=("courses_application", "testchecks_answer", "headhunter_hhnegotiationrecord")
    )

    assert "headhunter_hhnegotiationrecord" in base.classes.keys()
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/test_platform_db.py -v`
Expected: FAIL (таблицы ещё нет в тестовой схеме предыдущего теста — на самом деле
`reflect_platform_tables` уже общая функция из эпика E0, этот тест просто проверяет её
на новом наборе таблиц; должен упасть только если таблица не создана в фикстуре —
убедиться, что тест вообще запускается и падает по ожидаемой причине перед Step 3,
иначе перейти сразу к Step 4).

**Step 3: Функция не меняется — `reflect_platform_tables` уже принимает произвольный
`tables`. Добавить именованную константу для набора таблиц эпика E2.**

```python
# src/sfera_ai/platform_db.py — добавить в конец файла
IDENTITY_RESOLVER_TABLES = ("courses_application", "headhunter_hhnegotiationrecord")
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/test_platform_db.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/platform_db.py tests/test_platform_db.py
git commit -m "feat: extend platform reflection to headhunter_hhnegotiationrecord"
```

## Файлы

- `src/sfera_ai/platform_db.py` — изменить
- `tests/test_platform_db.py` — изменить

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/test_platform_db.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/test_platform_db.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
