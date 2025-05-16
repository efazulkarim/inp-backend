"""add_reports_table

Revision ID: f72020ca79a2
Revises: 81d1ff63f7ea
Create Date: 2025-05-17 00:44:07.416640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import ProgrammingError


# revision identifiers, used by Alembic.
revision: str = 'f72020ca79a2'
down_revision: Union[str, None] = '81d1ff63f7ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        inspector = Inspector.from_engine(op.get_bind())
        return table_name in inspector.get_table_names()
    except:
        # If there's any error checking, default to assuming it doesn't exist
        return False


def upgrade() -> None:
    # Check if the reports table already exists
    if not table_exists('reports'):
        # Create reports table
        op.create_table(
            'reports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('idea_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(50), nullable=True),
            sa.Column('content', sa.JSON(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['idea_id'], ['ideaboard.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_reports_id'), 'reports', ['id'], unique=False)
    else:
        print("Table 'reports' already exists - skipping creation")


def downgrade() -> None:
    # Check if reports table exists before dropping
    if table_exists('reports'):
        # Drop reports table
        op.drop_index(op.f('ix_reports_id'), table_name='reports')
        op.drop_table('reports')
    else:
        print("Table 'reports' doesn't exist - skipping drop")
