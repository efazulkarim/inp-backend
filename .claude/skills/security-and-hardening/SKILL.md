---
name: security-and-hardening
description: Security middleware order, headers, rate limits, request sanitization, and input validation for inp-backend. Use when modifying app/middleware/security.py or hardening a route.
---

# Security & hardening — `inp-backend`

## Middleware (in `app/main.py`, innermost to outermost)

```python
app.add_middleware(RateLimitingMiddleware, ...)        # outermost
app.add_middleware(RequestSanitizationMiddleware, ...)
app.add_middleware(SecurityHeadersMiddleware, ...)     # innermost — applies to all responses
```

Order matters: `SecurityHeadersMiddleware` must wrap every response, so it's innermost (added first).

## Security headers (set by `SecurityHeadersMiddleware`)

- `Strict-Transport-Security: max-age=63072000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

Don't add `Access-Control-Allow-Origin: *` from this middleware — CORS is handled by `CORSMiddleware` from FastAPI with an explicit `allow_origins` list.

## Rate limiting (`RateLimitingMiddleware`)

- Default: 60 req / 60 s per IP, sliding window.
- Auth routes (`/auth/login`, `/auth/refresh`, `/auth/password-reset`): 10 req / 60 s per IP.
- `/auth/google/*`: 20 req / 60 s per IP.
- Webhooks (`/polar/webhook`, `/stripe/webhook`): exempt — they hit our IP, not the user's, and we can't bucket by user yet.

Configure via `app/core/config.py` `Settings`:
```
ENABLE_RATE_LIMITING=true
RATE_LIMIT_DEFAULT=60
RATE_LIMIT_AUTH=10
```

## Request sanitization (`RequestSanitizationMiddleware`)

- Strips control characters from JSON string bodies (not from auth headers).
- Rejects bodies > 1 MB (configurable via `Settings.max_body_size_bytes`).
- Rejects paths with `..` or null bytes.
- Logs the rejection at WARNING with `request_id` (correlation middleware sets it).

## Input validation (Pydantic)

- Free-text fields MUST have `max_length`:
  - name: 200
  - description: 5000
  - answer text: 10000
- Email: `EmailStr` from `pydantic[email]`.
- IDs from path: typed as `int` (FastAPI returns 422 on non-int).
- Enums: `Literal[...]` over `str` where the set is closed.

## JWT

See `jwt-auth-fastapi` skill. Key points: `secret_key` from env, algorithm pinned to HS256, `get_current_user` on every mutating route.

## Webhooks

Always verify the signature. See `polar-payments` and `stripe-payments` skills.

## CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # list, not "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    max_age=600,
)
```

Production `allowed_origins` is the deployed frontend URL only. Never `*` with `allow_credentials=True`.

## Logging

Use `get_logger(__name__)` from `app/core/logging.py`. Never log:
- Authorization headers
- JWT tokens
- Passwords (plain or hashed is fine for debug; don't log `pwd_ctx.hash(...)` return value)
- API keys
- Webhook signatures
- Full request body on auth routes

## Don't do

- Don't roll your own auth. Use `app/auth.py`.
- Don't disable HTTPS in production (set `Strict-Transport-Security` always).
- Don't add a custom CORS exception — FastAPI handles it.
- Don't apply rate limit to webhooks.
- Don't return stack traces in prod responses (`debug=False`).
