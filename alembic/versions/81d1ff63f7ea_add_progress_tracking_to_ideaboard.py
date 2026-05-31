"""add_progress_tracking_to_ideaboard

Revision ID: 81d1ff63f7ea
Revises: e2e57bd0aefb
Create Date: 2025-05-16 15:35:56.516331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '81d1ff63f7ea'
down_revision: Union[str, None] = 'e2e57bd0aefb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'ideaboard' not in tables:
        return

    columns = [col['name'] for col in inspector.get_columns('ideaboard')]

    if 'current_step' not in columns:
        op.add_column('ideaboard', sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'))
    if 'is_complete' not in columns:
        op.add_column('ideaboard', sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='0'))
    if 'completed_steps' not in columns:
        op.add_column('ideaboard', sa.Column('completed_steps', sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if 'ideaboard' not in tables:
        return

    columns = [col['name'] for col in inspector.get_columns('ideaboard')]

    if 'completed_steps' in columns:
        op.drop_column('ideaboard', 'completed_steps')
    if 'is_complete' in columns:
        op.drop_column('ideaboard', 'is_complete')
    if 'current_step' in columns:
        op.drop_column('ideaboard', 'current_step')
