"""Update CustomerPersona model to new persona schema fields

Revision ID: 6806c503eb2d
Revises: dbd17723a379
Create Date: 2025-05-25 22:25:18.251798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '6806c503eb2d'
down_revision: Union[str, None] = 'dbd17723a379'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customer_personas', sa.Column('gender_identity', sa.String(length=50), nullable=True))
    op.add_column('customer_personas', sa.Column('education_level', sa.String(length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('location_region', sa.String(length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('role_occupation', sa.String(length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('industry_types', sa.JSON(), nullable=True))
    op.add_column('customer_personas', sa.Column('annual_income', sa.String(length=50), nullable=True))
    op.add_column('customer_personas', sa.Column('work_styles', sa.JSON(), nullable=True))
    op.add_column('customer_personas', sa.Column('tech_proficiency', sa.Integer(), nullable=True))
    op.add_column('customer_personas', sa.Column('info_sources', sa.JSON(), nullable=True))
    op.add_column('customer_personas', sa.Column('emotions', sa.JSON(), nullable=True))
    op.add_column('customer_personas', sa.Column('preferred_features', sa.JSON(), nullable=True))
    op.add_column('customer_personas', sa.Column('preferred_communication_channels', sa.JSON(), nullable=True))
    op.drop_column('customer_personas', 'gender')
    op.drop_column('customer_personas', 'information_sources')
    op.drop_column('customer_personas', 'income_range')
    op.drop_column('customer_personas', 'work_environment')
    op.drop_column('customer_personas', 'role')
    op.drop_column('customer_personas', 'location')
    op.drop_column('customer_personas', 'industry')
    op.drop_column('customer_personas', 'education')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customer_personas', sa.Column('education', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('industry', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('location', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('role', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=100), nullable=True))
    op.add_column('customer_personas', sa.Column('work_environment', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=True))
    op.add_column('customer_personas', sa.Column('income_range', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=True))
    op.add_column('customer_personas', sa.Column('information_sources', mysql.JSON(), nullable=True))
    op.add_column('customer_personas', sa.Column('gender', mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=50), nullable=True))
    op.drop_column('customer_personas', 'preferred_communication_channels')
    op.drop_column('customer_personas', 'preferred_features')
    op.drop_column('customer_personas', 'emotions')
    op.drop_column('customer_personas', 'info_sources')
    op.drop_column('customer_personas', 'tech_proficiency')
    op.drop_column('customer_personas', 'work_styles')
    op.drop_column('customer_personas', 'annual_income')
    op.drop_column('customer_personas', 'industry_types')
    op.drop_column('customer_personas', 'role_occupation')
    op.drop_column('customer_personas', 'location_region')
    op.drop_column('customer_personas', 'education_level')
    op.drop_column('customer_personas', 'gender_identity')
    # ### end Alembic commands ###
