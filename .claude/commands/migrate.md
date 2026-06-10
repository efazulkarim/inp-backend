---
description: Create a safe, reversible Alembic migration. Accepts a short slug describing the change.
argument-hint: "<short slug, e.g. 'add_idea_priority'>"
---

You are the migration assistant for `inp-backend`. Follow this flow:

1. Parse the slug from the argument. Refuse to proceed if it's empty or contains spaces.
2. Read `.claude/skills/alembic-migrations/SKILL.md` (or recall its rules).
3. Find the current head: `alembic heads`.
4. Run `alembic revision --autogenerate -m "<slug>"`. **Do not** trust autogenerate output blindly — read the generated file.
5. Edit `alembic/versions/<rev>_<slug>.py` so that:
   - `upgrade()` and `downgrade()` are exact mirrors.
   - New NOT NULL columns have a default or a backfill step.
   - New FKs come with an index in the same revision.
   - Data migrations are in a separate revision.
6. Run `alembic upgrade head` against the local DB. If it fails, fix the migration, not the DB.
7. Run `alembic downgrade -1`, then `alembic upgrade head` again. Both must succeed.
8. Update the matching model in `app/models.py` to keep autogenerate consistent next time.
9. Add a `@pytest.mark.database` test in `tests/integration/` that exercises the new column.
10. Report: revision id, slug, what changed, up/down/up verified.

Hard rules:

- Never edit an applied migration; write a new one.
- Never drop a column on a populated table without a deprecation window.
- Never disable FK checks.
