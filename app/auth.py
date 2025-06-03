import os
from dotenv import load_dotenv

# Robust .env loading (similar to main.py and stripe_routes.py)
possible_env_paths = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),  # project root
    os.path.join(os.path.dirname(__file__), '.env'),  # app directory
    '.env'  # current working directory
]
env_found = False
for env_path in possible_env_paths:
    if os.path.exists(env_path):
        print(f"[auth.py] 💡 Found .env file at: {env_path}")
        load_dotenv(dotenv_path=env_path)
        env_found = True
        break
if not env_found:
    print("[auth.py] ⚠️ WARNING: No .env file found in any standard location!")

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from app.blacklist import is_token_blacklisted
import secrets

# Token expiration times
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 90))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))  # Refresh token expiration period

# Secret key and algorithm for JWT
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes for Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
auth_scheme = HTTPBearer()

# Hashing password
def hash_password(password: str):
    return pwd_context.hash(password)

# Verifying password
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# JWT Token creation for access token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT Token creation for refresh token
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Check if token is blacklisted
        if is_token_blacklisted(token.credentials):
            raise credentials_exception

        # Decoding the token
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Query user from database
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Function to refresh the access token using the refresh token
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode the refresh token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verify if the user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception

    # Create a new access token
    new_access_token = create_access_token(data={"sub": email})

    # Return both the new access token and the existing refresh token
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token  # Include the same refresh token in the response
    }

# Password reset token expiration time (in minutes)
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", 95))

# Create a password reset token
def create_password_reset_token(email: str) -> str:
    """
    Create a JWT token for password reset
    """
    expires = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    token_data = {
        "sub": email,
        "exp": expires,
        "type": "password_reset"
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

# Verify password reset token
def verify_password_reset_token(token: str) -> str:
    """
    Verify a password reset token and return the email if valid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired password reset token"
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("type")
        
        if email is None or token_type != "password_reset":
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception