from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import create_access_token, get_current_user, verify_password
from app.config import get_runtime_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class User(BaseModel):
    username: str
    
class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=Token)
async def login(form_data: LoginRequest):
    settings = get_runtime_settings()
    
    # Dev mode bypass check
    if not settings.ADMIN_PASSWORD_HASH:
        logger.warning("AUTH WARNING: ADMIN_PASSWORD_HASH is empty! Bypassing authentication (DEV MODE).")
        access_token_expires = timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
        access_token = create_access_token(
            data={"sub": form_data.username, "role": "admin"}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.JWT_EXPIRY_MINUTES * 60}

    # Standard check
    if form_data.username != settings.ADMIN_USERNAME or not verify_password(form_data.password, settings.ADMIN_PASSWORD_HASH):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username, "role": "admin"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.JWT_EXPIRY_MINUTES * 60}

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    settings = get_runtime_settings()
    access_token_expires = timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.get("sub"), "role": current_user.get("role", "admin")}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.JWT_EXPIRY_MINUTES * 60}

@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user.get("sub", "unknown")}
