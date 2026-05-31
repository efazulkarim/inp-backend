"""add_performance_indexes

Revision ID: be8f733f36e5
Revises: 52976eaf8e81
Create Date: 2025-09-02 20:08:06.495038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be8f733f36e5'
down_revision: Union[str, None] = '52976eaf8e81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
