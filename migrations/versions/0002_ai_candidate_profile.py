"""ai_candidate_profile

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-26 12:18:54.944101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ai_candidate_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("hh_negotiation_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("data_completeness", sa.String(length=16), nullable=False, server_default="MINIMAL"),
        sa.Column("sources_snapshot", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_superseded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "application_id IS NOT NULL OR hh_negotiation_id IS NOT NULL",
            name="ck_candidate_profile_has_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["courses_application.id"],
            name="fk_candidate_profile_application", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hh_negotiation_id"], ["headhunter_hhnegotiationrecord.id"],
            name="fk_candidate_profile_hh_negotiation", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_by_id"], ["ai_candidate_profile.id"],
            name="fk_candidate_profile_superseded_by", ondelete="SET NULL",
        ),
    )
    op.create_index("ix_candidate_profile_application_id", "ai_candidate_profile", ["application_id"])
    op.create_index("ix_candidate_profile_hh_negotiation_id", "ai_candidate_profile", ["hh_negotiation_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ai_candidate_profile")
