"""add_progress_tracking_to_ideaboard

Revision ID: 81d1ff63f7ea
Revises: e2e57bd0aefb
Create Date: 2025-05-16 15:35:56.516331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81d1ff63f7ea'
down_revision: Union[str, None] = 'e2e57bd0aefb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to ideaboard table
    op.add_column('ideaboard', sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ideaboard', sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('ideaboard', sa.Column('completed_steps', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove columns if needed to rollback
    op.drop_column('ideaboard', 'completed_steps')
    op.drop_column('ideaboard', 'is_complete')
    op.drop_column('ideaboard', 'current_step')
