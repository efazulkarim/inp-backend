---
name: pytest-fastapi
description: Pytest patterns for inp-backend. Use when writing or running tests. Covers conftest fixtures, FastAPI TestClient vs httpx AsyncClient, mocking LLM providers with respx, and the marker system.
---

# Pytest + FastAPI — `inp-backend`

## Layout

```
tests/
  conftest.py            # shared fixtures
  unit/                  # fast, no DB, no network
  integration/           # DB-backed, marked `database`
  external/              # real LLM/Stripe/Polar, marked `external`
```

## Markers (`pytest.ini`)

`unit`, `integration`, `slow`, `database`, `external`

## conftest.py

```python
# tests/conftest.py
import os
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/inp_test")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user_token():
    from app.auth import create_access_token
    return create_access_token(user_id=1, email="test@example.com")


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}
```

## Router test (unit)

```python
# tests/unit/test_ideas.py
def test_list_ideas_empty(client, auth_headers):
    r = client.get("/ideas", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []
```

## Service test (unit, no router)

```python
# tests/unit/test_idea_service.py
def test_create_idea(db_session):
    from app.services.ideaboard_service import IdeaBoardService
    idea = IdeaBoardService.create(db_session, payload=..., user_id=1)
    assert idea.id is not None
    assert idea.is_deleted is False
```

## LLM mock (respx)

```python
# tests/unit/test_llm_service.py
import respx
from httpx import Response

@respx.mock
async def test_generate_section_uses_openrouter():
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=Response(200, json={
            "choices": [{"message": {"content": '{"score": 8, "insight": "x", "recommendations": [], "reasoning": "y"}'}}],
            "usage": {"total_tokens": 42},
        })
    )
    from app.services.llm_service import LLMService
    out = await LLMService.generate_section_analysis(
        section_name="Problem",
        answers=[{"value": "x"}],
        question_texts=["Q?"],
    )
    assert out["score"] == 8
    assert out["token_usage"] == 42
```

## Marking

```python
import pytest

@pytest.mark.unit
def test_foo():
    ...

@pytest.mark.database
def test_uses_db(db_session):
    ...

@pytest.mark.external
def test_hits_real_polar():
    ...
```

## Run commands

```bash
pytest -q                                # all
pytest -q -m unit                        # unit only
pytest -q tests/unit/test_foo.py         # one file
pytest -q -k "name_pattern"              # by name
pytest -q -m database --durations=10     # integration
pytest -q -m external                    # only when asked
```

## Don't do

- Don't put network calls in `unit` tests.
- Don't skip the `_create_schema` fixture when adding new tables; it will 500 silently.
- Don't `TestClient(app)` outside a fixture; it patches state globally.
- Don't mock `app.core.config.get_settings` per-test; build the env at conftest.
- Don't add a test that needs `database` and `external` markers together.
