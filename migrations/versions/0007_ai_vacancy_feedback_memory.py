"""ai_vacancy_feedback_memory

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, Sequence[str], None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_vacancy_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=True),
        sa.Column("analysis_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(length=16), nullable=False),
        sa.Column("ai_suggested_rule", sa.Text(), nullable=False, server_default=""),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"],
            name="fk_vacancy_feedback_course", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["ai_candidate_profile.id"],
            name="fk_vacancy_feedback_candidate_profile", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["ai_candidate_vacancy_analysis.id"],
            name="fk_vacancy_feedback_analysis", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users_customuser.id"],
            name="fk_vacancy_feedback_author", ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_vacancy_feedback_course_applied", "ai_vacancy_feedback", ["course_id", "applied"]
    )

    op.create_table(
        "ai_vacancy_memory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("weight_hint", sa.String(length=16), nullable=False),
        sa.Column("source_feedback_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"],
            name="fk_vacancy_memory_course", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_feedback_id"], ["ai_vacancy_feedback.id"],
            name="fk_vacancy_memory_source_feedback", ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_id"], ["users_customuser.id"],
            name="fk_vacancy_memory_approved_by", ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_vacancy_memory_course_is_active", "ai_vacancy_memory", ["course_id", "is_active"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_vacancy_memory")
    op.drop_table("ai_vacancy_feedback")
