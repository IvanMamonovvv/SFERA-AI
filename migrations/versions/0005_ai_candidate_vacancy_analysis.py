"""ai_candidate_vacancy_analysis

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_candidate_vacancy_analysis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("vacancy_profile_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fit_score", sa.Integer(), nullable=True),
        sa.Column("data_completeness", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("criteria_scores", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("contradictions", sa.JSON(), nullable=False),
        sa.Column("interview_questions", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("cost_estimate", sa.Numeric(10, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "candidate_profile_id", "course_id", "version",
            name="uq_candidate_vacancy_analysis_candidate_course_version",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["ai_candidate_profile.id"],
            name="fk_candidate_vacancy_analysis_candidate_profile", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"],
            name="fk_candidate_vacancy_analysis_course", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_profile_id"], ["ai_vacancy_profile.id"],
            name="fk_candidate_vacancy_analysis_vacancy_profile", ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_candidate_vacancy_analysis_candidate_course_current",
        "ai_candidate_vacancy_analysis",
        ["candidate_profile_id", "course_id", "is_current"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_candidate_vacancy_analysis")
