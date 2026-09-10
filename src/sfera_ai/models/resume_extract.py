from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class ResumeExtract(TimestampMixin, Base):
    """Кэш распарсенного резюме — один источник, два возможных происхождения (03_TDD.md, «2. Сущности / данные»)."""

    __tablename__ = "ai_resume_extract"
    __table_args__ = (
        CheckConstraint(
            "(source_answer_id IS NOT NULL) != (hh_resume_id IS NOT NULL)",
            name="ck_resume_extract_exactly_one_source",
        ),
        # NULL != NULL в UNIQUE — несколько строк с hh_resume_id=NULL для одного
        # candidate_profile_id проходят (ANSI-семантика, одинаково в Postgres и SQLite).
        UniqueConstraint(
            "candidate_profile_id", "hh_resume_id", name="uq_resume_extract_candidate_hh_resume"
        ),
        Index("ix_resume_extract_status_retry_after", "status", "retry_after"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_candidate_profile.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_answer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    hh_resume_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    structured_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
