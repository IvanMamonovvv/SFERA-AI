"""fit_scoring_summary_list

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "ai_candidate_vacancy_analysis",
        "summary",
        type_=sa.JSON(),
        existing_type=sa.Text(),
        existing_nullable=False,
        server_default=None,
        postgresql_using="to_jsonb(summary)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "ai_candidate_vacancy_analysis",
        "summary",
        type_=sa.Text(),
        existing_type=sa.JSON(),
        existing_nullable=False,
        postgresql_using="summary #>> '{}'",
    )
