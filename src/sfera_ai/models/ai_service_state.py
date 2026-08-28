from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sfera_ai.db.base import Base, TimestampMixin


class AiServiceState(TimestampMixin, Base):
    """Собственный key-value стор для служебных курсоров (03_TDD.md, «Candidate Identity
    — Merge кандидатов») — сейчас единственный ключ `last_seen_merge_log_id`."""

    __tablename__ = "ai_service_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
