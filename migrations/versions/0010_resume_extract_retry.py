"""resume_extract_retry

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-10 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "ai_resume_extract", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "ai_resume_extract", sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_resume_extract_status_retry_after", "ai_resume_extract", ["status", "retry_after"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_resume_extract_status_retry_after", table_name="ai_resume_extract")
    op.drop_column("ai_resume_extract", "retry_after")
    op.drop_column("ai_resume_extract", "attempts")
