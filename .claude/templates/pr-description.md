# PR description template — `inp-backend`

## Summary

<one-paragraph description of what this PR does and why>

## Changes

- <bullet per file or per logical change>
- `<path>:<line>` — <what>

## API impact

- New endpoints: <list with paths, methods, status codes>
- Changed endpoints: <list with old → new behavior>
- Removed endpoints: <list, if any>
- Response shape changes: <list, if any>

## Test plan

- [ ] `pytest -q -m unit` passes
- [ ] `pytest -q -m database` passes
- [ ] `ruff check .` clean
- [ ] Manual test: <describe>

## Migrations

- [ ] New migration added: `<rev_id>_<slug>.py`
- [ ] `alembic upgrade head` ✓
- [ ] `alembic downgrade -1` ✓
- [ ] `alembic upgrade head` ✓ (round-trip)
- [ ] Model in `app/models.py` updated

## Risks & rollout

- Backwards-incompatible? yes / no
- Feature flag needed? yes / no
- Rollback plan: <describe>

## Screenshots

(if UI-touching — usually N/A for this backend)
