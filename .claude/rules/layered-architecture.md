---
paths:
  - "app/routers/**"
  - "app/services/**"
  - "app/repositories/**"
  - "app/models.py"
  - "app/schemas.py"
  - "app/database.py"
---

# Layered architecture rules

Per `.kiro/specs/non-breaking-architecture-improvements/`, the target architecture is:

```
API layer (routers)        →  app/routers/*_routes.py
Service layer (logic)      →  app/services/*.py
Repository layer (data)    →  app/repositories/*.py
Infrastructure             →  app/database.py, app/auth.py, app/middleware/, external SDKs
```

These rules keep each layer honest.

## Routers (`app/routers/`)

- **Thin**: parse path/query/body, call a service, return a Pydantic model.
- **No DB calls** in the router body. `Depends(get_db)` is fine; `db.query(...)` is not.
- **No external SDK calls** in the router body. Stripe, Polar, LLM — all behind a service.
- **No business logic**: tier checks, rate-limit decisions, validation rules — all live in the service.
- **Auth**: `Depends(get_current_user)` on every mutating route. Pull the user from the JWT, not from the body.
- **Idempotency-Key**: every non-idempotent POST reads the header and forwards it to the service.

## Services (`app/services/`)

- **Static-method classes** (project pattern: `LLMService`, `IdeaBoardService`, ...). No instance state.
- **Own business logic**: validation rules, orchestration, external calls, transaction boundaries.
- **Repository access**: services call repositories, not `db.query(...)` directly. (Legacy code may still have direct queries — refactor gradually.)
- **External SDKs**: one service per external system (`PolarService`, `StripeService`, `LLMService`). No SDK imports in routers or repos.
- **Return DTOs, not ORM**: convert ORM → schema in the service or repo. Routers should never see `db.query()` results.
- **Logging**: `get_logger(__name__)`. Never `print()`.

## Repositories (`app/repositories/`)

- **One repo per aggregate**: `IdeaRepository`, `UserRepository`, ...
- **Data access only**: `get`, `list`, `create`, `update`, `soft_delete`. No business rules.
- **Return ORM objects** (services convert to DTOs) or domain objects (project choice — be consistent within a repo).
- **No HTTP, no auth, no logging beyond debug-level query tracing.**

## Schemas (`app/schemas.py`)

- **Pydantic v2**, separate request/response types: `IdeaCreate`, `IdeaUpdate`, `IdeaOut`.
- `from_attributes=True` on every response schema (so `IdeaOut.model_validate(idea)` works).
- Free-text fields: `max_length=...` for DoS protection.
- Closed enums: `Literal[...]` over `str`.

## Models (`app/models.py`)

- **SQLAlchemy 2.0** `Mapped[...]` style. No `Column(...)`.
- **TimestampMixin + SoftDeleteMixin** on every model. Soft delete via `is_deleted`, never `DELETE`.
- **Indexes**: every FK gets one. Composite indexes in `__table_args__`.
- **Relationships**: `back_populates`, `lazy="selectin"` for reads.

## Anti-patterns to flag

- `db.query(...)` in a router body.
- `stripe.` / `polar_sdk.` / `httpx` import in a router or repo.
- `print()` in production code path.
- A `BusinessRule` middleware that decides routing based on user attributes — that's service logic.
- A service that takes `Request` as a parameter — services don't know about HTTP.
- A model that mutates a Pydantic schema's nested data — that's an N+1 / hidden coupling smell.

## Don't

- Don't import `from app.routers...` in a service.
- Don't import `from app.services...` in a router unless the service exposes a `router`-friendly helper (rare).
- Don't put transaction control (`db.commit()`, `db.rollback()`) in a router. Services own transactions.
- Don't put `try/except` around the entire router body to "make it work" — exceptions should be specific.
