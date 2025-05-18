"""add_customer_persona_table

Revision ID: dca1690aa07f
Revises: f72020ca79a2
Create Date: 2025-05-17 03:26:03.727847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'dca1690aa07f'
down_revision: Union[str, None] = 'f72020ca79a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        inspector = inspect(op.get_bind())
        return table_name in inspector.get_table_names()
    except:
        # If there's any error checking, default to assuming it doesn't exist
        return False


def upgrade() -> None:
    # Check if customer_personas table exists before trying to create it
    if not table_exists('customer_personas'):
        # Create the customer_personas table
        op.create_table(
            'customer_personas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('idea_id', sa.Integer(), nullable=True),
            sa.Column('persona_name', sa.String(255), nullable=False),
            sa.Column('tag', sa.String(100), nullable=True),
            
            # Personal information
            sa.Column('age_range', sa.String(50), nullable=True),
            sa.Column('gender', sa.String(50), nullable=True),
            sa.Column('education', sa.String(100), nullable=True),
            sa.Column('location', sa.String(100), nullable=True),
            
            # Professional information
            sa.Column('role', sa.String(100), nullable=True),
            sa.Column('company_size', sa.String(50), nullable=True),
            sa.Column('industry', sa.String(100), nullable=True),
            sa.Column('income_range', sa.String(50), nullable=True),
            sa.Column('work_environment', sa.String(50), nullable=True),
            
            # Goals and challenges
            sa.Column('goals', sa.JSON(), nullable=True),
            sa.Column('challenges', sa.JSON(), nullable=True),
            
            # Behavior
            sa.Column('tools_used', sa.JSON(), nullable=True),
            sa.Column('decision_factors', sa.JSON(), nullable=True),
            sa.Column('information_sources', sa.JSON(), nullable=True),
            sa.Column('user_journey_stage', sa.String(100), nullable=True),
            
            # Emotional triggers
            sa.Column('pain_points', sa.JSON(), nullable=True),
            sa.Column('motivations', sa.JSON(), nullable=True),
            
            sa.Column('created_at', sa.DateTime(), default=sa.func.current_timestamp()),
            sa.Column('updated_at', sa.DateTime(), default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
            
            # Foreign keys
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['idea_id'], ['ideaboard.id'], ),
            
            # Primary key
            sa.PrimaryKeyConstraint('id')
        )
        
        # Add index for faster lookups
        op.create_index(op.f('ix_customer_personas_id'), 'customer_personas', ['id'], unique=False)
        print("Created customer_personas table")
    else:
        print("Table customer_personas already exists - skipping creation")


def downgrade() -> None:
    # Check if the table exists before trying to drop it
    if table_exists('customer_personas'):
        # Drop the customer_personas table
        op.drop_index(op.f('ix_customer_personas_id'), table_name='customer_personas')
        op.drop_table('customer_personas')
        print("Dropped customer_personas table")
    else:
        print("Table customer_personas doesn't exist - skipping drop")
