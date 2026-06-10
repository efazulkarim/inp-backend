---
name: db-schema-change
description: Multi-agent pipeline for safe, reversible Alembic schema changes — design → apply → test → audit.
phases: [Design, Apply, Test, Audit]
---

# db-schema-change workflow

Invoke via `/schema-change <description>`. Use when adding a column, table, FK, index, or constraint; or when refactoring an existing schema.

## Phase 1 — Design (subagent: `alembic-migrator`)

**Goal**: a draft migration that follows the project's hard rules.

- Find current head: `alembic heads`.
- Generate the revision with `alembic revision --autogenerate -m "<slug>"`.
- **Do not trust autogenerate**. Read and edit the file:
  - `upgrade()` and `downgrade()` are exact mirrors.
  - New NOT NULL columns have a `server_default` or a backfill step in a separate revision.
  - New FKs come with an index in the same revision.
  - Data migrations (`op.execute("UPDATE ...")`) are in a separate revision.
  - No `DROP COLUMN` on a populated table.
- Add the matching model change in `app/models.py` to keep autogenerate consistent next time.

**Exit criteria**: migration file present, model updated, draft looks reversible.

## Phase 2 — Apply

**Goal**: prove the migration is reversible locally before commit.

- `alembic upgrade head` — must succeed.
- `alembic downgrade -1` — must succeed.
- `alembic upgrade head` again — must succeed.
- If any step fails, edit the migration (not the DB) and retry.

**Exit criteria**: all three succeed. Local DB matches head.

## Phase 3 — Test (subagent: `pytest-runner`)

**Goal**: confirm the new column/table behaves under the test suite.

- Run `pytest -q -m database --durations=10`.
- Add a new `@pytest.mark.database` test that exercises the change (read/write, default value, FK cascade if applicable).
- Capture failure tail and propose fixes if any.

**Exit criteria**: green, or a clear failure with a fix.

## Phase 4 — Audit (subagent: `security-auditor`)

**Goal**: catch missing constraints, missing indexes, destructive ops, soft-delete violations.

- Read the migration file plus the model change.
- Check for:
  - Missing index on new FK.
  - Missing index on new column used in `WHERE` / `ORDER BY`.
  - NOT NULL on a populated column without a default.
  - `ondelete="CASCADE"` on a child whose parent is soft-deleted (data loss risk).
  - Drop or rename of a column that production code still references.
- Report findings severity-tagged. Apply only BLOCKER + MAJOR with user consent.

**Exit criteria**: clean, or BLOCKER/MAJOR fixed.

## On any phase failure

Stop the pipeline. Report the phase, the failure, and the proposed next step. Do not auto-apply destructive fixes. Do not roll back the local DB without asking.
