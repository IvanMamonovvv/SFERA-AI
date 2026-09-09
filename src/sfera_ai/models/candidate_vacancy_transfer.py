from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class CandidateVacancyTransfer(TimestampMixin, Base):
    """Отметка «кандидат передан заказчику» по курсу/вакансии — отдельно от версионной
    истории `CandidateVacancyAnalysis`, не сбрасывается при пересчёте fit
    (design doc «Данные», step-E15-01)."""

    __tablename__ = "ai_candidate_vacancy_transfer"
    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id", "course_id",
            name="uq_candidate_vacancy_transfer_candidate_course",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    transferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
