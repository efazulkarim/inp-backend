---
description: Run ruff check + format check on the repo. Reports issues grouped by file.
argument-hint: [optional path]
---

You are a linter assistant for `inp-backend`. Follow this flow:

1. Determine the target:
   - Argument provided → use as the path/glob.
   - Empty → repo root.
2. Run `ruff check <target>` (no autofix; this is a report).
3. Run `ruff format --check <target>`.
4. Group findings by file. For each finding, show: `file:line:col: <rule>: <message>`.
5. At the end, summarize: total errors, total warnings, fixable count.
6. Offer to autofix: "Run `ruff check --fix <target>` to autofix the safe ones? (y/n)".
7. On `y`, run the autofix, then re-check to show the new state.

Project rules (from `pyproject.toml [tool.ruff]`):

- `line-length = 100`
- `target-version = "py311"`
- Ignored: E402, F401, E722, F541, F841 (per project decision — do not re-enable)
- Excluded: `alembic/versions`, `.venv`, `venv`, `env`
