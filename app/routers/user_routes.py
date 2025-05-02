# app/routers/user_routes.py
from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.models import User
from app import schemas
from app.database import get_db

router = APIRouter()
security = HTTPBearer()

@router.get(
    "/me", 
    response_model=schemas.UserMe,
    summary="Get current user profile",
    description="Get the profile of the currently authenticated user. Requires a valid JWT token in the Authorization header."
)
def read_user_me(
    credentials: HTTPAuthorizationCredentials = Security(security),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user
