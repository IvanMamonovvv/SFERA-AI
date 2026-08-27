"""ai_resume_extract

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-26 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_resume_extract",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_answer_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("hh_resume_id", sa.String(length=64), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("structured_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "(source_answer_id IS NOT NULL) != (hh_resume_id IS NOT NULL)",
            name="ck_resume_extract_exactly_one_source",
        ),
        sa.UniqueConstraint(
            "candidate_profile_id", "hh_resume_id", name="uq_resume_extract_candidate_hh_resume"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["ai_candidate_profile.id"],
            name="fk_resume_extract_candidate_profile", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_answer_id"], ["testchecks_answer.id"],
            name="fk_resume_extract_source_answer", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_resume_extract_candidate_profile_id", "ai_resume_extract", ["candidate_profile_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_resume_extract")
