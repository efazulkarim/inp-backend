# Polar Checkout – Frontend Integration Guide

This guide explains how to integrate Polar.sh checkout into the InsightPilot frontend.

---

## Overview

- **Plans**: Fetch from `GET /api/polar/plans` (includes `polar_product_id` per plan).
- **Checkout**: Call `POST /api/polar/create-checkout?product_id=<uuid>` → redirect user to `checkout_url`.
- **Success**: User returns to your success page after payment.
- **Status**: Use `GET /api/polar/subscription-status` for subscription state.

---

## Environment

```env
NEXT_PUBLIC_API_URL=https://your-api.com   # or http://localhost:8000 for dev
```

---

## Types

```typescript
// Plan from GET /api/polar/plans
interface SubscriptionTier {
  plan_key: string;
  id: string | null;           // Polar price/plan ID (null for contact-sales)
  polar_product_id: string | null;  // Polar product UUID – use for Polar checkout
  name: string;
  description: string | null;
  price: number | null;
  display_price: number | null;
  currency: string | null;
  interval: string | null;      // "month" | "year" | "custom"
  contact_sales: boolean;
  features: string[];
}

interface SubscriptionPlanResponse {
  plans: SubscriptionTier[];
}

// Response from POST /api/polar/create-checkout
interface CheckoutCreationResponse {
  session_id: string;
  checkout_url: string;
}

// Response from GET /api/polar/subscription-status
interface SubscriptionStatus {
  status: string;               // "active" | "canceled" | "inactive" | etc.
  plan: string | null;
  current_period_end: string | null;  // ISO datetime
  trial_end: string | null;
  cancel_at_period_end: boolean | null;
}
```

---

## 1. Fetch Plans

```typescript
async function fetchPolarPlans(): Promise<SubscriptionTier[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/polar/plans`);
  if (!res.ok) throw new Error("Failed to fetch plans");
  const data: SubscriptionPlanResponse = await res.json();
  return data.plans;
}
```

Plans with `polar_product_id` are available for Polar checkout. Plans with `contact_sales: true` have no `polar_product_id`.

---

## 2. Create Checkout & Redirect

User must be authenticated. Send the Bearer token in the request.

```typescript
async function createPolarCheckout(
  productId: string,
  accessToken: string
): Promise<string> {
  const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/api/polar/create-checkout`);
  url.searchParams.set("product_id", productId);

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create checkout");
  }

  const data: CheckoutCreationResponse = await res.json();
  return data.checkout_url;
}

// Usage in a button handler
async function handleSubscribe(plan: SubscriptionTier) {
  if (!plan.polar_product_id) {
    // Contact sales
    return;
  }
  const checkoutUrl = await createPolarCheckout(plan.polar_product_id, accessToken);
  window.location.href = checkoutUrl;
}
```

---

## 3. Success Page

After payment, Polar redirects to your success URL (e.g. `/dashboard/checkout/success?checkout_id={CHECKOUT_ID}`).

```tsx
// app/dashboard/checkout/success/page.tsx (Next.js App Router)
"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function CheckoutSuccessPage() {
  const searchParams = useSearchParams();
  const checkoutId = searchParams.get("checkout_id");
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    // Refresh subscription status after redirect
    const token = localStorage.getItem("access_token"); // or your auth store
    if (!token) return;

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/polar/subscription-status`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setStatus)
      .catch(console.error);
  }, []);

  return (
    <div>
      <h1>Payment successful</h1>
      {checkoutId && <p>Checkout ID: {checkoutId}</p>}
      {status?.plan && <p>Your plan: {status.plan}</p>}
    </div>
  );
}
```

---

## 4. Subscription Status

Use the Polar endpoint:

```typescript
async function fetchSubscriptionStatus(accessToken: string): Promise<SubscriptionStatus> {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/polar/subscription-status`,
    { headers: { Authorization: `Bearer ${accessToken}` } }
  );
  if (!res.ok) throw new Error("Failed to fetch subscription");
  return res.json();
}
```

---

## 5. Pricing Page Example

```tsx
"use client";

import { useEffect, useState } from "react";

export default function PricingPage() {
  const [plans, setPlans] = useState<SubscriptionTier[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/polar/plans`)
      .then((r) => r.json())
      .then((data: SubscriptionPlanResponse) => setPlans(data.plans))
      .finally(() => setLoading(false));
  }, []);

  const handleSubscribe = async (plan: SubscriptionTier) => {
    if (plan.contact_sales) {
      window.location.href = "/contact";
      return;
    }
    if (plan.polar_product_id) {
      const token = getAccessToken(); // your auth helper
      const url = await createPolarCheckout(plan.polar_product_id, token);
      window.location.href = url;
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {plans.map((plan) => (
        <div key={plan.plan_key}>
          <h2>{plan.name}</h2>
          <p>{plan.description}</p>
          <p>${plan.display_price}/mo</p>
          <button onClick={() => handleSubscribe(plan)}>
            {plan.contact_sales ? "Contact Sales" : "Subscribe"}
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 6. Error Handling

| Status | Meaning |
|--------|---------|
| 401 | Not authenticated – redirect to login |
| 403 | Forbidden |
| 500 | Server error – show retry message |
| 503 | Polar not configured (`POLAR_ACCESS_TOKEN` missing) |

```typescript
if (res.status === 401) {
  redirect("/login");
}
if (!res.ok) {
  const err = await res.json().catch(() => ({}));
  toast.error(err.detail || "Something went wrong");
}
```

---

## 7. Polar-Only Notes

- The backend is Polar-only: there is no Stripe checkout fallback path.
- `/api/polar/plans` returns live Polar pricing from configured products.
- Use `polar_product_id` for checkout creation.

---

## 8. Checklist

- [ ] `NEXT_PUBLIC_API_URL` set in frontend env
- [ ] Plans fetched from `/api/polar/plans`
- [ ] Subscribe button calls `/api/polar/create-checkout` with `product_id` and Bearer token
- [ ] User redirected to `checkout_url`
- [ ] Success page at `/dashboard/checkout/success` (or path matching `POLAR_SUCCESS_URL`)
- [ ] Subscription status refreshed after success redirect

---

## 9. Production Readiness (Required)

### Backend and Polar configuration

- [ ] `POLAR_ACCESS_TOKEN` is valid (not expired/revoked) for the correct organization
- [ ] `POLAR_SANDBOX=false` in production
- [ ] Production product IDs are configured (`POLAR_SOLOPRENEUR_PRODUCT_ID`, `POLAR_ENTREPRENEUR_PRODUCT_ID`)
- [ ] Webhook endpoint is public HTTPS and set to `/api/polar/webhook`
- [ ] Webhook secret in app env exactly matches Polar endpoint secret
- [ ] Webhook events enabled: `order.paid`, `subscription.active`, `subscription.updated`, `subscription.canceled`, `subscription.revoked`

### Frontend behavior

- [ ] Pricing UI handles `contact_sales` plans (no checkout button)
- [ ] Checkout button is disabled while checkout session is being created
- [ ] User-facing error is shown when checkout creation fails
- [ ] Success page re-fetches subscription status after redirect

### Security and operations

- [ ] Access token is stored only in backend env (never exposed to client)
- [ ] Webhook endpoint is excluded from auth middleware (signature validation only)
- [ ] API logs include enough context to debug failed webhook events
- [ ] At least one end-to-end test purchase completed in sandbox and prod

---

## 10. Smoke Tests Before Launch

### Validate Polar token quickly

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv('app/.env'); from polar_sdk import Polar; p=Polar(access_token=os.getenv('POLAR_ACCESS_TOKEN'), server='sandbox' if os.getenv('POLAR_SANDBOX','').lower() in ('1','true','yes') else None); \
from contextlib import suppress; \
with p as c: \
    r=c.organizations.list(limit=1); \
    print('token_ok', r is not None)"
```

If you get `401 invalid_token`, rotate/regenerate `POLAR_ACCESS_TOKEN` in Polar dashboard and update env.

### Verify webhook delivery

1. Trigger a test checkout payment.
2. Confirm Polar dashboard shows webhook deliveries as `2xx`.
3. Confirm your DB user row is updated (`polar_subscription_id`, `subscription_status`).
