from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin

WEIGHT_HINTS = ("BOOST", "PENALIZE", "INFO_ONLY")


class VacancyMemory(TimestampMixin, Base):
    """Утверждённое менеджером правило для будущих кандидатов вакансии (03_TDD.md, «2. Сущности / данные»)."""

    __tablename__ = "ai_vacancy_memory"
    __table_args__ = (
        Index("ix_vacancy_memory_course_is_active", "course_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    weight_hint: Mapped[str] = mapped_column(String(16), nullable=False)
    source_feedback_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ai_vacancy_feedback.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
