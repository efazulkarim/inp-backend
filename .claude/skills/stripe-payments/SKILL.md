---
name: stripe-payments
description: Stripe (legacy) patterns for inp-backend. Use when modifying app/routers/stripe_routes.py. Covers checkout, webhook signature, and idempotency keys. Note: Polar is the primary billing path; Stripe routes exist for back-compat.
---

# Stripe (legacy) — `inp-backend`

## Status

**Frozen.** New features go through Polar (`app/routers/polar_routes.py`). Stripe routes stay for users who haven't migrated; bug fixes only.

## Files in scope

- `app/routers/stripe_routes.py` — checkout, webhook
- `app/services/subscription_service.py` — shared with Polar; do not branch on provider for entitlement logic
- `app/core/config.py` — `stripe_secret_key`, `stripe_webhook_secret`, `stripe_publishable_key`

## Env keys

```
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PUBLISHABLE_KEY=
```

## Use

```python
import stripe
from app.core.config import get_settings

settings = get_settings()
stripe.api_key = settings.stripe_secret_key
```

## Checkout

```python
@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    payload: CheckoutCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": payload.price_id, "quantity": 1}],
        success_url=...,
        cancel_url=...,
        customer_email=user.email,
        metadata={"user_id": str(user.id)},
        idempotency_key=idempotency_key,  # pass through
    )
    return CheckoutOut(url=session.url, id=session.id)
```

## Webhook

```python
@router.post("/webhook")
async def stripe_webhook(request: Request):
    settings = get_settings()
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(body, sig, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=401, detail="Bad signature")
    # dispatch on event["type"]
    await handle_stripe_event(event)
    return {"ok": True}
```

## Idempotency

Pass the `Idempotency-Key` header from the client straight to Stripe. Persist the key + session id so retries replay the same response.

## Hard rules

- Webhook always verifies signature. Always.
- `stripe_secret_key` and `stripe_webhook_secret` come from env, never logged.
- Use `user_id` from JWT, not from the request body.
- Webhook returns 200 quickly; heavy work in background.

## Don't do

- Don't add new endpoints. If you need new billing behavior, route through Polar.
- Don't `stripe.api_key = ...` at module top level outside a function; keep it lazy.
- Don't mix Stripe and Polar entitlement logic; both feed the same `subscription_service` tier field.
