---
name: jwt-auth-fastapi
description: JWT issuance, validation, refresh, password hashing, and Google OAuth for inp-backend. Use when modifying app/auth.py, adding a new auth endpoint, or wiring OAuth.
---

# JWT auth — `inp-backend`

## Files in scope

- `app/auth.py` — token issuance/validation, password hashing, OAuth flow
- `app/routers/auth_routes.py` — login, refresh, logout, password reset, Google callback
- `app/blacklist.py` — JWT denylist (logout, revocation)
- `app/core/config.py` — `secret_key`, `access_token_expire_minutes`, `algorithm`

## Token model

- **Access**: HS256, `exp` = now + 90 min (configurable), claims: `sub` (user id), `email`, `iat`, `exp`, `type="access"`.
- **Refresh**: HS256, `exp` = now + 7 days, claims: `sub`, `iat`, `exp`, `type="refresh"`, `jti` (uuid) for one-time use.

## Issue

```python
from jose import jwt
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.core.config import get_settings

def create_access_token(user_id: int, email: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """Returns (token, jti). jti is stored server-side for one-time rotation."""
    settings = get_settings()
    jti = str(uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.refresh_token_expire_days)).timestamp()),
        "type": "refresh",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, jti
```

## Validate (FastAPI dependency)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.config import get_settings
from app.models import User

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Wrong token type")
    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="User not found")
    return user
```

## Refresh rotation

1. Client POSTs `/auth/refresh` with the refresh token.
2. Decode, check `type == "refresh"`, check `jti` not in denylist.
3. Issue new access + new refresh, add old `jti` to denylist (in `app/blacklist.py`).
4. Return both.

## Password hashing

```python
from passlib.context import CryptContext
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)
```

`requirements.txt` pins `passlib[bcrypt]==1.7.4` and `bcrypt>=4.0,<5.0` — keep both.

## Google OAuth

`/auth/google/callback` is in `auth_routes.py`:

1. Exchange `code` for tokens via `Authlib`.
2. Verify `id_token` against `GOOGLE_CLIENT_ID`.
3. Find or create user; on creation, mark `email_verified=True`, hash a random password (no password login).
4. Issue access + refresh, redirect to `FRONTEND_URL` with tokens in URL fragment (or set httpOnly cookies — pick one and stick with it).

## Hard rules

- `secret_key` is read only via `get_settings()`. Never hardcode.
- Algorithm is pinned; do not accept `none`.
- `Authorization: Bearer` only. No cookies for API auth (cookies for OAuth callback is fine).
- Never log the token or the password (plain or hashed is fine to log; salt + work factor means no).
- Refresh tokens are one-time; old `jti` denylisted on rotation.
- `get_current_user` returns 401, not 403, on missing/invalid token.
- `is_deleted` users cannot authenticate.

## Don't do

- Don't store JWTs in localStorage from the backend's recommendation; that's a frontend concern, but if you advise, prefer httpOnly cookies.
- Don't add `jti` to a denylist that's not actually consulted on every decode.
- Don't issue a refresh token longer than 30 days.
