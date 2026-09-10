"""vacancy_profile_portrait_text

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, Sequence[str], None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "ai_vacancy_profile", sa.Column("portrait_text", sa.Text(), nullable=False, server_default="")
    )
    op.add_column(
        "ai_vacancy_profile", sa.Column("source_url", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("ai_vacancy_profile", "source_url")
    op.drop_column("ai_vacancy_profile", "portrait_text")
