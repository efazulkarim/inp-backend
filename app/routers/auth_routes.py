# app/routers/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import auth, schemas, models
from app.database import get_db
from app.auth import get_current_user
from app.blacklist import blacklist_token, is_token_blacklisted
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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

@router.post("/register", response_model=schemas.UserCreate)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.hash_password(user.password)
    new_user = models.User(
        email=user.email, 
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
