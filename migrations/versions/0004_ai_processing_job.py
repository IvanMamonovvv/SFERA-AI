"""ai_processing_job

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_processing_job",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["ai_candidate_profile.id"],
            name="fk_processing_job_candidate_profile", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"],
            name="fk_processing_job_course", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_processing_job_status_retry_after", "ai_processing_job", ["status", "retry_after"])
    op.create_index("ix_processing_job_candidate_profile_id", "ai_processing_job", ["candidate_profile_id"])
    # Partial UniqueConstraint: защита от двух джоб на одно и то же
    # (candidate_profile, course, reason) пока предыдущая ещё не завершена (03_TDD.md, «AIProcessingJob»).
    op.create_index(
        "uq_processing_job_candidate_course_reason_open",
        "ai_processing_job",
        ["candidate_profile_id", "course_id", "reason"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'PROCESSING')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_processing_job")
