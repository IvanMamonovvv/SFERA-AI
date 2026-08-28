from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin

SENTIMENTS = ("POSITIVE", "NEGATIVE", "NEUTRAL")


class VacancyFeedback(TimestampMixin, Base):
    """Сырой фидбек менеджера/заказчика по кандидату или вакансии (03_TDD.md, «2. Сущности / данные»)."""

    __tablename__ = "ai_vacancy_feedback"
    __table_args__ = (
        Index("ix_vacancy_feedback_course_applied", "course_id", "applied"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ai_candidate_profile.id", ondelete="CASCADE"), nullable=True
    )
    analysis_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ai_candidate_vacancy_analysis.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str] = mapped_column(String(16), nullable=False)
    ai_suggested_rule: Mapped[str] = mapped_column(Text, nullable=False, default="")
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
