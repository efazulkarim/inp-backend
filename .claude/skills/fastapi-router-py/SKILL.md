---
name: fastapi-router-py
description: FastAPI router patterns for inp-backend. Use when adding a new endpoint, new *_routes.py, or wiring a new resource into app/main.py. Covers function-based routers, schema-first validation, layered architecture, and idempotency keys.
---

# FastAPI router patterns — `inp-backend`

## Files in scope

- `app/routers/<resource>_routes.py` — the router
- `app/schemas.py` — request/response DTOs (extend, don't fork)
- `app/services/<resource>_service.py` — business logic (static-method class)
- `app/main.py` — register the router

## Template router

```python
# app/routers/<resource>_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, <Resource>
from app.schemas import <Resource>Create, <Resource>Out, <Resource>Update
from app.services.<resource>_service import <Resource>Service
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/<resources>", tags=["<resources>"])


@router.get("", response_model=list[<Resource>Out])
def list_resources(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return <Resource>Service.list(db, skip=skip, limit=limit)


@router.post("", response_model=<Resource>Out, status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: <Resource>Create,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return <Resource>Service.create(db, payload, user_id=user.id, idempotency_key=idempotency_key)


@router.get("/{resource_id}", response_model=<Resource>Out)
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    obj = <Resource>Service.get(db, resource_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Resource not found")
    return obj


@router.patch("/{resource_id}", response_model=<Resource>Out)
def update_resource(
    resource_id: int,
    payload: <Resource>Update,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return <Resource>Service.update(db, resource_id, payload)


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    <Resource>Service.soft_delete(db, resource_id)
    return None
```

## Registration in `app/main.py`

```python
from app.routers import <resource>_routes
# ... with the other includes:
app.include_router(<resource>_routes.router)
```

## Conventions

- Plural noun paths, no verbs, no trailing slash mismatch.
- `response_model=` on every endpoint. `status_code=` explicit.
- POST → 201, DELETE → 204.
- Auth via `Depends(get_current_user)`. Don't read user from body.
- DB via `Depends(get_db)`. No `Session()` calls in router.
- `Idempotency-Key` header on every non-idempotent POST.
- Errors: raise `HTTPException` or project `AppException`. Never return `200` with an error body.

## Schemas

In `app/schemas.py`:

```python
class <Resource>Base(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    # ... free-text inputs MUST have max_length

class <Resource>Create(<Resource>Base):
    pass

class <Resource>Update(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    # partial fields, all optional

class <Resource>Out(<Resource>Base):
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    model_config = ConfigDict(from_attributes=True)
```

## Service layer (no DB calls in router)

```python
# app/services/<resource>_service.py
class <Resource>Service:
    @staticmethod
    def list(db: Session, *, skip: int = 0, limit: int = 20) -> list[<Resource>]:
        return db.query(<Resource>).filter(<Resource>.is_deleted == False).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, payload: <Resource>Create, *, user_id: int, idempotency_key: str | None) -> <Resource>:
        # check idempotency, then create
        ...
```

## Test

`tests/unit/test_<resource>.py` covers the schema and service. `tests/integration/test_<resource>.py` covers the router via `TestClient`.
