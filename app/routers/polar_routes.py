"""
Polar.sh payment integration routes.
See: https://polar.sh/docs/integrate/sdk/python
"""
import logging
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from polar_sdk import Polar
from polar_sdk.webhooks import WebhookVerificationError, validate_event
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.constants import POLAR_PRODUCT_ID_ENV_KEYS
from app.database import get_db
from app.models import User
from app.schemas import (
    SubscriptionCreationResponse,
    SubscriptionPlanResponse,
    SubscriptionStatus,
)
from app.services.subscription_config import get_all_plans
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

# .env loading
_POSSIBLE_ENV_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    os.path.join(os.path.dirname(__file__), ".env"),
    ".env",
]
for _path in _POSSIBLE_ENV_PATHS:
    if os.path.exists(_path):
        load_dotenv(dotenv_path=_path)
        break

POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN")
POLAR_WEBHOOK_SECRET = os.getenv("POLAR_WEBHOOK_SECRET")
POLAR_SUCCESS_URL = os.getenv("POLAR_SUCCESS_URL")
POLAR_SANDBOX = os.getenv("POLAR_SANDBOX", "").lower() in ("1", "true", "yes")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

router = APIRouter()


def _read_field(source, field_name, default=None):
    """Read a field from dict-like or object-like SDK responses."""
    if source is None:
        return default
    if isinstance(source, dict):
        return source.get(field_name, default)
    return getattr(source, field_name, default)


def _normalize_amount(raw_amount):
    """Normalize Polar amount to major currency units (e.g. cents -> dollars)."""
    if raw_amount is None:
        return None
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return None
    return round(amount / 100, 2) if amount >= 100 else round(amount, 2)


def _monthly_equivalent(amount, interval: str):
    if amount is None:
        return None
    if interval == "year":
        return round(amount / 12, 2)
    return amount


def _extract_price_entries(product_obj) -> list[dict]:
    prices = _read_field(product_obj, "prices", []) or []
    entries = []
    for price_obj in prices:
        interval = (_read_field(price_obj, "recurring_interval") or _read_field(price_obj, "interval") or "month").lower()
        raw_amount = _read_field(price_obj, "price_amount")
        if raw_amount is None:
            raw_amount = _read_field(price_obj, "amount")
        if raw_amount is None:
            raw_amount = _read_field(price_obj, "unit_amount")
        amount = _normalize_amount(raw_amount)
        currency = (_read_field(price_obj, "price_currency") or _read_field(price_obj, "currency") or "usd").lower()
        entries.append(
            {
                "id": _read_field(price_obj, "id"),
                "interval": interval,
                "price": amount,
                "display_price": _monthly_equivalent(amount, interval),
                "currency": currency,
            }
        )
    return entries


def _get_polar_client(raise_if_missing: bool = True) -> Optional[Polar]:
    """Create a Polar SDK client. Set raise_if_missing=False for webhook background tasks."""
    if not POLAR_ACCESS_TOKEN:
        if raise_if_missing:
            raise HTTPException(
                status_code=503,
                detail="Polar integration is not configured (POLAR_ACCESS_TOKEN missing).",
            )
        return None
    server = "sandbox" if POLAR_SANDBOX else None
    return Polar(access_token=POLAR_ACCESS_TOKEN, server=server)


def _resolve_product_id(plan_key: str) -> Optional[str]:
    """Resolve Polar product ID from plan_key via env."""
    env_key = POLAR_PRODUCT_ID_ENV_KEYS.get(plan_key)
    return os.getenv(env_key) if env_key else None


@router.get("/plans")
async def get_subscription_plans():
    """Get plans from Polar products with live pricing."""
    plan_catalog = get_all_plans()
    plan_by_key = {p["plan_key"]: p for p in plan_catalog}

    response_plans = []
    polar = _get_polar_client()

    with polar as client:
        for plan_key, env_key in POLAR_PRODUCT_ID_ENV_KEYS.items():
            product_id = os.getenv(env_key)
            if not product_id:
                logger.warning("Missing Polar product mapping for plan '%s' (%s)", plan_key, env_key)
                continue

            try:
                product_response = client.products.get(id=product_id)
                product_obj = getattr(product_response, "product", product_response)
            except Exception as exc:
                logger.error("Failed loading Polar product %s for %s: %s", product_id, plan_key, exc, exc_info=True)
                continue

            plan_template = plan_by_key.get(plan_key, {})
            product_name = _read_field(product_obj, "name", plan_template.get("name", plan_key.title()))
            product_description = _read_field(
                product_obj,
                "description",
                plan_template.get("description"),
            )
            price_entries = _extract_price_entries(product_obj)

            # If product has no prices yet, still return the product as selectable.
            if not price_entries:
                response_plans.append(
                    {
                        "plan_key": plan_key,
                        "id": product_id,
                        "polar_product_id": product_id,
                        "name": product_name,
                        "description": product_description,
                        "interval": "month",
                        "price": None,
                        "display_price": None,
                        "currency": "usd",
                        "contact_sales": False,
                        "features": plan_template.get("features", []),
                    }
                )
                continue

            for entry in price_entries:
                interval = entry["interval"]
                suffix = " Yearly" if interval == "year" else ""
                response_plans.append(
                    {
                        "plan_key": plan_key,
                        "id": entry["id"] or product_id,
                        "polar_product_id": product_id,
                        "name": f"{product_name}{suffix}",
                        "description": product_description,
                        "interval": interval,
                        "price": entry["price"],
                        "display_price": entry["display_price"],
                        "currency": entry["currency"],
                        "contact_sales": False,
                        "features": plan_template.get("features", []),
                    }
                )

    # Keep enterprise/contact-sales visible even if no Polar product is configured.
    for plan in plan_catalog:
        if plan.get("contact_sales"):
            response_plans.append(
                {
                    "plan_key": plan["plan_key"],
                    "id": None,
                    "polar_product_id": None,
                    "name": plan["name"],
                    "description": plan.get("description"),
                    "interval": "custom",
                    "price": None,
                    "display_price": None,
                    "currency": None,
                    "contact_sales": True,
                    "features": plan.get("features", []),
                }
            )

    return SubscriptionPlanResponse(plans=response_plans)


@router.post("/create-checkout", response_model=SubscriptionCreationResponse)
async def create_checkout(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Polar checkout session for the given product.
    product_id: Polar product UUID from your Polar dashboard.
    """
    success_url = POLAR_SUCCESS_URL or f"{FRONTEND_URL}/dashboard/checkout/success?checkout_id={{CHECKOUT_ID}}"
    cancel_url = f"{FRONTEND_URL}/pricing" if FRONTEND_URL else None

    polar = _get_polar_client()
    try:
        with polar as client:
            create_params: dict = {
                "products": [product_id],
                "success_url": success_url,
                "customer_email": current_user.email,
                "external_customer_id": str(current_user.id),
                "metadata": {"user_id": str(current_user.id)},
            }
            if cancel_url:
                create_params["return_url"] = cancel_url

            res = client.checkouts.create(request=create_params)
    except Exception as e:
        logger.error(f"Polar checkout creation failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Could not create checkout session. Please try again later.",
        )

    checkout = getattr(res, "checkout", res)
    checkout_url = getattr(checkout, "url", None)
    if not checkout_url:
        raise HTTPException(status_code=500, detail="Invalid checkout response from Polar.")

    checkout_id = getattr(checkout, "id", None) or ""
    return SubscriptionCreationResponse(
        session_id=str(checkout_id),
        checkout_url=checkout_url,
    )


@router.post("/webhook")
async def polar_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Handle Polar webhook events.
    Configure this URL in your Polar dashboard: https://your-api.com/api/polar/webhook
    """
    if not POLAR_WEBHOOK_SECRET:
        logger.warning("[Polar Webhook] POLAR_WEBHOOK_SECRET not set")
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    body = await request.body()
    headers = dict(request.headers)

    try:
        event = validate_event(
            body=body,
            headers=headers,
            secret=POLAR_WEBHOOK_SECRET,
        )
    except WebhookVerificationError as e:
        logger.warning(f"[Polar Webhook] Signature verification failed: {e}")
        return Response(status_code=403)
    except Exception as e:
        logger.error(f"[Polar Webhook] Validation error: {e}", exc_info=True)
        return Response(status_code=400)

    event_type = getattr(event, "type", None) or event.get("type", "")
    data = getattr(event, "data", None) or event.get("data", {})

    logger.info(f"[Polar Webhook] Event: {event_type}")

    # Defer heavy work to background to respond within 2s (Polar recommendation)
    background_tasks.add_task(
        _handle_polar_webhook_event,
        event_type=event_type,
        data=data,
        db=db,
    )

    return Response(status_code=202)


async def _handle_polar_webhook_event(
    event_type: str,
    data: dict,
    db: Session,
) -> None:
    """Process Polar webhook event in background."""
    try:
        if event_type == "order.paid":
            await _handle_order_paid(data, db)
        elif event_type == "subscription.active":
            await _handle_subscription_active(data, db)
        elif event_type in ("subscription.canceled", "subscription.revoked"):
            await _handle_subscription_canceled(data, db)
        elif event_type == "subscription.updated":
            await _handle_subscription_updated(data, db)
    except Exception as e:
        logger.error(f"[Polar Webhook] Error handling {event_type}: {e}", exc_info=True)


async def _get_user_from_polar_customer(customer_id: str, db: Session) -> Optional[User]:
    """Resolve our User from Polar customer_id via external_id."""
    if not customer_id or not POLAR_ACCESS_TOKEN:
        return None
    polar = _get_polar_client(raise_if_missing=False)
    if not polar:
        return None
    try:
        with polar as client:
            customer = client.customers.get(id=customer_id)
        if not customer:
            return None
        # Handle both wrapped (customer.customer) and direct response
        cust = getattr(customer, "customer", customer)
        external_id = getattr(cust, "external_id", None)
        if not external_id:
            return None
        user_id = int(external_id)
        return db.query(User).filter(User.id == user_id).first()
    except Exception as e:
        logger.warning(f"Could not resolve Polar customer {customer_id}: {e}")
        return None


async def _get_product_name(product_id: str) -> str:
    """Fetch product name from Polar."""
    polar = _get_polar_client(raise_if_missing=False)
    if not product_id or not polar:
        return "Unknown"
    try:
        with polar as client:
            product = client.products.get(id=product_id)
        prod = getattr(product, "product", product)
        return getattr(prod, "name", None) or "Unknown"
    except Exception:
        return "Unknown"


async def _handle_order_paid(data: dict, db: Session) -> None:
    """Handle order.paid: first-time purchase or renewal."""
    customer_id = data.get("customer_id")
    if not customer_id:
        return
    user = await _get_user_from_polar_customer(customer_id, db)
    if not user:
        return

    order_id = data.get("id")
    product_id = data.get("product_id")
    subscription_id = data.get("subscription_id")

    product_name = await _get_product_name(product_id) if product_id else "Unknown"

    user.polar_customer_id = customer_id
    user.subscription_plan = product_name
    user.subscription_status = "active"

    if subscription_id:
        user.polar_subscription_id = subscription_id
        # Fetch subscription for period dates
        polar = _get_polar_client(raise_if_missing=False)
        if polar:
            try:
                with polar as client:
                    sub = client.subscriptions.get(id=subscription_id)
                sub_obj = getattr(sub, "subscription", sub)
                if sub_obj:
                    current_period_end = getattr(sub_obj, "current_period_end", None)
                    if current_period_end:
                        user.current_period_end = (
                            current_period_end
                            if isinstance(current_period_end, datetime)
                            else datetime.fromisoformat(str(current_period_end).replace("Z", "+00:00"))
                        )
                    trial_end = getattr(sub_obj, "trial_end", None)
                    if trial_end:
                        user.trial_end = (
                            trial_end
                            if isinstance(trial_end, datetime)
                            else datetime.fromisoformat(str(trial_end).replace("Z", "+00:00"))
                        )
            except Exception as e:
                logger.warning(f"Could not fetch subscription {subscription_id}: {e}")

    db.commit()
    logger.info(f"[Polar Webhook] Updated user {user.id} from order {order_id}")


async def _handle_subscription_active(data: dict, db: Session) -> None:
    """Handle subscription.active."""
    customer_id = data.get("customer_id")
    subscription_id = data.get("id")
    if not customer_id:
        return
    user = await _get_user_from_polar_customer(customer_id, db)
    if not user:
        return

    product_id = data.get("product_id")
    product_name = await _get_product_name(product_id) if product_id else "Unknown"

    user.polar_customer_id = customer_id
    user.polar_subscription_id = subscription_id
    user.subscription_plan = product_name
    user.subscription_status = "active"

    current_period_end = data.get("current_period_end")
    if current_period_end:
        user.current_period_end = (
            current_period_end
            if isinstance(current_period_end, datetime)
            else datetime.fromisoformat(str(current_period_end).replace("Z", "+00:00"))
        )
    trial_end = data.get("trial_end")
    if trial_end:
        user.trial_end = (
            trial_end
            if isinstance(trial_end, datetime)
            else datetime.fromisoformat(str(trial_end).replace("Z", "+00:00"))
        )

    db.commit()
    logger.info(f"[Polar Webhook] Activated subscription for user {user.id}")


async def _handle_subscription_canceled(data: dict, db: Session) -> None:
    """Handle subscription.canceled / subscription.revoked."""
    subscription_id = data.get("id")
    if not subscription_id:
        return
    user = db.query(User).filter(User.polar_subscription_id == subscription_id).first()
    if not user:
        return

    user.subscription_status = "canceled"
    user.polar_subscription_id = None
    user.current_period_end = None
    user.trial_end = None
    db.commit()
    logger.info(f"[Polar Webhook] Canceled subscription for user {user.id}")


async def _handle_subscription_updated(data: dict, db: Session) -> None:
    """Handle subscription.updated."""
    subscription_id = data.get("id")
    if not subscription_id:
        return
    user = db.query(User).filter(User.polar_subscription_id == subscription_id).first()
    if not user:
        return

    status = data.get("status")
    if status:
        user.subscription_status = status
    current_period_end = data.get("current_period_end")
    if current_period_end:
        user.current_period_end = (
            current_period_end
            if isinstance(current_period_end, datetime)
            else datetime.fromisoformat(str(current_period_end).replace("Z", "+00:00"))
        )
    trial_end = data.get("trial_end")
    if trial_end is not None:
        user.trial_end = (
            trial_end
            if isinstance(trial_end, datetime)
            else datetime.fromisoformat(str(trial_end).replace("Z", "+00:00"))
        )
    db.commit()


@router.get("/subscription-status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's subscription status (Stripe or Polar)."""
    details = await SubscriptionService.get_user_subscription_details(current_user)
    return SubscriptionStatus(
        status=details["status"],
        plan=details["plan"],
        current_period_end=details["current_period_end"],
        trial_end=details["trial_end"],
        cancel_at_period_end=details.get("cancel_at_period_end"),
    )
