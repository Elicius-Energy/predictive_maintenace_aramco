"""Cookie session authentication, account lifecycle, and CSRF enforcement."""
import base64, hashlib, hmac, secrets, struct, time
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.db.models import User, AuditLog
from app.core.security import verify_password, hash_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
_failures = defaultdict(list)

def secure_cookie() -> bool:
    return settings.COOKIE_SECURE if settings.COOKIE_SECURE is not None else settings.ENVIRONMENT.lower() not in {"development", "dev", "test"}

class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None

class UserResponse(BaseModel):
    username: str
    role: str
    must_change_password: bool = False

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=256)

class MfaConfirm(BaseModel):
    code: str

def csrf_cookie(response: Response):
    response.set_cookie("elicius_csrf", secrets.token_urlsafe(32), httponly=False, samesite="lax", secure=secure_cookie(), max_age=settings.JWT_EXPIRY_MINUTES * 60)

def verify_totp(secret: str, code: str) -> bool:
    try:
        key = base64.b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8))
        counter = int(time.time()) // 30
        for step in (-1, 0, 1):
            digest = hmac.new(key, struct.pack(">Q", counter + step), hashlib.sha1).digest()
            offset = digest[-1] & 0x0f
            value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7fffffff) % 1000000
            if hmac.compare_digest(f"{value:06d}", code): return True
    except Exception:
        pass
    return False

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if not user or not user.is_active or payload.get("sv") != user.session_version:
        raise HTTPException(status_code=401, detail="Session revoked")
    if user.must_change_password and request.url.path not in {"/api/auth/me", "/api/auth/password", "/api/auth/logout"}:
        raise HTTPException(status_code=403, detail="Change your temporary password before continuing")
    if request.cookies.get(settings.COOKIE_NAME) and request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = request.cookies.get("elicius_csrf")
        if not csrf or not hmac.compare_digest(csrf, request.headers.get("X-CSRF-Token", "")):
            raise HTTPException(status_code=403, detail="CSRF validation failed")
    return user

def require_roles(*roles):
    def check(user: User = Depends(get_current_user)):
        if user.role.lower() not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return check

def can_access_device(user: User, device_id: str, db: Session) -> bool:
    if user.role.lower() == "admin": return True
    from app.db.models import UserDeviceAccess
    return db.query(UserDeviceAccess).filter_by(user_id=user.id, device_id=device_id).first() is not None

def require_device_access(user: User, device_id: str, db: Session):
    if not can_access_device(user, device_id, db):
        raise HTTPException(status_code=404, detail="Device not found")

def audit(db, actor, action, target=None, details=None):
    db.add(AuditLog(actor=actor, action=action, target=target, details=details or {}))

@router.post("/login", response_model=UserResponse)
def login(req: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    now = time.time(); ip = request.client.host if request.client else "unknown"; key = f"{ip}:{req.username.lower()}"
    _failures[key] = [x for x in _failures[key] if now - x < settings.LOGIN_LOCKOUT_SECONDS]
    if len(_failures[key]) >= settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        _failures[key].append(now)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if user.role.lower() == "admin" and user.mfa_enabled and (not req.mfa_code or not verify_totp(user.mfa_secret or "", req.mfa_code)):
        _failures[key].append(now)
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    _failures.pop(key, None)
    token = create_access_token({"sub": user.username, "sv": user.session_version})
    response.set_cookie(key=settings.COOKIE_NAME, value=token, httponly=True, samesite="lax", secure=secure_cookie(), max_age=settings.JWT_EXPIRY_MINUTES * 60)
    csrf_cookie(response)
    audit(db, user.username, "login")
    db.commit()
    return UserResponse(username=user.username, role=user.role, must_change_password=user.must_change_password)

@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.delete_cookie(key=settings.COOKIE_NAME, httponly=True, samesite="lax", secure=secure_cookie())
    response.delete_cookie("elicius_csrf", samesite="lax", secure=secure_cookie())
    user.session_version += 1
    audit(db, user.username, "logout", user.username)
    db.commit()
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(response: Response, user: User = Depends(get_current_user)):
    csrf_cookie(response)
    return UserResponse(username=user.username, role=user.role, must_change_password=user.must_change_password)

@router.post("/password")
def change_password(req: PasswordChange, response: Response, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(req.current_password, user.password_hash): raise HTTPException(400, "Current password is incorrect")
    if req.new_password == req.current_password: raise HTTPException(400, "Choose a different password")
    user.password_hash = hash_password(req.new_password); user.must_change_password = False; user.session_version += 1
    response.delete_cookie(key=settings.COOKIE_NAME, httponly=True, samesite="lax", secure=secure_cookie())
    response.delete_cookie("elicius_csrf", samesite="lax", secure=secure_cookie())
    audit(db, user.username, "password_changed", user.username); db.commit()
    return {"message": "Password changed. Sign in again."}

@router.post("/mfa/setup")
def setup_mfa(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    if not user.mfa_secret: user.mfa_secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    audit(db, user.username, "mfa_setup_started", user.username); db.commit()
    return {"secret": user.mfa_secret, "otpauth_uri": f"otpauth://totp/Elicius:{user.username}?secret={user.mfa_secret}&issuer=Elicius"}

@router.post("/mfa/enable")
def enable_mfa(req: MfaConfirm, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    if not user.mfa_secret or not verify_totp(user.mfa_secret, req.code): raise HTTPException(400, "MFA code is invalid")
    user.mfa_enabled = True; audit(db, user.username, "mfa_enabled", user.username); db.commit()
    return {"mfa_enabled": True}
