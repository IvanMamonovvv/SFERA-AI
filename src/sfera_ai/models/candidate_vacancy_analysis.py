from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class CandidateVacancyAnalysis(TimestampMixin, Base):
    """Результат Fit-анализа — иммутабельные append-only версии (03_TDD.md, «2. Сущности / данные»)."""

    __tablename__ = "ai_candidate_vacancy_analysis"
    __table_args__ = (
        UniqueConstraint(
            "candidate_profile_id", "course_id", "version",
            name="uq_candidate_vacancy_analysis_candidate_course_version",
        ),
        Index(
            "ix_candidate_vacancy_analysis_candidate_course_current",
            "candidate_profile_id", "course_id", "is_current",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # PROTECT (не CASCADE, в отличие от остальных FK этой модели) — история анализа
    # не должна молча исчезать при замене версии VacancyProfile (03_TDD.md, «CandidateVacancyAnalysis»).
    vacancy_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_vacancy_profile.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_completeness: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    strengths: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    gaps: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    missing_information: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    criteria_scores: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    contradictions: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    interview_questions: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_estimate: Mapped[Any | None] = mapped_column(Numeric(10, 4), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
