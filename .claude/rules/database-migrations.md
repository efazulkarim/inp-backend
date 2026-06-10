---
paths:
  - "alembic/versions/**"
  - "app/models.py"
  - "app/database.py"
---

# Database migration rules

These rules apply to Alembic revisions and SQLAlchemy models.

## Reversibility

- Every `upgrade()` has a matching `downgrade()` that restores the prior state.
- If a downgrade is genuinely impossible (e.g., irreversible data transformation), say so in the PR description and get explicit reviewer sign-off.

## No destructive ops on populated tables

- Adding a `NOT NULL` column → provide a `server_default` or split into (a) add nullable, (b) backfill, (c) set NOT NULL.
- Dropping a column → deprecate in code first, then drop in a later revision. Two-step.
- Changing a type → add new column, backfill, switch, drop old.
- Truncate / drop table → never in a migration.

## Indexes

- Every new FK gets a matching `op.create_index` in the same revision.
- Every new column used in `WHERE` or `ORDER BY` gets an index.
- Composite indexes: name `ix_<table>_<col1>_<col2>`. Single-column: `ix_<table>_<col>`.
- Don't add indexes that duplicate an existing FK index.

## Constraints

- Unique constraints get a matching unique index.
- Foreign keys: explicit `ondelete` (`"CASCADE"` for owned children, `"SET NULL"` for optional links).
- Don't use `"RESTRICT"` for owned children; it blocks parent deletion.

## Data migrations

- `op.execute("UPDATE ...")` is a data migration. Put it in a separate revision.
- One revision = one schema change. One revision = one data backfill. Never mix.

## Model sync

- The model in `app/models.py` MUST be updated alongside the migration.
- `from_attributes=True` on every response Pydantic schema so `IdeaOut.model_validate(idea)` works.
- Field names in schema = column names in DB. No renaming.

## History

- Never edit an applied migration. Write a new one.
- Use sequential, descriptive slugs. Don't reuse slugs.

## Don't

- Don't disable FK checks (`PRAGMA foreign_keys=OFF`, `session_replication_role=replica`).
- Don't import models inside the migration file. Refer to tables by string name.
- Don't drop data without a deprecation window.
