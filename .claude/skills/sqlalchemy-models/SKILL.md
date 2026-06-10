---
name: sqlalchemy-models
description: SQLAlchemy 2.0 model patterns for inp-backend. Use when defining or modifying app/models.py — declarative style, timestamps, soft delete via is_deleted, relationships, and index hints.
---

# SQLAlchemy 2.0 model patterns — `inp-backend`

## File in scope

- `app/models.py` — all declarative models
- `app/database.py` — `Base = DeclarativeBase()` and `engine`

## Base + mixin

```python
# app/database.py
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class SoftDeleteMixin:
    is_deleted = mapped_column(Boolean, default=False, nullable=False, index=True)
```

## Model template

```python
# app/models.py
from sqlalchemy import String, ForeignKey, Integer, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.database import Base

class Idea(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="ideas", lazy="selectin")
    answers: Mapped[list["Answer"]] = relationship(back_populates="idea", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_ideas_user_active", "user_id", "is_deleted"),
    )
```

## Conventions

- Type-annotated `Mapped[...]` everywhere. No `Column()`.
- `nullable=False` explicit. Default for `is_deleted = False`.
- Timestamps: `created_at` + `updated_at` via mixin.
- Soft delete: `is_deleted` boolean, never `DELETE` rows.
- Foreign keys: explicit `ondelete="CASCADE"` for owned children, `"SET NULL"` for optional links.
- Indexes: every FK gets one. Composite indexes named `ix_<table>_<col1>_<col2>`. Add to `__table_args__`.
- Relationships: `back_populates`, `lazy="selectin"` for read paths.
- `__repr__`: f"{ClassName}(id={self.id})" only. No dumping of long fields.

## Schema→model sync

- `from_attributes=True` on every response Pydantic schema so `IdeaOut.model_validate(idea)` works.
- Field name alignment: `is_deleted` in DB maps to `is_deleted` in schema (no renaming).
- Enum-like fields: prefer `String(32)` with a Pydantic `Literal[...]` over a Postgres enum; easier migrations.

## Don't do

- Don't add `__table_args__` indexes that duplicate an existing FK index.
- Don't use `lazy="joined"` for collections; it N+1s.
- Don't expose `password_hash` or `secret_*` columns via schema.
- Don't add `ondelete="CASCADE"` to a child whose parent is soft-deleted (it'd be reachable).
