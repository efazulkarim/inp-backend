# Polar.sh Payment Integration

This document describes the Polar.sh payment integration for InsightPilot.

## Overview

Polar.sh is integrated alongside Stripe as an alternative payment provider. Users can subscribe via either provider; subscription status is unified in the `User` model.

## Setup

### 1. Install Dependencies

```bash
pip install polar-sdk
```

### 2. Environment Variables

Add to your `.env`:

| Variable | Description |
|----------|-------------|
| `POLAR_ACCESS_TOKEN` | Organization Access Token from [Polar Dashboard](https://polar.sh/dashboard) → Settings → Access Tokens |
| `POLAR_WEBHOOK_SECRET` | Webhook signing secret (from webhook endpoint setup) |
| `POLAR_SUCCESS_URL` | Optional. Redirect URL after successful payment. Default: `{FRONTEND_URL}/dashboard/checkout/success?checkout_id={CHECKOUT_ID}` |
| `POLAR_SANDBOX` | Set to `true` to use Polar sandbox environment |
| `POLAR_SOLOPRENEUR_PRODUCT_ID` | Polar product UUID for Solopreneur plan |
| `POLAR_ENTREPRENEUR_PRODUCT_ID` | Polar product UUID for Entrepreneur plan |

### 3. Create Products in Polar

1. Go to [Polar Dashboard](https://polar.sh/dashboard) → Products → Catalogue
2. Create products for Solopreneur and Entrepreneur (or your plan names)
3. Copy each Product ID (⋮ menu → Copy Product ID)
4. Set `POLAR_SOLOPRENEUR_PRODUCT_ID` and `POLAR_ENTREPRENEUR_PRODUCT_ID` in `.env`

### 4. Configure Webhook

1. Polar Dashboard → Settings → Webhooks → Create endpoint
2. URL: `https://your-api-domain.com/api/polar/webhook`
3. Subscribe to events: `order.paid`, `subscription.active`, `subscription.canceled`, `subscription.revoked`, `subscription.updated`
4. Copy the webhook secret to `POLAR_WEBHOOK_SECRET`

## API Endpoints

### `GET /api/polar/plans`

Returns subscription plans with Polar product IDs (when configured).

**Response:** `SubscriptionPlanResponse` with `polar_product_id` on each plan.

### `POST /api/polar/create-checkout`

Creates a Polar checkout session.

**Query params:**
- `product_id` (required): Polar product UUID

**Auth:** Bearer token required

**Response:**
```json
{
  "session_id": "checkout-uuid",
  "checkout_url": "https://buy.polar.sh/..."
}
```

**Flow:** Redirect the user to `checkout_url`. After payment, Polar redirects to `POLAR_SUCCESS_URL` with `checkout_id` in the query string.

### `POST /api/polar/webhook`

Webhook endpoint for Polar events. **Do not** protect with auth; Polar validates via signature.

### `GET /api/polar/subscription-status`

Returns the current user's subscription status (works for both Stripe and Polar subscriptions).

## Database

New columns on `users`:
- `polar_customer_id`: Polar customer UUID
- `polar_subscription_id`: Polar subscription UUID

Run migration:
```bash
alembic upgrade head
```

## References

- [Polar Python SDK](https://polar.sh/docs/integrate/sdk/python)
- [Create Checkout Session](https://polar.sh/docs/guides/create-checkout-session)
- [Webhook Delivery](https://polar.sh/docs/integrate/webhooks/delivery)
