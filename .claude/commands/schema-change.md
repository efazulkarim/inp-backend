---
description: Run the db-schema-change skill chain: design → apply → test → audit. Use when adding a column, table, FK, or index.
argument-hint: "<short description, e.g. 'add is_archived to ideas'>"
---

You are invoking the **db-schema-change** workflow. The workflow file is `.claude/workflows/db-schema-change.md` — read it first, then execute its phases in order.

Argument: a short description of the schema change. If empty, ask before proceeding.

Execution:

1. **Design** — invoke the `alembic-migrator` subagent. It drafts the migration with reversible `upgrade()` and `downgrade()`, splits data migrations from schema migrations, and adds indexes for new FKs.
2. **Apply** — run `alembic upgrade head` against the local DB, then `alembic downgrade -1`, then `alembic upgrade head`. All three must succeed.
3. **Test** — invoke the `pytest-runner` subagent with `-m database`.
4. **Audit** — invoke the `security-auditor` subagent on the migration. It checks for missing constraints, missing indexes, and destructive ops.

If any phase fails, stop and report.

Project rules enforced:

- Never destructive on populated tables. Deprecate in code first, drop later.
- New NOT NULL columns need a default or a backfill step.
- Every new FK gets an index in the same revision.
- Data migrations are separate revisions from schema migrations.
- Never edit an applied migration; write a new one.
- Update the matching SQLAlchemy model in `app/models.py` to keep autogenerate consistent.
