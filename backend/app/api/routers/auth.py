from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import jwt

from ...db.database import get_db
from ...crud import user as crud_user
from ...schemas.user import User, UserCreate, UserLogin
from ...models.user import User as UserModel
from ...core.config import settings

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: User

class ForgotPassword(BaseModel):
    email: EmailStr

# Helper functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = crud_user.user.get_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# Routes
@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    user = crud_user.user.get_by_email(db, email=user_data.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    user = crud_user.user.create(db, obj_in=user_data)
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    # Create user response
    user_response = User.model_validate(user)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_response
    )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = crud_user.user.authenticate(
        db, email=user_credentials.email, password=user_credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not crud_user.user.is_active(user):
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    user_response = User.model_validate(user)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_response
    )

@router.get("/profile", response_model=User)
async def get_profile(current_user: UserModel = Depends(get_current_user)):
    return User.model_validate(current_user)

@router.post("/logout")
async def logout():
    # In a real implementation, you might want to blacklist the token
    return {"message": "Successfully logged out"}

@router.post("/forgot-password")
async def forgot_password(forgot_data: ForgotPassword, db: Session = Depends(get_db)):
    user = crud_user.user.get_by_email(db, email=forgot_data.email)
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    # In a real implementation, you would send an email here
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/refresh")
async def refresh_token(refresh_data: dict, db: Session = Depends(get_db)):
    try:
        refresh_token = refresh_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token required")
        
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user = crud_user.user.get_by_email(db, email=email)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")