"""
Configuration file for subscription plans and their features.
This file defines the 3-tier subscription model with pricing and features.
"""
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Robust .env loading (similar to llm_service.py)
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),  # project root
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),  # app parent dir
    os.path.join(os.path.dirname(__file__), ".env"),  # services dir
    ".env"  # current working directory
]
env_found = False
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[Subscription Config] 💡 Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
if not env_found:
    print("[Subscription Config] ⚠️ WARNING: No .env file found!")

# -----------------------------------------------------------------------------
# ENVIRONMENT VARIABLES (PRICE IDS)
# -----------------------------------------------------------------------------
# Solopreneur (one-time) – currently only a single monthly style charge that
# gives 30-day access. We still treat it as a "month" interval in Stripe.

SOLO_MONTHLY_PRICE_ID = os.getenv("STRIPE_SOLOPRENEUR_MONTHLY_PRICE_ID") or \
                        os.getenv("STRIPE_SOLOPRENEUR_PRICE_ID", "price_solo_monthly")

# Entrepreneur – true subscription with month & year interval prices
ENTREPRENEUR_MONTHLY_PRICE_ID = os.getenv("STRIPE_ENTREPRENEUR_MONTHLY_PRICE_ID") or \
                               os.getenv("STRIPE_ENTREPRENEUR_PRICE_ID", "price_ent_monthly")
ENTREPRENEUR_YEARLY_PRICE_ID = os.getenv("STRIPE_ENTREPRENEUR_YEARLY_PRICE_ID", "price_ent_yearly")

# Enterprise is handled by sales → no Stripe price ID (manual invoicing / quote)

# -----------------------------------------------------------------------------
# INTERNAL HELPERS
# -----------------------------------------------------------------------------

def _monthly_equivalent(amount: float, interval: str) -> float:
    """Return the monthly equivalent for the given amount & billing interval."""
    if interval == "year":
        return round(amount / 12, 2)
    return amount

# -----------------------------------------------------------------------------
# PLAN DEFINITIONS
# -----------------------------------------------------------------------------

# We keep the top-level key (plan_key) for feature/limit lookup but move the real
# price information under a nested `prices` mapping so that a plan can have
# multiple billing intervals (month & year).

SUBSCRIPTION_PLANS: Dict[str, Dict[str, Any]] = {
    "solopreneur": {
        "name": "Solopreneur",
        "description": "Full proof idea validation for one idea (30 days access)",
        "features": [
            "Full proof idea validation for one idea",
            "10 report generations",
            "5 customer personas"
        ],
        "limits": {
            "idea_boards": 1,
            "reports_per_month": 10,
            "customer_personas": 5
        },
        "prices": {
            "month": {
                "id": SOLO_MONTHLY_PRICE_ID,
                "price": 20.0,
                "currency": "usd",
                "display_price": _monthly_equivalent(20.0, "month"),
            }
        }
    },
    "entrepreneur": {
        "name": "Entrepreneur",
        "description": "Unlimited validation & advanced features",
        "features": [
            "Unlimited idea boards",
            "Idea validation",
            "Report generation",
            "Customer persona building"
        ],
        "limits": {
            "idea_boards": float('inf'),
            "reports_per_month": float('inf'),
            "customer_personas": float('inf')
        },
        "prices": {
            "month": {
                "id": ENTREPRENEUR_MONTHLY_PRICE_ID,
                "price": 29.0,
                "currency": "usd",
                "display_price": _monthly_equivalent(29.0, "month"),
            },
            "year": {
                "id": ENTREPRENEUR_YEARLY_PRICE_ID,
                "price": 312.0,  # $29 × 12 = 348 → ~10% discount
                "currency": "usd",
                "discount_percent": 10,
                "display_price": _monthly_equivalent(312.0, "year"),
            },
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Special price for your whole team – contact sales",
        "contact_sales": True,
        "features": [
            "Applicable for Universities and organizations more than 500 team size",
        ],
        "limits": {
            "idea_boards": float('inf'),
            "reports_per_month": float('inf'),
            "customer_personas": float('inf')
        },
    }
}

# -----------------------------------------------------------------------------
# LOOK-UP HELPERS (USED BY THE REST OF THE CODEBASE)
# -----------------------------------------------------------------------------

def is_feature_available(plan_name: str, feature_name: str) -> bool:
    """Check if a specific feature is available for a subscription plan."""
    plan = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        return False
    return feature_name in plan.get("features", [])

def get_limit_for_plan(plan_name: str, limit_name: str):
    """Get the specified usage limit for a subscription plan."""
    plan = SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        return 0
    return plan.get("limits", {}).get(limit_name, 0)

def _flatten_plans_for_public() -> List[Dict[str, Any]]:
    """Return a list with one entry *per billing interval* that is ready for the
    public `/plans` endpoint (so the frontend does not have to understand the
    nested data-structure)."""

    all_plans: List[Dict[str, Any]] = []
    for key, plan in SUBSCRIPTION_PLANS.items():
        # Enterprise (contact sales) – no Stripe price, single entry
        if plan.get("contact_sales"):
            all_plans.append({
                "plan_key": key,
                "id": None,
                "name": plan["name"],
                "description": plan["description"],
                "interval": "custom",
                "price": None,
                "display_price": None,
                "currency": None,
                "contact_sales": True,
                "features": plan["features"],
            })
            continue

        for interval, price_info in plan.get("prices", {}).items():
            all_plans.append({
                "plan_key": key,
                "id": price_info["id"],
                "name": f"{plan['name']}" + (" Yearly" if interval == "year" else ""),
                "description": plan["description"],
                "interval": interval,
                "price": price_info["price"],
                "display_price": price_info["display_price"],
                "currency": price_info["currency"],
                "contact_sales": False,
                "features": plan["features"],
            })
    return all_plans

def get_all_plans() -> List[Dict[str, Any]]:
    """Return **flattened** plans ready for the public `/plans` endpoint."""
    return _flatten_plans_for_public()

def get_plan_by_price_id(price_id: str) -> Optional[Dict[str, Any]]:
    """Return the plan dict **and** interval that matches a Stripe price_id."""
    for plan_key, plan in SUBSCRIPTION_PLANS.items():
        if plan.get("contact_sales"):
            continue
        for interval, price_info in plan.get("prices", {}).items():
            if price_info["id"] == price_id:
                # Return a merged dict with convenience fields
                merged = plan.copy()
                merged.update({
                    "interval": interval,
                    "price": price_info["price"],
                    "currency": price_info["currency"],
                    "price_id": price_info["id"],
                })
                return merged
    return None
