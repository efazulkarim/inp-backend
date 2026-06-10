---
name: alembic-migrations
description: Safe, reversible Alembic migrations for inp-backend. Use when adding a column, table, FK, index, or constraint. Covers up/down, non-destructive adds, FK index requirement, and data-migration splits.
---

# Alembic migrations — `inp-backend`

## Config

- `alembic.ini`
- `alembic/env.py` — `target_metadata = Base.metadata`
- `alembic/versions/<revid>_<slug>.py`

## Procedure

```bash
# 1. Find current head
alembic heads

# 2. Generate (autogenerate is a starting point, not final)
alembic revision --autogenerate -m "add_idea_priority"

# 3. Edit alembic/versions/<revid>_add_idea_priority.py — see templates below
# 4. Verify up/down/up locally
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# 5. Add a -m database test that exercises the new column
pytest -q -m database
```

## Templates

### Add nullable column

```python
def upgrade() -> None:
    op.add_column("ideas", sa.Column("priority", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("ideas", "priority")
```

### Add NOT NULL column with default (safe on populated tables)

```python
def upgrade() -> None:
    op.add_column("ideas", sa.Column("status", sa.String(32), nullable=False, server_default="draft"))
    op.alter_column("ideas", "status", server_default=None)  # optional: drop the default after the column is backfilled

def downgrade() -> None:
    op.drop_column("ideas", "status")
```

### Add NOT NULL column without default (use a data migration first)

```python
# Revision A: add nullable, backfill
def upgrade() -> None:
    op.add_column("ideas", sa.Column("score", sa.Integer(), nullable=True))
    op.execute("UPDATE ideas SET score = 0 WHERE score IS NULL")

def downgrade() -> None:
    op.drop_column("ideas", "score")

# Revision B: set NOT NULL once backfilled
def upgrade() -> None:
    op.alter_column("ideas", "score", existing_type=sa.Integer(), nullable=False)

def downgrade() -> None:
    op.alter_column("ideas", "score", existing_type=sa.Integer(), nullable=True)
```

### Add FK + index (one shot)

```python
def upgrade() -> None:
    op.add_column("answers", sa.Column("idea_id", sa.Integer(), nullable=True))
    op.create_index("ix_answers_idea_id", "answers", ["idea_id"])
    op.create_foreign_key(
        "fk_answers_idea_id_ideas",
        "answers", "ideas",
        ["idea_id"], ["id"],
        ondelete="CASCADE",
    )

def downgrade() -> None:
    op.drop_constraint("fk_answers_idea_id_ideas", "answers", type_="foreignkey")
    op.drop_index("ix_answers_idea_id", table_name="answers")
    op.drop_column("answers", "idea_id")
```

### Composite index

```python
def upgrade() -> None:
    op.create_index(
        "ix_ideas_user_active",
        "ideas",
        ["user_id", "is_deleted"],
    )

def downgrade() -> None:
    op.drop_index("ix_ideas_user_active", table_name="ideas")
```

## Hard rules

1. Always reversible. If downgrade is genuinely impossible, document it in the PR.
2. Never `DROP COLUMN` on a column that still has production data; deprecate in code first, drop later.
3. Every new FK gets an index in the same migration.
4. Every new column used in `WHERE`/`ORDER BY` gets an index.
5. Data migrations are separate revisions from schema migrations.
6. Don't edit applied migrations. Write a new one.
7. Test up + down + up locally before committing.
8. Don't import ORM models inside the migration; refer to tables by string name (`"ideas"`).

## Don't do

- Don't use `op.execute("ALTER TABLE ...")` raw for anything `op.alter_column` covers.
- Don't disable FK checks.
- Don't drop a NOT NULL constraint on a column that's referenced by an index expression.
