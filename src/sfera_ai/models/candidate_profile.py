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
