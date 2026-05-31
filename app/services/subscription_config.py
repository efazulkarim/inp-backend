"""
Configuration file for subscription plans and their features.
Polar is the only active billing provider.
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
        print(f"[Subscription Config] Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
if not env_found:
    print("[Subscription Config] ⚠️ WARNING: No .env file found!")

# -----------------------------------------------------------------------------
# PLAN DEFINITIONS
# -----------------------------------------------------------------------------

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
            "customer_personas": 5,
            "metric_modules": 0
        }
    },
    "entrepreneur": {
        "name": "Entrepreneur",
        "description": "Unlimited validation & advanced features",
        "features": [
            "Unlimited idea boards",
            "Idea validation",
            "Report generation",
            "Customer persona building",
            "Advanced metric modules"
        ],
        "limits": {
            "idea_boards": float('inf'),
            "reports_per_month": float('inf'),
            "customer_personas": float('inf'),
            "metric_modules": float('inf')
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Special price for your whole team – contact sales",
        "contact_sales": True,
        "features": [
            "Applicable for Universities and organizations more than 500 team size",
            "Advanced metric modules",
        ],
        "limits": {
            "idea_boards": float('inf'),
            "reports_per_month": float('inf'),
            "customer_personas": float('inf'),
            "metric_modules": float('inf')
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
    """Return public plan templates; pricing is fetched from Polar at runtime."""
    all_plans: List[Dict[str, Any]] = []
    for key, plan in SUBSCRIPTION_PLANS.items():
        # Enterprise (contact sales) - single entry
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

        all_plans.append({
            "plan_key": key,
            "id": None,
            "name": plan["name"],
            "description": plan["description"],
            "interval": "month",
            "price": None,
            "display_price": None,
            "currency": "usd",
            "contact_sales": False,
            "features": plan["features"],
        })
    return all_plans

def get_all_plans() -> List[Dict[str, Any]]:
    """Return **flattened** plans ready for the public `/plans` endpoint."""
    return _flatten_plans_for_public()

def get_plan_by_price_id(price_id: str) -> Optional[Dict[str, Any]]:
    """Deprecated in Polar-only mode."""
    _ = price_id
    return None
