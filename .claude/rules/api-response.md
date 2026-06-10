---
paths:
  - "app/routers/**"
  - "app/services/**"
  - "app/api/**"
---

# API response rules

These rules apply to anything in `app/routers/`, `app/services/`, and `app/api/`.

## Content type

- Every API response is `Content-Type: application/json`. Never `text/plain`, never `text/html` from an API.
- No endpoint returns a bare string or dict without going through a Pydantic response model or an explicit JSONResponse.

## URI design

- Plural nouns: `/ideas`, `/users`, `/reports`. Never `/getIdea`.
- No verbs in paths. The verb is the HTTP method.
- Prefer flat: `/ideas?owner=foo` over `/users/foo/ideas`.
- Trailing slashes: pick one. Currently the project has no trailing slash on collection routes; do not introduce one.

## Query parameters

- Use for filtering, pagination, sorting, state. Example: `/ideas?page=1&page_size=20`.
- Page size: clamp to `1 ≤ page_size ≤ 100` via `Query(..., ge=1, le=100)`.
- Offset: `Query(0, ge=0)`.

## HTTP semantics

- GET → `200 OK`
- POST → `201 Created`
- PUT, PATCH → `200 OK`
- DELETE → `204 No Content`
- Async / background work → `202 Accepted` with a job id
- Auth failure → `401 Unauthorized`
- Permission failure → `403 Forbidden`

## Error response shape

Project standard:

```json
{
  "error": "Invalid payload",
  "detail": {
    "email": "This field is required"
  }
}
```

FastAPI's default 422 response uses `detail: [ { loc, msg, type } ]` — preserve that for Pydantic validation errors. For everything else, the structured shape above.

Never return:

```json
{ "ok": false, "message": "..." }
```

…with a 200 status. Errors always carry a non-2xx status.

## Idempotency

Every non-idempotent POST takes an `Idempotency-Key` header. Persist the key on the server side and replay the same response on retry.

## Status code pitfalls

- Don't use 200 for created. Don't use 201 for updated.
- Don't return 204 with a body.
- Don't return 401 when the user is authenticated but lacks permission — that's 403.
