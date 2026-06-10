---
paths:
  - "app/auth.py"
  - "app/middleware/**"
  - "app/routers/auth_routes.py"
  - "app/routers/polar_routes.py"
  - "app/routers/stripe_routes.py"
  - "app/core/config.py"
---

# Auth & security rules

## Secrets

- All secrets come from env via `app/core/config.py` `Settings`. Never `os.getenv(...)` outside that file.
- `SECRET_KEY` min length 32. Validate at startup with `Field(..., min_length=32)`.
- Never log secrets: no `print(secret)`, no `logger.info("token: %s", token)`, no echo in tracebacks.
- Never return a secret in an HTTP response, even a partial one.
- Never commit `.env`. The `.gitignore` covers it; the `pre-tool-use-secret-guard` hook blocks it.

## JWT

- Algorithm pinned: `HS256` (or `HS384`/`HS512`). Never accept `none`.
- Access token: `exp` = now + 90 min (configurable). Claims: `sub`, `email`, `iat`, `exp`, `type="access"`.
- Refresh token: `exp` = now + 7 days max. Claims: `sub`, `iat`, `exp`, `type="refresh"`, `jti` (uuid).
- Refresh tokens are one-time: add old `jti` to denylist on rotation. The denylist is consulted on every decode.
- `get_current_user` returns 401 (not 403) on missing/invalid token. 403 is for *authenticated but forbidden*.
- Soft-deleted users cannot authenticate: check `is_deleted` and reject.

## OAuth (Google)

- Verify `id_token` against `GOOGLE_CLIENT_ID` (not just decode it).
- `state` and `nonce` must be verified.
- On first login via OAuth, mark `email_verified=True` and hash a random password (no password login path).

## CORS

- `allow_origins` is an explicit list. Never `*` in any non-dev env.
- `allow_credentials=True` is fine, but only with an explicit `allow_origins`.
- Allowed methods: `["GET", "POST", "PATCH", "DELETE"]`. Don't add `PUT` unless you have a route that uses it.
- Allowed headers: `["Authorization", "Content-Type", "Idempotency-Key"]`. Add more only with a reason.

## Rate limits

- Default: 60 req / 60 s per IP, sliding window.
- Auth routes (`/auth/login`, `/auth/refresh`, `/auth/password-reset`): 10 req / 60 s.
- Webhooks (`/polar/webhook`, `/stripe/webhook`): exempt. They hit our IP, not the user's.

## Webhook signature verification

- Every webhook handler verifies the signature. Always.
  - Polar: `webhook-signature` header, `HMAC-SHA256(body, POLAR_WEBHOOK_SECRET)`.
  - Stripe: `stripe-signature` header, `stripe.Webhook.construct_event(body, sig, secret)`.
- Webhook returns 200 quickly; heavy work goes in a background task.

## Logging

- Use `get_logger(__name__)` from `app/core/logging.py`. Never `print()`.
- Never log: Authorization headers, JWT tokens, passwords (plain or hashed), API keys, webhook signatures, full request body on auth routes.
- Structured logging: include `request_id` (CorrelationIDMiddleware sets it) and `user_id` (when authenticated).

## Input validation

- Free-text fields MUST have `max_length`:
  - `name`: 200
  - `description`: 5000
  - answer text: 10000
- Email: `EmailStr`.
- Path IDs: typed as `int` (FastAPI returns 422 on non-int).
- Enums: `Literal[...]` over `str` where the set is closed.

## Debug mode

- `DEBUG=true` only in development. Production sets `DEBUG=false`.
- Never return stack traces in production responses.
