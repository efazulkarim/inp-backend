"""add_polar_fields_to_user

Revision ID: a1b2c3d4e5f6
Revises: 52976eaf8e81
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "52976eaf8e81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("polar_customer_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("polar_subscription_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "polar_subscription_id")
    op.drop_column("users", "polar_customer_id")
