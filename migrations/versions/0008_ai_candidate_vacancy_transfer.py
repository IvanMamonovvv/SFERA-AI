"""ai_candidate_vacancy_transfer

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, Sequence[str], None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_candidate_vacancy_transfer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"], ["ai_candidate_profile.id"],
            name="fk_candidate_vacancy_transfer_candidate_profile", ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "candidate_profile_id", "course_id",
            name="uq_candidate_vacancy_transfer_candidate_course",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_candidate_vacancy_transfer")
