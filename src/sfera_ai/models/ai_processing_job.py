from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin

REASONS = (
    "NEW_HH_LEAD", "NEW_APPLICATION", "NEW_ANSWER", "NEW_RESUME", "NEW_VIDEO",
    "CANDIDATE_DATA_CHANGED", "VACANCY_PROFILE_CHANGED", "FEEDBACK_APPLIED",
    "MANUAL", "BACKFILL",
)
STATUSES = ("PENDING", "PROCESSING", "DONE", "FAILED")


class AIProcessingJob(TimestampMixin, Base):
    """Собственная очередь обработки (03_TDD.md, «2. Сущности / данные», «6. Processing Queue»)."""

    __tablename__ = "ai_processing_job"
    __table_args__ = (
        Index("ix_processing_job_status_retry_after", "status", "retry_after"),
        Index(
            "uq_processing_job_candidate_course_reason_open",
            "candidate_profile_id", "course_id", "reason",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'PROCESSING')"),
            sqlite_where=text("status IN ('PENDING', 'PROCESSING')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
