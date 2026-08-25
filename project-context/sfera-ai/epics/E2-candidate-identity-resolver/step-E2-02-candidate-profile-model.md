# Шаг E2-02 — `CandidateProfile` модель

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E1-03 (`Base`/`TimestampMixin`)
**Перед началом:** прочитай `03_TDD.md`, раздел «2. Сущности / данные», подраздел
`CandidateProfile`. Оба FK — обычные `Integer`, unique, nullable, без `ForeignKey()`
(платформенные таблицы только reflected). `CheckConstraint` — хотя бы один заполнен.

## Цель

Модель `CandidateProfile` с `CheckConstraint` «хотя бы один якорь заполнен».

## Что сделать

**Step 1: Написать падающий тест**

```python
# tests/models/test_candidate_profile.py
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sfera_ai.db.base import Base
from sfera_ai.models.candidate_profile import CandidateProfile


def test_candidate_profile_has_expected_columns():
    columns = {c.name for c in CandidateProfile.__table__.columns}
    assert columns == {
        "id", "application_id", "hh_negotiation_id", "facts", "data_completeness",
        "sources_snapshot", "version", "built_at", "is_superseded", "superseded_by_id",
        "created_at", "updated_at",
    }


def test_candidate_profile_requires_at_least_one_anchor(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        session.add(CandidateProfile(application_id=None, hh_negotiation_id=None))
        with pytest.raises(IntegrityError):
            session.commit()


def test_candidate_profile_allows_hh_lead_only(tmp_engine):
    Base.metadata.create_all(tmp_engine)
    with Session(tmp_engine) as session:
        profile = CandidateProfile(hh_negotiation_id=42)
        session.add(profile)
        session.commit()
        session.refresh(profile)
        assert profile.version == 1
        assert profile.data_completeness == "MINIMAL"
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/models/test_candidate_profile.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать модель**

```python
# src/sfera_ai/models/candidate_profile.py
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class CandidateProfile(TimestampMixin, Base):
    """Живой (мутируемый) снепшот фактов о человеке — ядро идентичности (03_TDD.md, «2. Сущности / данные»)."""

    __tablename__ = "ai_candidate_profile"
    __table_args__ = (
        CheckConstraint(
            "application_id IS NOT NULL OR hh_negotiation_id IS NOT NULL",
            name="ck_candidate_profile_has_anchor",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    hh_negotiation_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    facts: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    data_completeness: Mapped[str] = mapped_column(String(16), nullable=False, default="MINIMAL")
    sources_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    built_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_superseded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    superseded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ai_candidate_profile.id", ondelete="SET NULL"), nullable=True
    )
```

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/models/test_candidate_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/models/candidate_profile.py tests/models/test_candidate_profile.py
git commit -m "feat: add CandidateProfile SQLAlchemy model"
```

## Файлы

- `src/sfera_ai/models/candidate_profile.py` — создать
- `tests/models/test_candidate_profile.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/models/test_candidate_profile.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/models/test_candidate_profile.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
