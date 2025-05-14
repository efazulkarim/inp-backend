# app/routers/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import auth, schemas, models
from app.database import get_db
from app.auth import get_current_user
from app.blacklist import blacklist_token, is_token_blacklisted
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter()
auth_scheme = HTTPBearer()

@router.post("/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    if not auth.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    access_token = auth.create_access_token(data={"sub": db_user.email})
    refresh_token = auth.create_refresh_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}

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
