---
description: Run pytest with smart targeting. Accepts a path, marker, or `-k` pattern. Defaults to the unit suite.
argument-hint: [path|marker|-k pattern]
---

You are a test runner for `inp-backend`. Follow this flow:

1. Parse the argument:
   - `--db` / `database` / `integration` → `pytest -q -m database --durations=10`
   - `--external` → `pytest -q -m external`
   - `--slow` → `pytest -q -m slow`
   - Path ending in `.py` → `pytest -q <path> -x`
   - Starts with `-k` → `pytest -q -k <rest>`
   - Empty → `pytest -q -m unit --durations=10`
2. Run the command. Capture the tail (last 40 lines) on failure.
3. If all green: report `✓ <N> passed in <T>s`.
4. If failures: for each, print:
   - file:line where the assertion is
   - the assertion message
   - a one-line fix suggestion
5. Do not modify tests to make them pass. Suggest the fix and ask the user.

Project rule reminders:

- Tests live in `tests/unit/`, `tests/integration/`, `tests/external/`.
- `conftest.py` already provides `client`, `db_session`, `user_token`, `auth_headers`.
- Mock LLM calls with `respx`. Real provider calls are `@pytest.mark.external` only.
- Never run the full unmarked suite by default; it includes slow and external tests.
