"""
Power Study management endpoints.
Handles server-synchronized start/stop power studies per device, sequential unique code generation
(LEDL0001...), customer name attribution, and separate archive DB persistence on admin delete.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.auth import can_access_device, get_current_user, require_device_access, require_roles
from app.config import settings
from app.db.models import Device, DeviceProfile, PowerStudy, User, UserDeviceAccess
from app.db.session import get_db
from app.services.query_service import query_service

router = APIRouter(tags=["studies"])


class StartPowerStudyRequest(BaseModel):
    customer_name: Optional[str] = None


class StopPowerStudyRequest(BaseModel):
    customer_name: Optional[str] = None


class UpdatePowerStudyRequest(BaseModel):
    customer_name: str


def _get_archive_db_path() -> Path:
    env_override = os.environ.get("DELETED_STUDIES_ARCHIVE_DB_PATH")
    if env_override:
        path = Path(env_override)
    else:
        path = Path(settings.REPORTS_DIR).parent / "deleted_power_studies_archive.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _init_archive_db() -> Path:
    db_path = _get_archive_db_path()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deleted_power_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_code TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                device_id TEXT NOT NULL,
                device_alias TEXT,
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                duration_seconds INTEGER,
                duration_str TEXT,
                energy_kwh REAL,
                running_hours REAL,
                avg_kw REAL,
                kwh_per_running_hour REAL,
                started_by TEXT,
                stopped_by TEXT,
                deleted_by TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                payload_json TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _format_duration_str(duration_seconds: Optional[int]) -> str:
    if duration_seconds is None or duration_seconds < 0:
        return "0s"
    hrs = duration_seconds // 3600
    mins = (duration_seconds % 3600) // 60
    secs = duration_seconds % 60
    if hrs > 0:
        return f"{hrs}h {mins}m {secs}s"
    if mins > 0:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _next_study_code(db: Session) -> str:
    max_seq = 0
    pattern = re.compile(r"^LEDL(\d+)$", re.IGNORECASE)

    for (code,) in db.query(PowerStudy.study_code).all():
        if code:
            m = pattern.match(code.strip())
            if m:
                max_seq = max(max_seq, int(m.group(1)))

    try:
        archive_path = _init_archive_db()
        conn = sqlite3.connect(str(archive_path))
        try:
            cur = conn.cursor()
            cur.execute("SELECT study_code FROM deleted_power_studies")
            for (code,) in cur.fetchall():
                if code:
                    m = pattern.match(str(code).strip())
                    if m:
                        max_seq = max(max_seq, int(m.group(1)))
        finally:
            conn.close()
    except Exception:
        pass

    return f"LEDL{max_seq + 1:04d}"


def _serialize_study(study: PowerStudy, device_alias: Optional[str] = None) -> Dict[str, Any]:
    started_dt = study.started_at
    if started_dt and started_dt.tzinfo is None:
        started_dt = started_dt.replace(tzinfo=timezone.utc)
    stopped_dt = study.stopped_at
    if stopped_dt and stopped_dt.tzinfo is None:
        stopped_dt = stopped_dt.replace(tzinfo=timezone.utc)
    updated_dt = study.updated_at
    if updated_dt and updated_dt.tzinfo is None:
        updated_dt = updated_dt.replace(tzinfo=timezone.utc)

    duration_sec = study.duration_seconds
    if duration_sec is None and started_dt:
        end_ref = stopped_dt or datetime.now(timezone.utc)
        duration_sec = max(0, int((end_ref - started_dt).total_seconds()))

    cust = (study.customer_name or "").strip()
    display_label = f"{study.study_code} — {cust}" if cust else study.study_code

    return {
        "id": study.id,
        "study_code": study.study_code,
        "device_id": study.device_id,
        "device_alias": device_alias or (study.device.alias if study.device else study.device_id),
        "customer_name": cust,
        "display_label": display_label,
        "status": study.status,
        "started_at": started_dt.isoformat() if started_dt else None,
        "stopped_at": stopped_dt.isoformat() if stopped_dt else None,
        "updated_at": updated_dt.isoformat() if updated_dt else (started_dt.isoformat() if started_dt else None),
        "duration_seconds": duration_sec,
        "duration_str": _format_duration_str(duration_sec),
        "energy_kwh": study.energy_kwh,
        "running_hours": study.running_hours,
        "avg_kw": study.avg_kw,
        "kwh_per_running_hour": study.kwh_per_running_hour,
        "started_by": study.started_by,
        "stopped_by": study.stopped_by,
    }


@router.post("/api/devices/{device_id}/studies/start")
def start_device_power_study(
    device_id: str,
    payload: StartPowerStudyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Start a new power study on a device.
    Enforces at most one running study per device across all logins/users.
    """
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    running = (
        db.query(PowerStudy)
        .filter(PowerStudy.device_id == device_id, PowerStudy.status == "running")
        .first()
    )
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"Power study {running.study_code} is already running on this device.",
        )

    profile = device.profile
    if not profile:
        profile = DeviceProfile(device_id=device_id)
        db.add(profile)
        db.flush()

    customer_name = (payload.customer_name or "").strip()
    if customer_name:
        profile.customer_name = customer_name
    else:
        customer_name = (profile.customer_name or "").strip()

    now_utc = datetime.now(timezone.utc)
    study_code = _next_study_code(db)
    study = PowerStudy(
        study_code=study_code,
        device_id=device_id,
        customer_name=customer_name,
        status="running",
        started_at=now_utc,
        stopped_at=None,
        started_by=user.username,
        created_at=now_utc,
        updated_at=now_utc,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return _serialize_study(study, device.alias)


@router.post("/api/devices/{device_id}/studies/stop")
def stop_device_power_study(
    device_id: str,
    payload: Optional[StopPowerStudyRequest] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stop the currently running power study for a device and persist its energy summary."""
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    running = (
        db.query(PowerStudy)
        .filter(PowerStudy.device_id == device_id, PowerStudy.status == "running")
        .order_by(desc(PowerStudy.started_at))
        .first()
    )
    if not running:
        raise HTTPException(status_code=404, detail="No running power study found for this device.")

    now_utc = datetime.now(timezone.utc)
    started_dt = running.started_at
    if started_dt.tzinfo is None:
        started_dt = started_dt.replace(tzinfo=timezone.utc)
    if now_utc <= started_dt:
        now_utc = started_dt

    if payload and payload.customer_name is not None and payload.customer_name.strip():
        running.customer_name = payload.customer_name.strip()
        if device.profile:
            device.profile.customer_name = running.customer_name

    duration_sec = max(0, int((now_utc - started_dt).total_seconds()))
    summary = query_service.get_period_summary(device_id, started_dt, now_utc, db)
    energy_kwh = float(summary.get("energy_kwh") or 0.0)
    running_hrs = float(summary.get("running_hours") or 0.0)
    duration_hrs = float(summary.get("duration_hours") or 0.0)
    avg_kw = float(summary.get("avg_kw") or 0.0)

    kwh_hr: Optional[float] = None
    if running_hrs > 0 and energy_kwh > 0:
        kwh_hr = round(energy_kwh / running_hrs, 3)
    elif duration_hrs > 0 and energy_kwh > 0:
        kwh_hr = round(energy_kwh / duration_hrs, 3)
    elif avg_kw > 0:
        kwh_hr = round(avg_kw, 3)

    running.status = "completed"
    running.stopped_at = now_utc
    running.updated_at = now_utc
    running.stopped_by = user.username
    running.duration_seconds = duration_sec
    running.energy_kwh = round(energy_kwh, 3)
    running.running_hours = round(running_hrs, 3)
    running.avg_kw = round(avg_kw, 3)
    running.kwh_per_running_hour = kwh_hr
    running.summary_snapshot = {
        "energy_kwh": running.energy_kwh,
        "running_hours": running.running_hours,
        "avg_kw": running.avg_kw,
        "kwh_per_running_hour": running.kwh_per_running_hour,
        "samples_count": summary.get("samples_count", 0),
    }

    db.commit()
    db.refresh(running)
    return _serialize_study(running, device.alias)


@router.get("/api/devices/{device_id}/studies/active")
def get_active_device_power_study(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Return the currently running study for this device (across all login sessions),
    or the most recently completed study if none is running.
    """
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    alias = device.alias if device else device_id

    running = (
        db.query(PowerStudy)
        .filter(PowerStudy.device_id == device_id, PowerStudy.status == "running")
        .order_by(desc(PowerStudy.started_at))
        .first()
    )
    if running:
        return _serialize_study(running, alias)

    latest = (
        db.query(PowerStudy)
        .filter(PowerStudy.device_id == device_id)
        .order_by(desc(PowerStudy.id))
        .first()
    )
    if latest:
        return _serialize_study(latest, alias)
    return None


@router.get("/api/devices/{device_id}/studies")
def list_device_power_studies(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all power studies recorded for a specific device."""
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    alias = device.alias if device else device_id
    studies = (
        db.query(PowerStudy)
        .filter(PowerStudy.device_id == device_id)
        .order_by(desc(PowerStudy.id))
        .all()
    )
    return [_serialize_study(s, alias) for s in studies]


@router.get("/api/studies")
def list_all_power_studies(
    status: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List recorded power studies across all devices accessible to the user."""
    q = db.query(PowerStudy)
    if user.role.lower() != "admin":
        accessible_ids = [
            row.device_id
            for row in db.query(UserDeviceAccess.device_id).filter(UserDeviceAccess.user_id == user.id).all()
        ]
        if not accessible_ids:
            return []
        q = q.filter(PowerStudy.device_id.in_(accessible_ids))

    if device_id:
        q = q.filter(PowerStudy.device_id == device_id)
    if status:
        q = q.filter(PowerStudy.status == status)

    studies = q.order_by(desc(PowerStudy.id)).all()
    return [_serialize_study(s) for s in studies]


@router.patch("/api/studies/{study_id}")
def update_power_study_customer(
    study_id: int,
    payload: UpdatePowerStudyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update the customer name on an active or completed power study."""
    study = db.query(PowerStudy).filter(PowerStudy.id == study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Power study not found")
    require_device_access(user, study.device_id, db)
    study.customer_name = payload.customer_name.strip()
    study.updated_at = datetime.now(timezone.utc)
    if study.device and study.device.profile and study.customer_name:
        study.device.profile.customer_name = study.customer_name
    db.commit()
    db.refresh(study)
    return _serialize_study(study)


@router.delete("/api/studies/{study_id}")
def delete_power_study(
    study_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    """
    Delete a power study from the active database (admin only), while archiving
    its code, customer name, timestamps, duration, and metrics in a separate backend database.
    """
    study = db.query(PowerStudy).filter(PowerStudy.id == study_id).first()
    if not study:
        raise HTTPException(status_code=404, detail="Power study not found")
    require_device_access(user, study.device_id, db)

    serialized = _serialize_study(study)
    deleted_at_iso = datetime.now(timezone.utc).isoformat()

    archive_path = _init_archive_db()
    conn = sqlite3.connect(str(archive_path))
    try:
        conn.execute(
            """
            INSERT INTO deleted_power_studies (
                study_code, customer_name, device_id, device_alias,
                started_at, stopped_at, duration_seconds, duration_str,
                energy_kwh, running_hours, avg_kw, kwh_per_running_hour,
                started_by, stopped_by, deleted_by, deleted_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                serialized["study_code"],
                serialized["customer_name"],
                serialized["device_id"],
                serialized["device_alias"],
                serialized["started_at"] or "",
                serialized["stopped_at"],
                serialized["duration_seconds"],
                serialized["duration_str"],
                serialized["energy_kwh"],
                serialized["running_hours"],
                serialized["avg_kw"],
                serialized["kwh_per_running_hour"],
                serialized["started_by"],
                serialized["stopped_by"],
                user.username,
                deleted_at_iso,
                json.dumps(serialized),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    study_code = study.study_code
    db.delete(study)
    db.commit()

    return {
        "success": True,
        "deleted_id": study_id,
        "study_code": study_code,
        "archived": True,
    }


@router.get("/api/studies/deleted-archive")
def list_deleted_studies_archive(
    user: User = Depends(require_roles("admin")),
):
    """Retrieve deleted power studies from the separate backend archive database (admin only)."""
    archive_path = _init_archive_db()
    conn = sqlite3.connect(str(archive_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM deleted_power_studies ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
