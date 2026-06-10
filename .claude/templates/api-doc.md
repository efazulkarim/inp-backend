# API doc template — `inp-backend`

## `<METHOD> <path>`

### Summary

<one-line summary of what the endpoint does>

### Auth

`<none>` / `<user>` / `<admin>` (i.e. `Depends(get_current_user)`) / `<service>` (API key, etc.)

### Headers

| Header | Required | Notes |
|---|---|---|
| `Authorization` | yes (mutating routes) | `Bearer <jwt>` |
| `Idempotency-Key` | yes (non-idempotent POST) | UUID v4 recommended |
| `Content-Type` | yes (with body) | `application/json` |

### Path / query params

| Name | Type | Required | Notes |
|---|---|---|---|
| `<id>` | int | yes | path |

### Request body

```json
{
  "field": "value"
}
```

Schema: `<Resource>Create` in `app/schemas.py`.

### Response — `<status>`

```json
{
  "id": 1,
  "field": "value",
  "created_at": "2026-06-10T12:00:00Z",
  "updated_at": "2026-06-10T12:00:00Z",
  "is_deleted": false
}
```

Schema: `<Resource>Out` in `app/schemas.py`.

### Error responses

| Status | When | Body shape |
|---|---|---|
| 401 | missing/invalid JWT | `{ "detail": "Invalid token" }` |
| 403 | wrong owner / tier | `{ "detail": "Forbidden" }` |
| 404 | resource not found | `{ "detail": "Resource not found" }` |
| 422 | invalid body | `{ "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }` |
| 429 | rate limited | `{ "detail": "Rate limit exceeded" }` |
| 500 | unexpected | `{ "detail": "Internal server error" }` |

### Example

```bash
curl -X POST http://localhost:8000/<path> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"field": "value"}'
```
