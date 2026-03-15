"""add metric modules tables and questionnaire module_slug

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "metric_modules" not in tables:
        op.create_table(
            "metric_modules",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("max_score", sa.Integer(), server_default="9"),
            sa.Column("is_default", sa.Boolean(), server_default="0"),
            sa.Column("sort_order", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_metric_modules_slug", "metric_modules", ["slug"], unique=True)

    if "idea_module_selections" not in tables:
        op.create_table(
            "idea_module_selections",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("idea_id", sa.Integer(), sa.ForeignKey("ideaboard.id"), nullable=False),
            sa.Column("module_id", sa.Integer(), sa.ForeignKey("metric_modules.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "questionnaire" in tables:
        columns = [col["name"] for col in inspector.get_columns("questionnaire")]
        if "module_slug" not in columns:
            op.add_column(
                "questionnaire",
                sa.Column("module_slug", sa.String(length=100), nullable=True),
            )
            op.create_index("ix_questionnaire_module_slug", "questionnaire", ["module_slug"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "questionnaire" in tables:
        columns = [col["name"] for col in inspector.get_columns("questionnaire")]
        if "module_slug" in columns:
            op.drop_index("ix_questionnaire_module_slug", table_name="questionnaire")
            op.drop_column("questionnaire", "module_slug")

    if "idea_module_selections" in tables:
        op.drop_table("idea_module_selections")

    if "metric_modules" in tables:
        op.drop_index("ix_metric_modules_slug", table_name="metric_modules")
        op.drop_table("metric_modules")
