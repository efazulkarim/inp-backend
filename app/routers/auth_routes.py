# app/routers/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app import auth, schemas, models # Assuming app.auth handles JWT creation
from app.database import get_db
# get_current_user might be used for protected routes, not directly in OAuth flow here
# from app.auth import get_current_user 
from app.blacklist import blacklist_token # Keep if you have a manual logout for JWTs
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging
from fastapi.responses import RedirectResponse, JSONResponse
import os
import traceback
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware # Required for Oauth state

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()
auth_scheme = HTTPBearer() # Keep for other auth methods if any

# OAuth settings
# Ensure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI are in your .env
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI") # This will be used in authorize_redirect

if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
    logger.error("Missing Google OAuth environment variables!")
    # You might want to raise an error here or handle it gracefully

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# The guide implies session middleware is needed for OAuth state management.
# This should be added to your main FastAPI app, not here directly.
# Example for main.py: app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))
# Make sure SESSION_SECRET_KEY is set in your .env file.

@router.post("/login", response_model=schemas.Token) # Standard email/password login
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or password")
    
    access_token = auth.create_access_token(data={"sub": db_user.email})
    refresh_token = auth.create_refresh_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

@router.get('/google/login')
async def google_login_route(request: Request):
    logger.info(f"[Google Login] Initiating Google OAuth login. Configured Redirect URI: {GOOGLE_REDIRECT_URI}")
    # The redirect_uri for authorize_redirect should match one of the Authorized redirect URIs in your Google Cloud Console.
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)

@router.get('/google/callback')
async def google_callback_route(request: Request, db: Session = Depends(get_db)):
    logger.info(f"[Google Callback] Received callback. Request URL: {request.url}")
    try:
        token = await oauth.google.authorize_access_token(request)
        logger.info(f"[Google Callback] Token received successfully.") 
        # logger.debug(f"[Google Callback] Full token: {token}") # Be cautious logging full tokens
    except Exception as e:
        logger.error(f"[Google Callback] Error authorizing access token: {e}")
        logger.error(f"[Google Callback] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth authorization failed: {str(e)}")

    try:
        user_info_google = token.get('userinfo')
        if not user_info_google:
            # If userinfo is not directly in the token, try parsing id_token
            # This part depends on how authlib is configured and what Google returns
            logger.info("[Google Callback] 'userinfo' not in token, attempting to parse id_token.")
            user_info_google = await oauth.google.parse_id_token(token)
            if not user_info_google:
                 logger.error("[Google Callback] Failed to get user_info from token or id_token.")
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not fetch user information from Google.")
        
        logger.info(f"[Google Callback] User info from Google: {user_info_google}")
        email = user_info_google.get('email')

        if not email:
            logger.error("[Google Callback] Email not found in user_info.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google.")

    except HTTPException as he:
        raise he # Re-raise HTTPExceptions directly
    except Exception as e:
        logger.error(f"[Google Callback] Error processing user information: {e}")
        logger.error(f"[Google Callback] Full token at error: {token}") # Log token for debugging
        logger.error(f"[Google Callback] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to process user information: {str(e)}")

    # Check if user exists, else create
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if not db_user:
        logger.info(f"[Google Callback] User {email} not found. Creating new user.")
        db_user = models.User(
            email=email,
            username=user_info_google.get('email', '').split('@')[0], # Use email part as username
            first_name=user_info_google.get('given_name', ''),
            last_name=user_info_google.get('family_name', ''),
            password="",  # No password for OAuth users, or generate a random one if your model requires it
            verified=True # Assume email is verified by Google
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"[Google Callback] User {email} created successfully.")
    else:
        logger.info(f"[Google Callback] User {email} found in database.")

    # Issue JWT tokens (using your existing app.auth methods)
    access_token = auth.create_access_token(data={"sub": db_user.email})
    refresh_token = auth.create_refresh_token(data={"sub": db_user.email})
    logger.info(f"[Google Callback] JWTs created for user {email}.")

    # Redirect to frontend with tokens
    # Ensure FRONTEND_URL is set in your .env
    frontend_url = os.getenv('FRONTEND_URL', 'https://inp-dashboard.netlify.app') # Default to root if not set
    response_url = f"{frontend_url}/oauth-success?access_token={access_token}&refresh_token={refresh_token}"
    logger.info(f"[Google Callback] Redirecting to: {response_url}")
    return RedirectResponse(url=response_url)

@router.post("/register", response_model=schemas.UserDisplay)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user_by_username = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    hashed_password = auth.hash_password(user.password)
    new_user = models.User(
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/refresh-token", response_model=schemas.Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    return auth.refresh_access_token(refresh_token, db)

@router.post("/logout")
def logout(token: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    """
    This route allows the user to "logout" by blacklisting the access token.
    """
    # Add the token to the blacklist
    blacklist_token(token.credentials)
    return {"msg": "Successfully logged out"}

@router.post("/forgot-password", response_model=schemas.MessageResponse)
def forgot_password(request: schemas.ForgotPassword, db: Session = Depends(get_db)):
    """
    Request a password reset. This endpoint will generate a token and in a real application would
    send an email with a link containing the token.
    """
    # Check if the user exists
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        # Don't reveal that the user doesn't exist for security reasons
        # Instead, log it and return a generic message
        logger.info(f"Password reset requested for non-existent email: {request.email}")
        return {"msg": "If your email is registered, you will receive a password reset link."}
    
    # Generate password reset token
    reset_token = auth.create_password_reset_token(user.email)
    
    # TODO: In a real application, send an email with the reset token/link
    # For development, we'll just return the token in the response
    logger.info(f"Password reset token generated for {user.email}: {reset_token}")
    
    # Return success message
    return {"msg": "If your email is registered, you will receive a password reset link."}

@router.post("/reset-password", response_model=schemas.MessageResponse)
def reset_password(request: schemas.ResetPassword, db: Session = Depends(get_db)):
    """
    Reset the password using the token received from the forgot-password endpoint.
    """
    # Verify the reset token and get the email
    try:
        email = auth.verify_password_reset_token(request.token)
    except HTTPException as e:
        # Token verification failed
        logger.warning(f"Invalid password reset token: {request.token}")
        raise e
    
    # Find the user
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # This shouldn't happen if the token was valid, but check anyway
        logger.error(f"User not found for valid token with email: {email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash the new password and update the user
    hashed_password = auth.hash_password(request.new_password)
    user.password = hashed_password
    db.commit()
    
    # Log the success
    logger.info(f"Password successfully reset for user: {email}")
    
    # Return success message
    return {"msg": "Password has been reset successfully. You can now log in with your new password."}
