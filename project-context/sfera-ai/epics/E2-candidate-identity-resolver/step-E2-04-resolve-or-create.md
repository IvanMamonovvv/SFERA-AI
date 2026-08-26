# Шаг E2-04 — `resolve_or_create_candidate_profile` — сервис identity

**Статус:** DONE
**Слой:** Backend · **Зависит от:** E2-02, E2-01
**Перед началом:** прочитай `03_TDD.md`, раздел «Candidate Identity»; `02_CONTEXT.md`,
«Граничные случаи». Два входа — `NEW_HH_LEAD` (передан `hh_negotiation_id`) и
`NEW_APPLICATION` (передан `application_id`). Для `NEW_APPLICATION` сервис обязан
сначала проверить через reflection, есть ли у этого `Application` обратная связь
`HHNegotiationRecord` (поле `application_id` на платформенной таблице
`headhunter_hhnegotiationrecord`) — если есть, искать/обновлять существующий
`CandidateProfile` по `hh_negotiation_id`, а не создавать новый по `application_id`.
Платформенное чтение делается через `AutomapBase`, переданный вызывающим кодом (не
создаётся engine внутри сервиса — тестируется на in-memory SQLite без реального
Postgres).

## Цель

`resolve_or_create_candidate_profile` защищён от гонки HH Lead / Application — ровно
один `CandidateProfile` на человека даже при пересекающихся вызовах.

## Что сделать

**Step 1: Написать падающие тесты**

```python
# tests/services/test_candidate_identity.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile
from sfera_ai.platform_db import reflect_platform_tables
from sfera_ai.services.candidate_identity import resolve_or_create_candidate_profile


def _platform_base_with_hh_record(application_id_for_hh=None):
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE courses_application (id INTEGER PRIMARY KEY)")
        conn.exec_driver_sql(
            "CREATE TABLE headhunter_hhnegotiationrecord (id INTEGER PRIMARY KEY, application_id INTEGER)"
        )
        if application_id_for_hh is not None:
            conn.exec_driver_sql(
                f"INSERT INTO headhunter_hhnegotiationrecord (id, application_id) VALUES (99, {application_id_for_hh})"
            )
    base = reflect_platform_tables(engine, tables=("courses_application", "headhunter_hhnegotiationrecord"))
    return base


def test_new_hh_lead_creates_profile_with_hh_negotiation_only(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_hh_record()
    with Session(tmp_engine) as session:
        profile = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, hh_negotiation_id=42,
        )
        assert profile.hh_negotiation_id == 42
        assert profile.application_id is None


def test_new_application_creates_profile_when_no_hh_link(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_hh_record()  # нет привязанного HH-лида
    with Session(tmp_engine) as session:
        profile = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, application_id=7,
        )
        assert profile.application_id == 7
        assert profile.hh_negotiation_id is None


def test_new_application_resolves_existing_hh_lead_profile_no_duplicate(tmp_engine):
    """Гонка: Application уже привязан к HHNegotiationRecord(id=99) в платформе,
    но AI-профиль по этому лиду ещё существует только с hh_negotiation_id=99.
    Вызов resolve_or_create с application_id=7 не должен создать второй CandidateProfile."""
    Base.metadata.create_all(tmp_engine)
    platform_base = _platform_base_with_hh_record(application_id_for_hh=7)
    with Session(tmp_engine) as session:
        existing = CandidateProfile(hh_negotiation_id=99)
        session.add(existing)
        session.commit()

        resolved = resolve_or_create_candidate_profile(
            session, platform_base=platform_base, application_id=7,
        )

        assert resolved.id == existing.id
        assert resolved.hh_negotiation_id == 99
        assert resolved.application_id == 7  # дозаполнено на месте

        count = session.query(CandidateProfile).count()
        assert count == 1


def test_concurrent_insert_race_resolves_to_winner_no_crash(tmp_engine):
    """_insert_or_resolve_race — прямой юнит-тест на путь IntegrityError: строка с тем же
    application_id уже вставлена (эмулирует выигравшую параллельную джобу, коммит между
    чужим SELECT-miss и своим INSERT — 03_TDD.md, «Processing Queue», параллельный batch).
    Второй insert обязан упасть на UniqueConstraint и резолвиться в выигравшую строку, не
    пробрасывая IntegrityError наружу."""
    from sfera_ai.services.candidate_identity import _insert_or_resolve_race

    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        winner = CandidateProfile(application_id=7)
        session.add(winner)
        session.commit()
        winner_id = winner.id

        loser = CandidateProfile(application_id=7)
        resolved = _insert_or_resolve_race(
            session, loser,
            lookup_column=CandidateProfile.application_id, lookup_value=7,
        )
        assert resolved.id == winner_id
        assert session.query(CandidateProfile).count() == 1
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/services/test_candidate_identity.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать**

```python
# src/sfera_ai/services/candidate_identity.py
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.models.candidate_profile import CandidateProfile


def _insert_or_resolve_race(session: Session, profile: CandidateProfile, *, lookup_column, lookup_value) -> CandidateProfile:
    """Вставляет profile; если параллельный вызов уже успел вставить строку с тем же
    application_id/hh_negotiation_id (UniqueConstraint), не падает наружу — резолвит
    в выигравшую строку. Защита от гонки двух джоб на одном тике (03_TDD.md, «Processing
    Queue» — параллельная обработка батча)."""
    session.add(profile)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        winner = session.scalar(select(CandidateProfile).where(lookup_column == lookup_value))
        if winner is None:
            raise  # не гонка за этот якорь — реальная ошибка, пробрасываем
        return winner
    session.refresh(profile)
    return profile


def _find_hh_negotiation_for_application(platform_base, application_id: int) -> int | None:
    """Читает платформенную таблицу headhunter_hhnegotiationrecord через reflection —
    есть ли запись с application_id == данный (обратная OneToOne). Read-only."""
    from sqlalchemy.orm import Session as PlatformSession

    HHNegotiationRecord = platform_base.classes.headhunter_hhnegotiationrecord
    engine = platform_base.metadata.bind
    with PlatformSession(engine) as platform_session:
        record = platform_session.scalar(
            select(HHNegotiationRecord).where(HHNegotiationRecord.application_id == application_id)
        )
        return record.id if record is not None else None


def resolve_or_create_candidate_profile(
    session: Session,
    *,
    platform_base,
    application_id: int | None = None,
    hh_negotiation_id: int | None = None,
) -> CandidateProfile:
    if application_id is None and hh_negotiation_id is None:
        raise ValueError("either application_id or hh_negotiation_id is required")

    if hh_negotiation_id is not None:
        existing = session.scalar(
            select(CandidateProfile).where(CandidateProfile.hh_negotiation_id == hh_negotiation_id)
        )
        if existing is not None:
            return existing
        profile = CandidateProfile(hh_negotiation_id=hh_negotiation_id, application_id=application_id)
        return _insert_or_resolve_race(
            session, profile,
            lookup_column=CandidateProfile.hh_negotiation_id, lookup_value=hh_negotiation_id,
        )

    # application_id задан, hh_negotiation_id — нет: проверить гонку через reflection
    linked_hh_id = _find_hh_negotiation_for_application(platform_base, application_id)
    if linked_hh_id is not None:
        existing = session.scalar(
            select(CandidateProfile).where(CandidateProfile.hh_negotiation_id == linked_hh_id)
        )
        if existing is not None:
            if existing.application_id is None:
                existing.application_id = application_id
                session.commit()
                session.refresh(existing)
            return existing
        # HH-лид есть на платформе, но AI-профиля по нему ещё нет — создать сразу с обоими якорями
        profile = CandidateProfile(hh_negotiation_id=linked_hh_id, application_id=application_id)
        return _insert_or_resolve_race(
            session, profile,
            lookup_column=CandidateProfile.hh_negotiation_id, lookup_value=linked_hh_id,
        )

    existing = session.scalar(
        select(CandidateProfile).where(CandidateProfile.application_id == application_id)
    )
    if existing is not None:
        return existing

    profile = CandidateProfile(application_id=application_id)
    return _insert_or_resolve_race(
        session, profile,
        lookup_column=CandidateProfile.application_id, lookup_value=application_id,
    )
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/services/test_candidate_identity.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/services/candidate_identity.py tests/services/test_candidate_identity.py
git commit -m "feat: add resolve_or_create_candidate_profile with race protection"
```

## Файлы

- `src/sfera_ai/services/candidate_identity.py` — создать
- `tests/services/test_candidate_identity.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/services/test_candidate_identity.py -v` зелёный
- [ ] Тест на гонку HH Lead/Application подтверждает отсутствие дублей
- [ ] Тест на конкурентную вставку (`IntegrityError` из `UniqueConstraint`) подтверждает
      резолв в выигравшую строку без падения наружу

## Как проверить

```bash
uv run pytest tests/services/test_candidate_identity.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `2026-08-26` — реализован `resolve_or_create_candidate_profile` + `_insert_or_resolve_race`
  + `_find_hh_negotiation_for_application`. Все 4 теста зелёные. Правка `platform_db.py`:
  `reflect_platform_tables` теперь кладёт `base.engine = engine` — в SQLAlchemy 2.0
  `MetaData.bind` убран, engine платформы больше негде было взять внутри сервиса.
