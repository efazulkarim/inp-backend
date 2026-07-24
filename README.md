# InsightPilot Backend

InsightPilot Backend is the FastAPI service for the InsightPilot idea validation platform. It provides authentication, idea board management, questionnaire and answer capture, customer persona workflows, report generation, metric modules, subscriptions, health checks, and operational metrics.

## Table of contents

- [What this service does](#what-this-service-does)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Database setup and migrations](#database-setup-and-migrations)
- [Running the API](#running-the-api)
- [API surface](#api-surface)
- [Development workflow](#development-workflow)
- [Testing and checks](#testing-and-checks)
- [Utility scripts](#utility-scripts)
- [Deployment notes](#deployment-notes)
- [Troubleshooting](#troubleshooting)

## What this service does

- Exposes the InsightPilot REST API using FastAPI.
- Stores users, ideas, questionnaires, answers, reports, customer personas, metric modules, and subscription metadata in a SQL database.
- Uses Alembic for schema migrations.
- Supports JWT and Google OAuth authentication.
- Integrates with LLM providers for idea validation insights and reports.
- Integrates with Polar for subscription checkout and webhook handling, with legacy Stripe routes still present in the codebase.
- Includes health, metrics, structured logging, request correlation IDs, rate limiting, request sanitization, and security headers.

## Tech stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy + Alembic
- Pydantic settings
- PostgreSQL in CI/production-style environments; local development can use any `DATABASE_URL` supported by SQLAlchemy and the installed drivers
- Polar SDK, Authlib, python-jose, ReportLab, HTTPX
- Ruff and pytest for code quality checks

## Repository layout

```text
.
├── app/                         # FastAPI application package
│   ├── api/                     # Health and monitoring endpoints
│   ├── core/                    # Configuration, logging, exceptions, metrics
│   ├── middleware/              # Security and request middleware
│   ├── repositories/            # Data access layer
│   ├── routers/                 # API route modules
│   ├── services/                # Business logic and integrations
│   ├── auth.py                  # JWT/password auth helpers
│   ├── database.py              # SQLAlchemy engine/session setup
│   ├── main.py                  # FastAPI app factory/module and router wiring
│   ├── models.py                # SQLAlchemy models
│   └── schemas.py               # Pydantic request/response schemas
├── alembic/                     # Alembic migration environment and revisions
├── docs/                        # Product/API/deployment documentation
│   └── deployment/              # Hosting and database setup notes
├── scripts/
│   ├── checks/                  # Manual smoke/integration check scripts
│   └── database/                # Database creation, migration, and seeding helpers
├── tests/                       # Pytest suite
├── .env.example                 # Environment variable template
├── requirements.txt             # Runtime and development Python dependencies
├── pyproject.toml               # Project metadata and Ruff configuration
├── pytest.ini                   # Pytest configuration
├── Procfile                     # Process definition for platform deployments
└── vercel.json                  # Vercel deployment configuration
```

## Prerequisites

- Python 3.11 or newer.
- A database URL. PostgreSQL is recommended for shared and production environments.
- Optional service credentials depending on the features you run:
  - Google OAuth client credentials.
  - Polar access token, product IDs, and webhook secret.
  - An LLM provider key (`GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `APIFREELL_API_KEY`, `GLM_API_KEY`, or `VULTR_API_KEY`).

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create local configuration
cp .env.example .env
# Edit .env and set DATABASE_URL and SECRET_KEY at minimum.

# 4. Apply database migrations
alembic upgrade head

# 5. Run the API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open the interactive API documentation at:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Root status: <http://localhost:8000/>
- Health checks: <http://localhost:8000/health/health>

## Configuration

Configuration is loaded from environment variables, with `.env` support for local development. Start from `.env.example` and never commit real secrets.

### Required variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection string. |
| `SECRET_KEY` | Secret used for JWT signing and auth flows. |

### Common application variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | One of `development`, `staging`, `production`, or `testing`. |
| `DEBUG` | `false` | Enables extra debug behavior and SQL echoing when true. |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend base URL used for redirects and checkout return URLs. |
| `ALLOWED_ORIGINS` | See `app/core/config.py` | Comma-separated CORS allowlist. |
| `SESSION_SECRET_KEY` | Generated at runtime if absent | Session secret for OAuth middleware. Set explicitly outside development. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `90` | JWT access token lifetime. |
| `ALGORITHM` / `JWT_ALGORITHM` | `HS256` | JWT algorithm settings used by the config and auth helper modules. |

### Database pool variables

| Variable | Default |
| --- | --- |
| `DB_POOL_SIZE` | `5` |
| `DB_MAX_OVERFLOW` | `10` |
| `DB_POOL_TIMEOUT` | `30` |
| `DB_POOL_RECYCLE` | `3600` |

### Observability and security variables

| Variable | Default |
| --- | --- |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `json` |
| `ENABLE_SECURITY_HEADERS` | `true` |
| `ENABLE_RATE_LIMITING` | `true` |
| `ENABLE_METRICS` | `true` |
| `METRICS_PORT` | `8001` |

### Integration variables

| Area | Variables |
| --- | --- |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| Polar | `POLAR_ACCESS_TOKEN`, `POLAR_WEBHOOK_SECRET`, `POLAR_SUCCESS_URL`, `POLAR_SANDBOX`, `POLAR_SOLOPRENEUR_PRODUCT_ID`, `POLAR_ENTREPRENEUR_PRODUCT_ID` |
| Stripe legacy routes | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY` |
| LLM providers | `GEMINI_API_KEY`, `GEMINI_CHAT_MODEL`, `OPENROUTER_API_KEY`, `OPENROUTER_CHAT_MODEL`, `APIFREELL_API_KEY`, `APIFREELL_CHAT_MODEL`, `GLM_API_KEY`, `GLM_CHAT_MODEL`, `VULTR_API_KEY` |

## Database setup and migrations

### Existing database

```bash
alembic upgrade head
```

### Fresh database

For most environments, prefer migrations:

```bash
alembic upgrade head
```

The repo also includes a model-based helper for bootstrap/CI scenarios:

```bash
python scripts/database/create_tables.py
alembic stamp head
```

Use `stamp head` only when the schema has already been created from models and you intentionally want Alembic to mark all migrations as applied.

### Seed data

Seed scripts live under `scripts/database/`:

```bash
python scripts/database/seed_questionnaire.py
python scripts/database/seed_customerboard_questionnaire.py
python scripts/database/seed_metric_modules.py
```

Run seed scripts only against the intended database and after reviewing the data they insert/update.

## Running the API

Development server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Production-style local server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The `Procfile` uses the same ASGI entrypoint for platform deployments.

## API surface

Routers are mounted from `app/main.py` with these prefixes:

| Prefix | Purpose |
| --- | --- |
| `/` | Root status payload. |
| `/health` | Health, readiness-style diagnostics, and monitoring endpoints. |
| `/metrics` | Application metrics summary. |
| `/auth` | Registration, login, OAuth, and auth utilities. |
| `/user` | User profile and user-related operations. |
| `/api/answer` | Questionnaire answer operations. |
| `/api/ideaboard` | Idea board operations and metric module routes. |
| `/api/trash` | Trash/restore workflows. |
| `/archive` | Archive workflows. |
| `/api/report` | Report generation and retrieval. |
| `/api/customerboard` | Customer persona/customer board workflows. |
| `/api/polar` | Polar plans, checkout, webhooks, and subscription status. |

Legacy Stripe routes are still importable in the repository but are not mounted by the current application entrypoint.

See the focused docs in `docs/` for frontend integration details:

- `docs/REPORT_API.md`
- `docs/POLAR_API.md`
- `docs/POLAR_FRONTEND_GUIDE.md`
- `docs/METRIC_MODULES_FRONTEND_INTEGRATION.md`
- `docs/LLM_FRONTEND_WORKFLOW.md`

## Development workflow

1. Create a branch for your change.
2. Keep application code in `app/`, tests in `tests/`, docs in `docs/`, and one-off operational scripts in `scripts/`.
3. Update `.env.example` when adding a new required or commonly used environment variable.
4. Add an Alembic revision for schema changes.
5. Run linting and targeted tests before opening a PR.

## Testing and checks

Install dependencies first:

```bash
pip install -r requirements.txt
```

Recommended checks:

```bash
ruff check .
pytest
python -c "from app.main import app; print('App loaded OK')"
alembic check
```

Manual smoke checks are available in `scripts/checks/`:

```bash
python scripts/checks/check_db_connection.py
python scripts/checks/check_infrastructure.py
python scripts/checks/check_llm.py
python scripts/checks/check_polar_products.py
```

Some manual checks require external credentials or a live database. They are not a replacement for the pytest suite.

## Utility scripts

| Script | Purpose |
| --- | --- |
| `scripts/database/create_tables.py` | Create tables directly from SQLAlchemy models. Useful for controlled bootstrap/CI flows. |
| `scripts/database/setup_fresh_database.py` | Create model tables and inspect setup for a fresh DB workflow. |
| `scripts/database/seed_questionnaire.py` | Seed core questionnaire data. |
| `scripts/database/seed_customerboard_questionnaire.py` | Seed customer persona questionnaire data. |
| `scripts/database/seed_metric_modules.py` | Seed optional metric module definitions. |
| `scripts/checks/check_db_connection.py` | Verify database connectivity from the current environment. |
| `scripts/checks/check_infrastructure.py` | Exercise configuration, logging, repositories, and services. |
| `scripts/checks/check_import.py` | Verify all application imports resolve correctly. |
| `scripts/checks/check_llm.py` | Exercise configured LLM provider calls. Requires provider credentials. |
| `scripts/checks/check_polar_products.py` | Inspect configured Polar product data. Requires Polar credentials. |

## Deployment notes

Deployment-specific notes are under `docs/deployment/`:

- `docs/deployment/NEON_SETUP.md` for Neon/PostgreSQL setup.
- `docs/deployment/VERCEL.md` for Vercel deployment notes.

General production checklist:

- Set `ENVIRONMENT=production`.
- Set strong `SECRET_KEY` and `SESSION_SECRET_KEY` values.
- Use explicit `ALLOWED_ORIGINS`; do not rely on development wildcard behavior.
- Run `alembic upgrade head` during release.
- Configure provider webhooks using the public API URL.
- Confirm `/health/health` returns a healthy status after deploy.

## Troubleshooting

### The app fails on startup with missing settings

Confirm `.env` exists or the environment contains at least `DATABASE_URL` and `SECRET_KEY`.

### Database connection errors

Run:

```bash
python scripts/checks/check_db_connection.py
```

Then verify credentials, network access, SSL parameters, and that the database accepts connections from your environment.

### Alembic says the database is not up to date

Run:

```bash
alembic upgrade head
alembic check
```

If you created tables directly from models for a brand-new database, use `alembic stamp head` only after confirming the schema matches the current models.

### CORS problems in development

Check `FRONTEND_URL` and `ALLOWED_ORIGINS`. In non-production environments, the app also appends a wildcard origin for development convenience.

### LLM report generation returns fallback responses

Set at least one supported provider key. Provider priority is Gemini, OpenRouter, ApiFreeLLM, GLM, then Vultr.
