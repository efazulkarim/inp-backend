---
description: Run the add-endpoint skill chain: analyze → plan → build → test → review.
argument-hint: "<path method, e.g. 'POST /ideas/{id}/share'>"
---

You are invoking the **add-endpoint** workflow. The workflow file is `.claude/workflows/add-endpoint.md` — read it first, then execute its phases in order, using the subagents it names.

Argument: pass `<path method>` (e.g. `POST /ideas/{id}/share`, `GET /reports/{id}.pdf`).

Execution:

1. **Analyze** — invoke the `fastapi-router-builder` subagent. It reads sibling routers, schemas, and the related service to extract the local style.
2. **Plan** — emit an endpoint spec: path, method, request schema, response schema, status codes, auth dependency, service function signature, and test plan.
3. **Build** — the `fastapi-router-builder` writes the router, service, schemas, and tests. Run `ruff check` on the new files.
4. **Test** — invoke the `pytest-runner` subagent with the new test path.
5. **Review** — invoke the `repo-reviewer` subagent on the diff.

If any phase fails, stop and report. Do not proceed to the next phase on failure.

Project rules enforced (from `.claude/CLAUDE.md` and `.claude/rules/`):

- POST → 201, DELETE → 204, PATCH/PUT → 200.
- `response_model=` on every endpoint.
- `Depends(get_current_user)` on every mutating route.
- `Idempotency-Key` on every non-idempotent POST.
- No DB calls in router bodies.
- Schemas in `app/schemas.py`, not in the router file.
- Service-layer test in `tests/unit/`, integration test in `tests/integration/`.
