# InsightPilot Backend — Claude Project Rules

## What this is

`inp-backend` is the **InsightPilot FastAPI backend** (Python 3.11). It powers an idea-validation SaaS: idea boards, questionnaires, AI-generated section analysis and strategic overviews, PDF reports, customer personas, and Polar/Stripe billing.

## Stack

- **Framework**: FastAPI 0.116, uvicorn
- **ORM**: SQLAlchemy 2.0 + Alembic migrations, PostgreSQL (Neon in prod, local in dev)
- **Validation**: Pydantic v2 (Settings v2)
- **Auth**: JWT (HS256), Google OAuth, refresh tokens
- **Billing**: Polar (primary) + Stripe (legacy routes)
- **LLM providers** (priority order): OpenRouter → ApiFreeLLM → GLM → Vultr
- **Testing**: pytest with markers `unit`, `integration`, `slow`, `database`, `external`
- **Lint/format**: ruff (`line-length = 100`, target py311)

## Architecture (target, non-breaking)

Per `.kiro/specs/non-breaking-architecture-improvements/`:

```
API layer (routers)        →  app/routers/*_routes.py
Service layer (logic)      →  app/services/*.py
Repository layer (data)    →  app/repositories/*.py
Infrastructure             →  app/database.py, app/auth.py, app/middleware/, external SDKs
```

- **Routers are thin**: parse path/query/body, call service, return schema. No DB calls in routers.
- **Services own business logic**: static-method classes (`LLMService`, `IdeaBoardService`, ...).
- **Repositories own data access**: one repo per aggregate, return ORM or domain objects.
- **External SDKs (Stripe, Polar, LLM)** live in `app/services/` behind a service class.

## Conventions

- **Endpoints**: plural nouns, no verbs, flat where possible (`/ideas`, `/ideas/{id}/answers`).
- **Response format**: `Content-Type: application/json` only. Errors use `{ "error": "...", "detail": {...} }`.
- **HTTP semantics**: POST → 201, PUT/PATCH → 200, DELETE → 204, async → 202, auth fail → 401, forbidden → 403.
- **Idempotency**: every non-idempotent POST takes an `Idempotency-Key` header; persist it on the worker side too.
- **Schemas**: Pydantic v2 in `app/schemas.py`; request DTOs and response DTOs are separate types.
- **Models**: SQLAlchemy 2.0 declarative in `app/models.py`; timestamps via `created_at`/`updated_at`; soft-delete via `is_deleted` flag, not row removal.
- **Migrations**: Alembic, never destructive, always reversible, always add indexes for new FKs and new query columns.
- **Tests**: mirror the layer under test (`tests/unit/test_<module>.py`). Mark slow/db/external tests.
- **Env**: typed in `app/core/config.py` `Settings` class. Never read `os.getenv` outside that file. Never log a secret.

## Domain invariants (do not break)

1. **LLM provider chain** in `app/services/llm_service.py` stays **OpenRouter > ApiFreeLLM > GLM > Vultr**. Adding a provider means inserting it into the chain, not replacing it.
2. **`_get_error_response()`** shape in `app/services/llm_service.py` is consumed by routers; do not remove or rename keys (`error`, `insight`, `recommendations`, `score`, `reasoning`, `overview`, `strategic_next_steps`, `key_strengths`, `key_challenges`).
3. **JSON extraction** in LLM responses uses first-`{` to last-`}`; do not change to a strict `response_format: json_object` (some providers don't support it).
4. **API response shapes** are a public contract; never change a field name, type, or nullability without a deprecation path.
5. **`SECRET_KEY`**, `POLAR_*`, `STRIPE_*`, `OPENROUTER_API_KEY`, `GLM_API_KEY`, `VULTR_API_KEY`, `APIFREELL_API_KEY` come from env only. Never commit values.

## Common commands

```bash
# Lint
ruff check .                     # check
ruff check --fix .               # autofix
ruff format .                    # format

# Tests
pytest -q                        # all
pytest -q -m unit                # unit only
pytest -q tests/unit/test_foo.py # one file
pytest -q -k "name_pattern"      # by name

# Migrations
alembic revision --autogenerate -m "msg"
alembic upgrade head
alembic downgrade -1

# Dev server
uvicorn app.main:app --reload --port 8000

# Health
curl http://localhost:8000/api/health
```

## What NOT to do

- Don't write plain-text responses from any API endpoint.
- Don't `git push --force` or `git reset --hard`.
- Don't edit `.env` (local dev file, ignored). Use `.env.example` for new keys.
- Don't refactor unrelated code in a feature PR — keep diffs minimal and focused.
- Don't introduce `any` (TypeScript-style thinking); in Python, prefer explicit types and small Protocols.
- Don't log JWTs, API keys, passwords, or session secrets.
- Don't skip Alembic down-migrations.
- Don't bypass the layered architecture ("I'll just call the DB from the router for now").
- Don't replace the LLM provider chain — extend it.
- Don't run `pip install` against prod; use the pinned `requirements.txt` from the venv.

## What to defer to globals

- **Caveman mode**, env vars, base permissions, plugins → `~/.claude/settings.json` (already wired).
- **General engineering rules** (REST standards, error shape, secrets policy) → `~/.claude/CLAUDE.md`.

This file is the **project-specific** layer. The global layer is the default. Where they conflict, project rules win.
