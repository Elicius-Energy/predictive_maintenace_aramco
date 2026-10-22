"""Administrator user and device grant management."""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User, Device, UserDeviceAccess, AuditLog
from app.api.auth import require_roles, audit
from app.core.security import hash_password

router = APIRouter(prefix="/api/users", tags=["user management"])

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    role: str
    device_ids: list[str] = []

class UserUpdate(BaseModel):
    role: str
    is_active: bool
    device_ids: list[str] = []

def validate_role(role):
    role = role.lower()
    if role not in {"admin", "analyst", "viewer"}: raise HTTPException(400, "Role must be Admin, Analyst, or Viewer")
    return role

def set_grants(db, user, ids):
    ids = list(dict.fromkeys(ids))
    found = {d.device_id for d in db.query(Device.device_id).filter(Device.device_id.in_(ids)).all()} if ids else set()
    if found != set(ids): raise HTTPException(400, "One or more device IDs are invalid")
    db.query(UserDeviceAccess).filter_by(user_id=user.id).delete()
    db.add_all([UserDeviceAccess(user_id=user.id, device_id=i) for i in ids])

@router.get("")
def list_users(db: Session = Depends(get_db), _admin=Depends(require_roles("admin"))):
    users = db.query(User).order_by(User.username).all()
    return [{"username": u.username, "role": u.role, "is_active": u.is_active, "must_change_password": u.must_change_password,
             "mfa_enabled": u.mfa_enabled, "device_ids": [g.device_id for g in u.device_access]} for u in users]

@router.get("/audit")
def list_audit(db: Session = Depends(get_db), _admin=Depends(require_roles("admin"))):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [{"actor": row.actor, "action": row.action, "target": row.target, "details": row.details,
             "created_at": row.created_at.isoformat()} for row in rows]

@router.post("")
def create_user(req: UserCreate, db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    if db.query(User).filter_by(username=req.username).first(): raise HTTPException(409, "Username already exists")
    temporary_password = secrets.token_urlsafe(18)
    user = User(username=req.username, role=validate_role(req.role), password_hash=hash_password(temporary_password), must_change_password=True)
    db.add(user); db.flush(); set_grants(db, user, req.device_ids)
    audit(db, admin.username, "user_created", user.username, {"role": user.role, "device_ids": req.device_ids})
    db.commit()
    return {"username": user.username, "temporary_password": temporary_password, "must_change_password": True}

@router.put("/{username}")
def update_user(username: str, req: UserUpdate, db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    user = db.query(User).filter_by(username=username).first()
    if not user: raise HTTPException(404, "User not found")
    role = validate_role(req.role)
    if user.role.lower() == "admin" and (role != "admin" or not req.is_active):
        admins = db.query(User).filter(User.role.ilike("admin"), User.is_active.is_(True)).count()
        if admins <= 1: raise HTTPException(400, "Cannot disable or demote the last active admin")
    user.role = role
    if user.is_active != req.is_active: user.session_version += 1
    user.is_active = req.is_active
    set_grants(db, user, req.device_ids)
    audit(db, admin.username, "user_updated", username, {"role": role, "is_active": req.is_active, "device_ids": req.device_ids})
    db.commit()
    return {"message": "User updated"}

@router.post("/{username}/reset-password")
def reset_password(username: str, db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    user = db.query(User).filter_by(username=username).first()
    if not user: raise HTTPException(404, "User not found")
    temporary_password = secrets.token_urlsafe(18)
    user.password_hash = hash_password(temporary_password); user.must_change_password = True; user.session_version += 1
    audit(db, admin.username, "password_reset", username); db.commit()
    return {"username": username, "temporary_password": temporary_password, "must_change_password": True}

@router.post("/{username}/revoke-sessions")
def revoke_sessions(username: str, db: Session = Depends(get_db), admin=Depends(require_roles("admin"))):
    user = db.query(User).filter_by(username=username).first()
    if not user: raise HTTPException(404, "User not found")
    user.session_version += 1
    audit(db, admin.username, "sessions_revoked", username); db.commit()
    return {"message": "All sessions revoked"}
