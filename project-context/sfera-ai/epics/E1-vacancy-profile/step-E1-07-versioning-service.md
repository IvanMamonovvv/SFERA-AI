# Шаг E1-07 — Versioning-сервис

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E1-04, E1-06
**Перед началом:** «Никогда не UPDATE `requirements` у существующей версии»
(`03_TDD.md`, раздел «2. Сущности / данные») — сервис только создаёт новые строки и
переключает `is_current` на предыдущей.

**Важное правило (применимо и к E6/E7 — везде, где переключается `is_current`):**
снятие `is_current=False` со старой записи требует `session.flush()` до `INSERT` новой
строки с `is_current=True` — иначе порядок операций в рамках одного flush не
гарантирован, и partial unique index на `is_current` может упасть.

## Цель

`create_vacancy_profile_version` создаёт новую иммутабельную версию, снимает
`is_current` со старой в той же транзакции.

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/services/test_vacancy_profile.py
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.vacancy_profile import VacancyProfile
from sfera_ai.services.vacancy_profile import create_vacancy_profile_version


def test_first_version_is_current(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = create_vacancy_profile_version(
            session, course_id=1, requirements={"must_have": ["B2B sales"]}, notes="", created_by_id=None,
        )
        assert profile.version == 1
        assert profile.is_current is True


def test_second_version_unsets_previous_current(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        create_vacancy_profile_version(session, course_id=1, requirements={"a": 1}, notes="", created_by_id=None)
        second = create_vacancy_profile_version(session, course_id=1, requirements={"a": 2}, notes="", created_by_id=None)

        rows = session.query(VacancyProfile).filter_by(course_id=1).order_by(VacancyProfile.version).all()
        assert [r.is_current for r in rows] == [False, True]
        assert second.version == 2
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/services/test_vacancy_profile.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать**

```python
# src/sfera_ai/services/vacancy_profile.py
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from sfera_ai.models.vacancy_profile import VacancyProfile


def create_vacancy_profile_version(
    session: Session,
    *,
    course_id: int,
    requirements: dict[str, Any],
    notes: str,
    created_by_id: int | None,
) -> VacancyProfile:
    previous_current = session.scalar(
        select(VacancyProfile).where(VacancyProfile.course_id == course_id, VacancyProfile.is_current.is_(True))
    )
    next_version = (previous_current.version + 1) if previous_current else 1

    if previous_current is not None:
        previous_current.is_current = False
        session.flush()  # UPDATE до INSERT — иначе partial unique index (uq_vacancy_profile_course_current)
        # может увидеть на миг две строки is_current=True на одном course_id (порядок flush не гарантирован)

    new_profile = VacancyProfile(
        course_id=course_id,
        version=next_version,
        is_current=True,
        requirements=requirements,
        notes=notes,
        created_by_id=created_by_id,
    )
    session.add(new_profile)
    session.commit()
    session.refresh(new_profile)
    return new_profile
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/services/test_vacancy_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/services tests/services/test_vacancy_profile.py
git commit -m "feat: add VacancyProfile versioning service"
```

## Файлы

- `src/sfera_ai/services/__init__.py` — создать
- `src/sfera_ai/services/vacancy_profile.py` — создать
- `tests/services/test_vacancy_profile.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/services/test_vacancy_profile.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/services/test_vacancy_profile.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-26 — `create_vacancy_profile_version` реализован, тесты `tests/services/test_vacancy_profile.py` зелёные (2 passed), полный сьют 9 passed. Коммит `20ade28`.
