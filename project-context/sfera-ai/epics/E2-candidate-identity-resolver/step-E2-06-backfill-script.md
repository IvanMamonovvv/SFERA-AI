# Шаг E2-06 — Read-only backfill-скрипт

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E2-04
**Перед началом:** `05_EPICS.md`, эпик E2: «read-only backfill-скрипт для первого
прогона по существующим `Application`/`HHNegotiationRecord`». Читает платформу через
reflection (read-only роль `ai_readonly`), пишет только в `ai_candidate_profile` (роль
`ai_owner`) — два разных подключения к БД, как в эпиках E0/E1.

## Цель

Backfill-скрипт проходит по существующим `HHNegotiationRecord`/`Application` и создаёт
`CandidateProfile` без дублей.

## Что сделать

**Step 1: Реализовать entrypoint (без юнит-теста — интеграционный скрипт, ручной прогон)**

```python
# src/sfera_ai/cli/backfill_candidate_profiles.py
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sfera_ai.config import Settings
from sfera_ai.db.session import make_write_engine
from sfera_ai.platform_db import IDENTITY_RESOLVER_TABLES, reflect_platform_tables
from sfera_ai.services.candidate_identity import resolve_or_create_candidate_profile


def main() -> None:
    settings = Settings()
    platform_engine = create_engine(settings.platform_database_url)
    platform_base = reflect_platform_tables(platform_engine, tables=IDENTITY_RESOLVER_TABLES)
    Application = platform_base.classes.courses_application
    HHNegotiationRecord = platform_base.classes.headhunter_hhnegotiationrecord

    write_engine = make_write_engine(settings)

    created = 0
    with Session(platform_engine) as platform_session, Session(write_engine) as write_session:
        for record in platform_session.scalars(select(HHNegotiationRecord)):
            resolve_or_create_candidate_profile(
                write_session, platform_base=platform_base,
                hh_negotiation_id=record.id, application_id=record.application_id,
            )
            created += 1

        hh_linked_application_ids = {
            r.application_id for r in platform_session.scalars(select(HHNegotiationRecord))
            if r.application_id is not None
        }
        for application in platform_session.scalars(select(Application)):
            if application.id in hh_linked_application_ids:
                continue  # уже обработан через HHNegotiationRecord выше
            resolve_or_create_candidate_profile(
                write_session, platform_base=platform_base, application_id=application.id,
            )
            created += 1

    print(f"OK: processed {created} platform records, 0 platform writes", file=sys.stderr)


if __name__ == "__main__":
    main()
```

**Step 2: Ручной прогон (требует туннеля с обоими наборами credentials —
`ai_readonly` для `PLATFORM_DATABASE_URL`, `ai_owner` для `WRITE_DATABASE_URL`)**

Run: `uv run python -m sfera_ai.cli.backfill_candidate_profiles`
Expected: `OK: processed N platform records, 0 platform writes` — проверить вручную
через `sfera_ai.cli.vacancy_profile`-подобный `SELECT COUNT(*) FROM ai_candidate_profile`
(или отдельным CLI-запросом), что дублей по `application_id`/`hh_negotiation_id` нет
(гарантировано `UniqueConstraint`, повторный прогон должен быть идемпотентен — упадёт
на 0 новых при повторе).

**Step 3: Commit**

```bash
git add src/sfera_ai/cli/backfill_candidate_profiles.py
git commit -m "feat: add read-only backfill script for CandidateProfile identity"
```

## Файлы

- `src/sfera_ai/cli/backfill_candidate_profiles.py` — создать

## Критерии готовности (DoD)

- [ ] Ручной прогон печатает `OK: processed N platform records, 0 platform writes`
- [ ] Повторный прогон не создаёт дублей

## Как проверить

```bash
uv run python -m sfera_ai.cli.backfill_candidate_profiles
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
