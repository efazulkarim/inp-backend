"""
Subscription service for managing user subscriptions and feature access.
"""
import stripe
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models import User
from app.services.subscription_config import (
    SUBSCRIPTION_PLANS, 
    get_limit_for_plan, 
    is_feature_available, 
    get_plan_by_price_id
)

class SubscriptionService:
    """Service for managing subscriptions and subscription-related logic"""
    
    @staticmethod
    async def get_user_subscription_details(user: User) -> Dict[str, Any]:
        """Get the subscription details for a user"""
        if not user.subscription_plan or not user.stripe_subscription_id:
            return {
                "status": "inactive",
                "plan": None,
                "current_period_end": None,
                "trial_end": None,
                "cancel_at_period_end": False,
                "features": [],
                "limits": {}
            }
        
        # Get the plan details
        plan_key = user.subscription_plan.lower() if user.subscription_plan else None
        plan_details = SUBSCRIPTION_PLANS.get(plan_key, {})
        
        return {
            "status": user.subscription_status or "inactive",
            "plan": user.subscription_plan,
            "current_period_end": user.current_period_end,
            "trial_end": user.trial_end,
            "cancel_at_period_end": False,  # This should be fetched from Stripe in a real implementation
            "features": plan_details.get("features", []),
            "limits": plan_details.get("limits", {})
        }
    
    @staticmethod
    async def can_access_feature(user: User, feature_name: str) -> bool:
        """Check if a user can access a specific feature based on their subscription"""
        if not user.subscription_plan:
            return False
            
        plan_key = user.subscription_plan.lower()
        return is_feature_available(plan_key, feature_name)
    
    @staticmethod
    async def get_user_limit(user: User, limit_name: str) -> int:
        """Get the limit for a specific resource based on user's subscription"""
        if not user.subscription_plan:
            return 0
            
        plan_key = user.subscription_plan.lower()
        return get_limit_for_plan(plan_key, limit_name)
    
    @staticmethod
    async def check_resource_limit(user: User, limit_name: str, current_count: int) -> bool:
        """Check if a user has reached their limit for a specific resource"""
        limit = await SubscriptionService.get_user_limit(user, limit_name)
        
        # Handle unlimited (float('inf')) case
        if limit == float('inf'):
            return True
            
        return current_count < limit
    
    @staticmethod
    async def get_all_subscription_plans() -> List[Dict[str, Any]]:
        """Return all plans (one entry per billing interval) ready for the public API."""
        from app.services.subscription_config import get_all_plans  # Local import to avoid circular
        return get_all_plans()
    
    @staticmethod
    async def update_user_subscription_from_stripe(user: User, db: Session) -> None:
        """Update user's subscription details from Stripe"""
        if not user.stripe_subscription_id:
            return
            
        try:
            # Get the subscription from Stripe
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
            
            # Get the product details
            product = stripe.Product.retrieve(subscription.plan.product)
            
            # Update the user record
            user.subscription_status = subscription.status
            user.subscription_plan = product.name
            user.current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            
            if subscription.trial_end:
                user.trial_end = datetime.fromtimestamp(subscription.trial_end)
                
            db.commit()
        except Exception as e:
            # Log the error but don't throw an exception
            print(f"Error updating subscription from Stripe: {str(e)}")
    
    @staticmethod
    async def process_subscription_change(user: User, new_price_id: str, db: Session) -> Dict[str, Any]:
        """Process a subscription change (upgrade/downgrade)"""
        if not user.stripe_subscription_id:
            raise ValueError("No active subscription found")
        
        # Get the new plan details
        new_plan = get_plan_by_price_id(new_price_id)
        if not new_plan:
            raise ValueError(f"Invalid price ID: {new_price_id}")
            
        try:
            # Retrieve the subscription
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
            
            # Update the subscription
            updated_subscription = stripe.Subscription.modify(
                user.stripe_subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
            )
            
            # Get product details
            product = stripe.Product.retrieve(updated_subscription['items']['data'][0]['price']['product'])
            
            # Update user record
            user.subscription_plan = product.name
            user.subscription_status = updated_subscription.status
            user.current_period_end = datetime.fromtimestamp(updated_subscription.current_period_end)
            db.commit()
            
            return {
                "status": "success",
                "message": "Subscription updated successfully",
                "new_plan": product.name
            }
        except Exception as e:
            raise ValueError(f"Failed to update subscription: {str(e)}")
