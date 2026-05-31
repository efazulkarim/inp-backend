from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import get_current_user
from datetime import datetime
import stripe
from app.services.subscription_service import SubscriptionService
from app.schemas import (
    SubscriptionTier, 
    SubscriptionPlanResponse,
    SubscriptionStatus,
    SubscriptionUpdateRequest, 
    SubscriptionCreationResponse,
    SubscriptionPortalResponse
)
import os
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
import json
from typing import Optional
from fastapi.security import HTTPBearer
import logging

logger = logging.getLogger(__name__)

# Robust .env loading (similar to llm_service.py)
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),  # project root
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),  # app dir
    os.path.join(os.path.dirname(__file__), ".env"),  # routers dir
    ".env"  # current working directory
]

env_found = False
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[Stripe Routes] Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
        
if not env_found:
    print("[Stripe Routes] ⚠️ WARNING: No .env file found in any standard location!")

# Set Stripe API Key and print debug info
stripe_key = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = stripe_key

# Get webhook secret and print debug info
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

router = APIRouter()
security = HTTPBearer()

@router.get("/plans")
async def get_subscription_plans():
    """Get all available subscription plans"""
    try:
        plans = await SubscriptionService.get_all_subscription_plans()
        return SubscriptionPlanResponse(plans=plans)
    except Exception as e:
        logger.error(f"Error getting subscription plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve subscription plans. Please try again later.")

@router.post("/create-checkout-session", response_model=SubscriptionCreationResponse)
async def create_checkout_session(
    price_id: str,
    user_email: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if not stripe.api_key:
            # Fallback: Try to set it again
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
            logger.warning("Stripe API key was missing at runtime. Reloaded from env.")
        
        # Check if user already has a Stripe customer ID
        if not current_user.stripe_customer_id:
            # Create a new customer in Stripe
            customer = stripe.Customer.create(
                email=user_email,
                metadata={
                    "user_id": current_user.id
                }
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{os.getenv('FRONTEND_URL')}/dashboard/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/pricing",
            metadata={
                "user_id": current_user.id,
                "app_email": current_user.email  # Store email in metadata
            }
        )
        
        return SubscriptionCreationResponse(
            session_id=session.id,
            checkout_url=session.url
        )
    except Exception as e:
        logger.error(f"Error creating checkout session for user {current_user.email}, price_id {price_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not create checkout session. Please try again later.")

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.warning("[Stripe Webhook] Invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.warning("[Stripe Webhook] Signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid signature")
    logger.info("[Stripe Webhook] Event received: %s", event["type"])

    # Handle various webhook events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Extract data
        user_id = session['metadata']['user_id']
        subscription_id = session.get('subscription')
        customer_id = session['customer']
        
        # Retrieve subscription details
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Safely extract dates (might not exist for new subscriptions)
        current_period_end = None
        trial_end = None
        
        if subscription.get('current_period_end'):
            current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        
        if subscription.get('trial_end'):
            trial_end = datetime.fromtimestamp(subscription['trial_end'])
        
        # Get product details
        product_id = subscription['items']['data'][0]['price']['product']
        product = stripe.Product.retrieve(product_id)
        
        # Update user in database
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
            user.subscription_plan = product['name']
            user.subscription_status = subscription['status']
            user.current_period_end = current_period_end
            user.trial_end = trial_end
            db.commit()
            # Send invoice in background
            background_tasks.add_task(
                send_invoice_email,
                user_email=user.email,
                amount=session['amount_total'] / 100,
                currency=session['currency'],
                subscription_plan=product['name']
            )
        else:
            logger.warning("[Stripe Webhook] No user found for user_id=%s", user_id)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        user = db.query(User).filter(
            User.stripe_subscription_id == subscription['id']
        ).first()
        
        if user:
            user.subscription_status = "canceled"
            user.stripe_subscription_id = None
            user.current_period_end = None
            user.trial_end = None
            db.commit()
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        user = db.query(User).filter(
            User.stripe_subscription_id == subscription['id']
        ).first()
        
        if user:
            product = stripe.Product.retrieve(subscription['items']['data'][0]['price']['product'])
            user.subscription_plan = product['name']
            user.subscription_status = subscription['status']
            user.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            user.trial_end = datetime.fromtimestamp(subscription['trial_end']) if subscription.get('trial_end') else None
            db.commit()
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        user = db.query(User).filter(
            User.stripe_customer_id == invoice['customer']
        ).first()
        
        if user:
            user.subscription_status = "past_due"
            db.commit()
            
            # TODO: Send payment failed email to user
            background_tasks.add_task(
                send_payment_failed_email,
                user_email=user.email,
                amount=invoice['amount_due'] / 100,
                currency=invoice['currency']
            )

    return {"status": "success"}

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.stripe_subscription_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    try:
        # Cancel the subscription in Stripe
        stripe.Subscription.delete(current_user.stripe_subscription_id)
        
        # Update user record
        current_user.subscription_status = "canceled"
        current_user.stripe_subscription_id = None
        current_user.current_period_end = None
        current_user.trial_end = None
        db.commit()
        
        return {"message": "Subscription canceled successfully"}
    except Exception as e:
        logger.error(f"Error canceling subscription for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not cancel subscription. Please try again later.")

@router.post("/create-portal-session", response_model=SubscriptionPortalResponse)
async def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(status_code=404, detail="No Stripe customer found")

        # Create a portal session
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{os.getenv('FRONTEND_URL')}/settings",
        )

        return SubscriptionPortalResponse(portal_url=session.url)
    except Exception as e:
        logger.error(f"Error creating portal session for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not create portal session. Please try again later.")

@router.get("/subscription-status", response_model=SubscriptionStatus)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's subscription status"""
    try:
        # Update the user's subscription data from Stripe
        await SubscriptionService.update_user_subscription_from_stripe(current_user, db)
        
        # Get subscription details from our service
        subscription_details = await SubscriptionService.get_user_subscription_details(current_user)
        
        return SubscriptionStatus(
            status=subscription_details["status"],
            plan=subscription_details["plan"],
            current_period_end=subscription_details["current_period_end"],
            trial_end=subscription_details["trial_end"],
            cancel_at_period_end=subscription_details["cancel_at_period_end"]
        )
    except Exception as e:
        logger.error(f"Error fetching subscription status for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve subscription status. Please try again later.")

@router.post("/update-subscription")
async def update_subscription(
    update_request: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the subscription to a new plan"""
    try:
        result = await SubscriptionService.process_subscription_change(
            user=current_user,
            new_price_id=update_request.price_id,
            db=db
        )
        return result
    except ValueError as ve: # Specific exception for user not found or invalid plan
        logger.warning(f"ValueError during subscription update for user {current_user.email}, price_id {update_request.price_id}: {ve}")
        raise HTTPException(status_code=404, detail=str(ve)) # Can expose str(ve) as it's a custom message
    except stripe.error.StripeError as se:
        logger.error(f"StripeError during subscription update for user {current_user.email}, price_id {update_request.price_id}: {se}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Stripe error: {se.user_message or 'Could not process payment or update.'}")
    except Exception as e:
        logger.error(f"Unexpected error during subscription update for user {current_user.email}, price_id {update_request.price_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not update subscription. Please try again later.")

async def send_invoice_email(user_email: str, amount: float, currency: str, subscription_plan: str):
    """
    Send an invoice email to the user
    Note: Implement your email sending logic here
    You can use libraries like fastapi-mail or python-jose for this
    """
    # TODO: Implement your email sending logic
    logger.info("Invoice email task queued for %s", user_email)
    pass

async def send_payment_failed_email(user_email: str, amount: float, currency: str):
    """
    Send a payment failed notification email to the user
    Note: Implement your email sending logic here
    """
    # TODO: Implement your email sending logic
    logger.info("Payment failed email task queued for %s", user_email)
    pass