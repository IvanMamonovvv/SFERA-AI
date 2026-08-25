# Шаг E0-05 — Smoke-test: прочитать одну реальную запись `Application`

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E0-03, E0-04

## Цель

Entrypoint читает по id одну реальную запись `Application` через reflection, ничего не
пишет.

## Что сделать

**Step 1: Реализовать entrypoint**

```python
# src/sfera_ai/smoke_test.py
import sys

from sqlalchemy import create_engine

from sfera_ai.config import Settings
from sfera_ai.platform_db import reflect_platform_tables

PLATFORM_TABLES = ("courses_application", "testchecks_answer")


def main(application_id: int) -> None:
    settings = Settings()
    engine = create_engine(settings.platform_database_url)
    base = reflect_platform_tables(engine, tables=PLATFORM_TABLES)
    Application = base.classes.courses_application

    from sqlalchemy.orm import Session
    from sqlalchemy.exc import DBAPIError

    with Session(engine) as session:
        app = session.get(Application, application_id)
        if app is None:
            print(f"Application {application_id} not found", file=sys.stderr)
            raise SystemExit(1)
        print(f"OK: read Application id={app.id}")

        # Подтверждаем, что роль ai_readonly реально read-only — не только по DDL,
        # но и на практике: попытка записи должна упасть InsufficientPrivilege.
        try:
            session.execute(
                Application.__table__.update()
                .where(Application.id == application_id)
                .values(comment=app.comment)
            )
            session.rollback()
            print(
                "FAIL: write succeeded through ai_readonly — role is not actually read-only",
                file=sys.stderr,
            )
            raise SystemExit(1)
        except DBAPIError:
            session.rollback()
            print("OK: write correctly rejected (read-only role confirmed)")


if __name__ == "__main__":
    main(int(sys.argv[1]))
```

**Step 2: Ручной прогон (не автотест — требует реального туннеля и реальных данных)**

Run: `uv run python -m sfera_ai.smoke_test <реальный_id_application>`
Expected: `OK: read Application id=<id>`, затем `OK: write correctly rejected (read-only
role confirmed)` — без исключений наружу, без реальной записи.

**Step 3: Commit**

```bash
git add src/sfera_ai/smoke_test.py
git commit -m "feat: add DB reflection smoke test entrypoint"
```

## Файлы

- `src/sfera_ai/smoke_test.py` — создать

## Критерии готовности (DoD)

- [ ] Ручной прогон на реальном `application_id` печатает `OK: read Application id=<id>`
- [ ] Попытка записи через `ai_readonly` падает с `DBAPIError`/`InsufficientPrivilege`,
      скрипт печатает `OK: write correctly rejected` — подтверждает, что роль реально
      read-only, а не просто задокументирована как таковая
- [ ] Ничего не записывается в платформенную БД

## Как проверить

```bash
uv run python -m sfera_ai.smoke_test <реальный_id_application>
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано, id проверенной записи>.
