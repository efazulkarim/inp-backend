---
description: Review the working diff (vs main) or a specific path with the repo-reviewer subagent's lens.
argument-hint: [optional path or glob]
---

You are the code reviewer for `inp-backend`. Follow this flow:

1. Determine the review target:
   - Argument provided → `git diff -- <argument>` (or read the file if it's a single path).
   - Empty → `git diff main...HEAD` (falls back to `git diff` if `main` doesn't exist).
2. Delegate the actual review to the **`repo-reviewer` subagent** (see `.claude/agents/repo-reviewer.md`).
3. The subagent reports findings as `file:line: <emoji> <severity>: <problem>. <fix>.` — pass that through.
4. Group findings by severity: BLOCKER → MAJOR → MINOR.
5. For each BLOCKER or MAJOR, propose the exact code change (one snippet, no more than ~20 lines).
6. End with: "Apply the proposed fixes? (y/n)". On `y`, apply only the BLOCKER + MAJOR fixes.
7. Run `pytest -q -m unit --durations=10` and `ruff check <changed files>` after applying.

Project rules you enforce:

- Routers are thin (no DB calls in router bodies).
- Schemas are Pydantic v2, separate request/response types.
- LLM provider chain is OpenRouter > ApiFreeLLM > GLM > Vultr — never reorder.
- `_get_error_response()` keys are a contract — never remove or rename.
- Idempotency-Key on every non-idempotent POST.
- Migrations are reversible, never destructive on populated tables.
- New FKs come with an index in the same revision.
- Don't refactor unrelated code; keep the diff focused.
