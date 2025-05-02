"""Add pin column to ideaboard table

Revision ID: dfb7f3127fcb
Revises: dc2f639fdcd0
Create Date: 2025-01-28 10:16:50.315688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfb7f3127fcb'
down_revision: Union[str, None] = 'dc2f639fdcd0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new column to the ideaboard table
    op.add_column('ideaboard', sa.Column('pin', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove the column if the migration is rolled back
    op.drop_column('ideaboard', 'pin')