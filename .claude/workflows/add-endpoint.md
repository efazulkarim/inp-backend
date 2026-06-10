---
name: add-endpoint
description: Multi-agent pipeline to add a new FastAPI endpoint to inp-backend — analyze → plan → build → test → review. Stops on any phase failure.
phases: [Analyze, Plan, Build, Test, Review]
---

# add-endpoint workflow

Invoke via `/add-endpoint <path method>`. This is a deterministic pipeline; do not skip phases.

## Phase 1 — Analyze (subagent: `fastapi-router-builder`)

**Goal**: extract the local style so the new endpoint matches.

- Read 1-2 sibling routers from `app/routers/`.
- Read the related service in `app/services/`.
- Read the relevant schema block in `app/schemas.py`.
- Read the auth dependency in `app/auth.py`.
- Output a short style report: signature shape, error pattern, status codes, test fixture names.

**Exit criteria**: style report present.

## Phase 2 — Plan

**Goal**: produce a concrete endpoint spec, no code yet.

- Path and method.
- Path params and query params.
- Request body schema (or `None`).
- Response model and `status_code`.
- Auth dependency.
- Idempotency-Key requirement (yes for non-idempotent POST, no otherwise).
- Service function signature (no DB in router, remember).
- Test plan: which unit test file, which integration test file, what cases.
- Stop and ask the user if the spec is ambiguous.

**Exit criteria**: spec confirmed by the user.

## Phase 3 — Build (subagent: `fastapi-router-builder`)

**Goal**: write the code.

- Add request/response schemas to `app/schemas.py` (extend, don't fork).
- Add or extend the service method in `app/services/`.
- Add the route to the appropriate `app/routers/*_routes.py`.
- Wire the router into `app/main.py` only if it's a new file.
- Write `tests/unit/test_<resource>.py` for the service.
- Write `tests/integration/test_<resource>.py` for the router.
- Run `ruff check <new_files>` and fix what's safe.

**Exit criteria**: files added, ruff clean, working tree staged or unstaged.

## Phase 4 — Test (subagent: `pytest-runner`)

**Goal**: prove the new code works.

- Run `pytest -q tests/unit/test_<resource>.py -x` first (fast).
- Then `pytest -q tests/integration/test_<resource>.py -x` (DB).
- Capture failure tail and propose fixes.
- Do not modify the new code to make tests pass without telling the user.

**Exit criteria**: green, OR a clear failure with a fix proposal.

## Phase 5 — Review (subagent: `repo-reviewer`)

**Goal**: enforce project conventions on the new code.

- Run the reviewer on the diff (`git diff` against the last commit, or staged).
- Group findings by severity (BLOCKER > MAJOR > MINOR).
- Apply BLOCKER + MAJOR fixes; surface MINOR for the user.
- Re-run lint + tests after applying.

**Exit criteria**: no BLOCKER, no MAJOR, tests green.

## On any phase failure

Stop the pipeline. Report which phase failed and why. Do not roll back changes — let the user decide. Do not auto-proceed.
