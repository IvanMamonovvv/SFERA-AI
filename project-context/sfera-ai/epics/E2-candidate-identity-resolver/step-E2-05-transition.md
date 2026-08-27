# Шаг E2-05 — Функция перехода HH Lead → Platform Candidate

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E2-04
**Перед началом:** прочитай `03_TDD.md`, «Candidate Identity». Detection-джоба (эпик E5,
здесь только сама функция) видит `HHNegotiationRecord.application_id IS NOT NULL` у
записи, чей связанный `CandidateProfile.application_id` всё ещё `None` — выполняет
`UPDATE` одной строки, не `INSERT`.

## Цель

`promote_hh_lead_to_application` обновляет профиль на месте, без пересоздания.

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/services/test_candidate_transition.py
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.services.candidate_transition import promote_hh_lead_to_application


def test_promote_updates_existing_profile_in_place(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        profile_id = profile.id

        updated = promote_hh_lead_to_application(session, hh_negotiation_id=42, application_id=7)

        assert updated is True
        session.refresh(profile)
        assert profile.id == profile_id  # тот же профиль, не пересоздан
        assert profile.application_id == 7


def test_promote_is_noop_if_already_promoted(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.add(CandidateProfile(hh_negotiation_id=42, application_id=7))
        session.commit()

        updated = promote_hh_lead_to_application(session, hh_negotiation_id=42, application_id=7)

        assert updated is False
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/services/test_candidate_transition.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать**

```python
# src/sfera_ai/services/candidate_transition.py
from sqlalchemy import update
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile


def promote_hh_lead_to_application(session: Session, *, hh_negotiation_id: int, application_id: int) -> bool:
    """UPDATE одной строки — переход HH Lead в Platform Candidate на месте, без INSERT."""
    result = session.execute(
        update(CandidateProfile)
        .where(CandidateProfile.hh_negotiation_id == hh_negotiation_id, CandidateProfile.application_id.is_(None))
        .values(application_id=application_id)
    )
    session.commit()
    return result.rowcount > 0
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/services/test_candidate_transition.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/services/candidate_transition.py tests/services/test_candidate_transition.py
git commit -m "feat: add HH lead to platform candidate transition service"
```

## Файлы

- `src/sfera_ai/services/candidate_transition.py` — создать
- `tests/services/test_candidate_transition.py` — тест

## Критерии готовности (DoD)

- [x] `uv run pytest tests/services/test_candidate_transition.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/services/test_candidate_transition.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- 2026-08-26 — реализован `promote_hh_lead_to_application`, оба теста зелёные, коммит `71ef56a`.
