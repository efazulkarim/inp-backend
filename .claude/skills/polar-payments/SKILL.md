---
name: polar-payments
description: Polar SDK patterns for inp-backend. Use when modifying app/routers/polar_routes.py, app/services/subscription_service.py, or webhook handling. Covers checkout creation, webhook signature verification, and sandbox vs live toggle.
---

# Polar payments — `inp-backend`

## Files in scope

- `app/routers/polar_routes.py` — checkout creation, customer portal, webhook
- `app/services/subscription_service.py` — tier mapping, entitlement checks
- `app/services/subscription_config.py` — product IDs, feature flags per tier
- `app/core/config.py` — `polar_access_token`, `polar_webhook_secret`, `polar_sandbox`, product IDs

## Env keys

```
POLAR_ACCESS_TOKEN=                 # required
POLAR_WEBHOOK_SECRET=               # required
POLAR_SANDBOX=true|false
POLAR_SUCCESS_URL=...
POLAR_SOLOPRENEUR_PRODUCT_ID=...
POLAR_ENTREPRENEUR_PRODUCT_ID=...
```

## SDK use

```python
from polar_sdk import Polar

def get_polar_client() -> Polar:
    settings = get_settings()
    return Polar(
        access_token=settings.polar_access_token,
        server=settings.polar_sandbox and "sandbox" or "production",
    )
```

The SDK is async-first; use it inside `async def` routes.

## Checkout

```python
@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    payload: CheckoutCreate,
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    polar = get_polar_client()
    session = await polar.checkouts.create(
        request=CreateCheckoutRequest(
            product_id=payload.product_id,
            success_url=settings.polar_success_url.format(CHECKOUT_ID="{CHECKOUT_ID}"),
            customer_email=user.email,
            metadata={"user_id": str(user.id)},
        )
    )
    return CheckoutOut(url=session.url, id=session.id)
```

`POLAR_SUCCESS_URL` template uses `{CHECKOUT_ID}` placeholder; pass it through `success_url` as a Polar-side substitution.

## Webhook signature

```python
import hmac
import hashlib
from fastapi import Request, HTTPException

@router.post("/webhook")
async def polar_webhook(request: Request):
    settings = get_settings()
    body = await request.body()
    sig = request.headers.get("webhook-signature", "")
    expected = hmac.new(
        settings.polar_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="Bad signature")
    event = await request.json()
    # dispatch on event["type"]
    await handle_polar_event(event)
    return {"ok": True}
```

## Sandbox vs live

- `POLAR_SANDBOX=true` → SDK points at `https://sandbox-api.polar.sh`, no real cards.
- `POLAR_SANDBOX=false` → production.
- Local dev: `POLAR_SANDBOX=true`. CI: same.
- Production env var is set at deploy time; never commit it.

## Tier mapping (in `subscription_config.py`)

```python
TIER_PRODUCTS = {
    "free": None,
    "solopreneur": settings.polar_solopreneur_product_id,
    "entrepreneur": settings.polar_entrepreneur_product_id,
}

TIER_LIMITS = {
    "free": {"ideas": 3, "personas_per_idea": 2, "llm_calls_per_month": 50},
    "solopreneur": {"ideas": 25, "personas_per_idea": 5, "llm_calls_per_month": 1000},
    "entrepreneur": {"ideas": -1, "personas_per_idea": 10, "llm_calls_per_month": -1},  # -1 = unlimited
}
```

Entitlement checks live in `subscription_service.py`, called from routers/services, not from middleware.

## Idempotency

`POST /checkout` takes an `Idempotency-Key` header. Persist the key + checkout id; replay returns the same checkout.

## Hard rules

- Webhook handler always verifies signature. Always.
- `polar_access_token` and `polar_webhook_secret` come from env, never logged.
- Sandbox mode in any non-prod env.
- Webhook returns 200 quickly; do heavy work in a background task.
- Always use `user_id` from the validated JWT, not from the request body or query.

## Don't do

- Don't trust the `customer_email` in webhook payload alone; reconcile with the user from `metadata.user_id`.
- Don't downgrade a user on `subscription.cancelled` immediately — wait for `subscription.period.ended`.
- Don't use the legacy `STRIPE_*` paths for new features; they're frozen.
