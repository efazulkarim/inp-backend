---
name: test-driven-development
description: TDD workflow adapted to FastAPI + service layer in inp-backend. Use when adding a new endpoint, service method, or business rule. Red → Green → Refactor, with the project's test layout and markers.
---

# TDD — `inp-backend`

## Cycle

1. **Red** — write the smallest failing test for the new behavior.
2. **Green** — write the minimum code to make it pass.
3. **Refactor** — clean up, keep tests green.

## Layout reminder

- Service-layer tests → `tests/unit/test_<service>_service.py`, marked `@pytest.mark.unit`.
- Router tests → `tests/integration/test_<resource>.py` if they touch the DB, otherwise `tests/unit/`.
- DB tests → marked `@pytest.mark.database`.
- LLM-touching tests → `respx` mock, no real calls (unless `@pytest.mark.external`).

## Recipe: add a new endpoint

1. **Red (schema)** — write a test that constructs the request/response Pydantic models. Don't import the model class yet; let the import fail.
2. **Green (schema)** — add the schemas to `app/schemas.py` minimally. Test passes.
3. **Red (service)** — write a test for the service method. Use the `db_session` fixture. Inject behavior (mocks for external calls) via constructor or patch.
4. **Green (service)** — add the static method to the service class. Pass the test. Touch only the service; don't add the route yet.
5. **Red (router)** — write a router test using `TestClient` + `auth_headers`. Assert status code + body shape.
6. **Green (router)** — add the route in `app/routers/<resource>_routes.py`. Pass the test. Wire into `app/main.py` if it's a new file.
7. **Refactor** — extract repeated code; tighten types; check that the layered rule is intact (no DB in router, no `Depends` in service).

## Recipe: add a new LLM provider

1. **Red (config)** — add a test that reads `Settings.<new>_api_key` from env.
2. **Green (config)** — add to `app/core/config.py`. Update `.env.example`.
3. **Red (selection)** — test that with only the new key set, the active provider is the new one.
4. **Green (selection)** — add the provider block + `USE_<NEW>` flag, slot into the chain.
5. **Red (request)** — `respx` mock for the new base URL, hit the route, assert body.
6. **Green (request)** — extend `_make_chat_request` if needed; most providers reuse the OpenAI-compatible path.
7. **Refactor** — ensure error shape stable; check existing providers still pass.

## Recipe: add a new column to a model

1. **Red (model)** — model test: instantiate, assert the column exists and has the right default.
2. **Green (model)** — add the column to `app/models.py`. Make it nullable OR give a `server_default`.
3. **Red (migration)** — write the Alembic migration by hand (autogenerate is a starting point, not the result). Run `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head`.
4. **Green (migration)** — the test for the model is now actually exercised against the migrated schema.
5. **Refactor** — update Pydantic schema, service code, router.

## What "minimum" means here

- Don't add error handling for cases the code can't reach yet.
- Don't add type hints to every local variable; annotate public API only.
- Don't write a docstring for a one-line function.
- Don't pre-optimize.

## When to break the cycle

- A bug in a third-party SDK — write a regression test, then patch the wrapper, not the SDK.
- A perf issue — write a failing perf test if you can (e.g., `pytest-benchmark`), then optimize.
- A security finding — fix the line, write a test that would have caught the regression, then move on. Don't TDD the security model itself; that work is review-driven.

## Don't do

- Don't write the implementation first, "to get the shape right," then write tests. The test tells you the shape.
- Don't skip refactor because "the test passes." Refactor is part of green.
- Don't disable a failing test to merge. Fix or delete it.
