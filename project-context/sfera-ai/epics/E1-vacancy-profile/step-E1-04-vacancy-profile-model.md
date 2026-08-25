# Шаг E1-04 — `VacancyProfile` модель

**Статус:** TODO
**Слой:** Backend · **Зависит от:** E1-03
**Перед началом:** прочитай `03_TDD.md`, раздел «2. Сущности / данные». `course_id` —
обычный Integer, FK-констрейнт на `courses_course.id` создаётся в Alembic-миграции
(E1-05) через raw DDL, не через `ForeignKey()` в модели (нет ORM-класса `Course` в этом
сервисе — платформенные таблицы только reflected, эпик E0). В модели `course_id` —
просто `Mapped[int]`, без `ForeignKey`.

## Цель

Модель `VacancyProfile` с полями и `UniqueConstraint(course_id, version)` по TDD.

## Что сделать

**Step 1: Написать падающий тест (структура полей + constraint на уровне Python, без БД)**

```python
# tests/models/test_vacancy_profile.py
from sfera_ai.models.vacancy_profile import VacancyProfile


def test_vacancy_profile_has_expected_columns():
    columns = {c.name for c in VacancyProfile.__table__.columns}
    assert columns == {
        "id", "course_id", "version", "is_current", "requirements",
        "notes", "created_by_id", "created_at",
    }


def test_vacancy_profile_unique_constraint_on_course_and_version():
    constraint_columns = {
        tuple(c.name for c in uc.columns)
        for uc in VacancyProfile.__table__.constraints
        if uc.__class__.__name__ == "UniqueConstraint"
    }
    assert ("course_id", "version") in constraint_columns
```

**Step 2: Запустить, убедиться что падает**

Run: `uv run pytest tests/models/test_vacancy_profile.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Реализовать модель**

```python
# src/sfera_ai/models/vacancy_profile.py
from typing import Any

from sqlalchemy import Integer, JSON, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class VacancyProfile(TimestampMixin, Base):
    """Структурированные требования заказчика к вакансии (03_TDD.md, раздел «2. Сущности / данные»)."""

    __tablename__ = "ai_vacancy_profile"
    __table_args__ = (UniqueConstraint("course_id", "version", name="uq_vacancy_profile_course_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

Примечание: у модели нет своего `created_at` — используется из `TimestampMixin` (та же
семантика, что `auto_now_add`); `updated_at` из миксина здесь избыточен (версии
иммутабельны), но оставлен для единообразия со всеми `ai_*`-таблицами — обсудить на
код-ревью, не критично.

**Step 4: Запустить, убедиться что проходит**

Run: `uv run pytest tests/models/test_vacancy_profile.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/sfera_ai/models tests/models/test_vacancy_profile.py
git commit -m "feat: add VacancyProfile SQLAlchemy model"
```

## Файлы

- `src/sfera_ai/models/__init__.py` — создать
- `src/sfera_ai/models/vacancy_profile.py` — создать
- `tests/models/test_vacancy_profile.py` — тест

## Критерии готовности (DoD)

- [ ] `uv run pytest tests/models/test_vacancy_profile.py -v` зелёный

## Как проверить

```bash
uv run pytest tests/models/test_vacancy_profile.py -v
```

## Как отметить выполнение

1. Впиши результат в журнал ниже. 2. Статус → `DONE`. 3. Обнови `04_STATE.md`.

## Журнал

- `YYYY-MM-DD` — <что сделано>.
