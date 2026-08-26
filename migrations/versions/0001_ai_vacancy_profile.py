"""ai_vacancy_profile

Revision ID: 0001
Revises:
Create Date: 2026-08-26 10:20:20.122856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_vacancy_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "version", name="uq_vacancy_profile_course_version"),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses_course.id"],
            name="fk_vacancy_profile_course", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_vacancy_profile_course_id", "ai_vacancy_profile", ["course_id"])
    # Частичный индекс: быстрый lookup «текущий профиль» + гарантия ровно одного is_current=True на course
    op.create_index(
        "uq_vacancy_profile_course_current",
        "ai_vacancy_profile",
        ["course_id"],
        unique=True,
        postgresql_where=sa.text("is_current IS TRUE"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_vacancy_profile")
