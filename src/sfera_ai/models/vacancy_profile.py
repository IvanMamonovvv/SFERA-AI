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
