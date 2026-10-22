"""
Device endpoints: registration, configuration, live cards, trends, period summaries, baselining, and alarms.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.session import get_db
from app.db.models import Device, DeviceProfile, DeviceBaseline, Reading, Alert, User, UserDeviceAccess
from app.api.auth import get_current_user, require_roles, can_access_device, require_device_access
from app.services.query_service import query_service

router = APIRouter(prefix="/api/devices", tags=["devices"])


class DeviceResponse(BaseModel):
    device_id: str
    alias: Optional[str]
    fw_ver: Optional[str]
    first_seen: Optional[str]
    last_seen: Optional[str]
    status: str
    status_detail: Dict[str, Any]
    configured: bool


class ProfileUpdateRequest(BaseModel):
    alias: Optional[str] = None
    nominal_voltage: Optional[float] = 240.0
    ct_rated_current: Optional[float] = 100.0
    customer_name: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    contact_person: Optional[str] = None
    contact_number: Optional[str] = None
    motor_make: Optional[str] = None
    motor_rating_kw: Optional[float] = None
    frame_size: Optional[str] = None
    rated_current_amps: Optional[float] = None
    rated_speed_rpm: Optional[float] = None
    rated_voltage: Optional[float] = None
    rated_efficiency_pct: Optional[float] = None
    motor_connection: Optional[str] = None
    motor_duty: Optional[str] = None
    insulation_class: Optional[str] = None
    motor_type: Optional[str] = None
    serial_number: Optional[str] = None
    machine_name: Optional[str] = None
    machine_make: Optional[str] = None
    machine_model_no: Optional[str] = None
    machine_count: Optional[str] = None
    machine_tpi: Optional[str] = None
    raw_material: Optional[str] = None
    machine_rpm_max: Optional[float] = None
    machine_rpm_avg: Optional[float] = None
    no_of_spindles: Optional[int] = None
    inverter_make: Optional[str] = None
    inverter_model: Optional[str] = None
    rep_name: Optional[str] = None
    rep_designation: Optional[str] = None
    rep_contact_number: Optional[str] = None
    rep_email: Optional[str] = None
    signatory_customer_name: Optional[str] = None
    signatory_designation: Optional[str] = None
    electricity_tariff: Optional[float] = None
    annual_operating_hours: Optional[float] = None
    motor_investment: Optional[float] = 0.0
    installation_cost: Optional[float] = 0.0
    replacement_motor_rating_kw: Optional[float] = None
    replacement_motor_efficiency_pct: Optional[float] = None
    idle_threshold_kw: Optional[float] = None
    thresholds: Optional[Dict[str, Any]] = None
    email_alerts_enabled: Optional[bool] = False
    alert_email: Optional[str] = None


class DeviceRegisterRequest(BaseModel):
    device_id: str
    alias: str


@router.get("", response_model=List[DeviceResponse])
def list_devices(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """List all registered devices with their current health status."""
    devices = db.query(Device).all() if user.role.lower() == "admin" else db.query(Device).join(UserDeviceAccess).filter(UserDeviceAccess.user_id == user.id).all()
    res = []
    for d in devices:
        res.append(DeviceResponse(
            device_id=d.device_id,
            alias=d.alias or d.device_id,
            fw_ver=d.fw_ver,
            first_seen=d.first_seen.isoformat() if d.first_seen else None,
            last_seen=d.last_seen.isoformat() if d.last_seen else None,
            status=d.status,
            status_detail=d.status_detail or {},
            configured=d.configured
        ))
    return res


@router.post("/register")
def register_device(
    req: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin"))
):
    """
    Manually register a new device by its hardware dID.
    The device must be registered before its MQTT telemetry is accepted.
    """
    device_id = req.device_id.strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="Device ID cannot be empty")

    existing = db.query(Device).filter(Device.device_id == device_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Device '{device_id}' is already registered as '{existing.alias}'")

    device = Device(
        device_id=device_id,
        alias=req.alias.strip() or f"Meter-{device_id[-6:]}",
        status="New \u2013 not configured",
        status_detail={
            "ct_l1": "Normal", "ct_l2": "Normal", "ct_l3": "Normal",
            "vclip_l1": "Normal", "vclip_l2": "Normal", "vclip_l3": "Normal"
        },
        configured=False
    )
    db.add(device)
    db.flush()

    profile = DeviceProfile(
        device_id=device_id,
        nominal_voltage=240.0,
        ct_rated_current=100.0,
        thresholds={
            "active_current_a": 1.0,
            "debounce_raise_count": 3,
            "debounce_clear_count": 3,
            "v_min_present": 50.0,
            "i_min_present": 0.05,
            "ct_swap_pf_diff": 0.25,
            "v_line_tol_pct": 6.0,
            "v_nom_min_pct": 80.0,
            "v_nom_max_pct": 120.0,
            "tolerance_pct": 30.0
        }
    )
    db.add(profile)
    db.commit()

    return {
        "message": f"Device '{device_id}' registered successfully as '{device.alias}'",
        "device_id": device_id,
        "alias": device.alias
    }


@router.delete("/{device_id}")
def delete_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin"))
):
    """Remove a registered device and all its data."""
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()
    return {"message": f"Device '{device_id}' deleted successfully"}


@router.get("/{device_id}/profile")
def get_device_profile(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Fetch configuration profile for a device."""
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    profile = device.profile
    if not profile:
        raise HTTPException(status_code=404, detail="Device profile not found")

    return {
        "device_id": device.device_id,
        "alias": device.alias,
        "fw_ver": device.fw_ver,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "expected_interval_s": device.expected_interval_s,
        "configured": device.configured,
        "nominal_voltage": profile.nominal_voltage,
        "ct_rated_current": profile.ct_rated_current,
        "customer_name": profile.customer_name,
        "location": profile.location,
        "department": profile.department,
        "contact_person": profile.contact_person,
        "contact_number": profile.contact_number,
        "motor_make": profile.motor_make,
        "motor_rating_kw": profile.motor_rating_kw,
        "frame_size": profile.frame_size,
        "rated_current_amps": profile.rated_current_amps,
        "rated_speed_rpm": profile.rated_speed_rpm,
        "rated_voltage": profile.rated_voltage,
        "rated_efficiency_pct": profile.rated_efficiency_pct,
        "motor_connection": profile.motor_connection,
        "motor_duty": profile.motor_duty,
        "insulation_class": profile.insulation_class,
        "motor_type": profile.motor_type,
        "serial_number": profile.serial_number,
        "machine_name": profile.machine_name,
        "machine_make": profile.machine_make,
        "machine_model_no": profile.machine_model_no,
        "machine_count": profile.machine_count,
        "machine_tpi": profile.machine_tpi,
        "raw_material": profile.raw_material,
        "machine_rpm_max": profile.machine_rpm_max,
        "machine_rpm_avg": profile.machine_rpm_avg,
        "no_of_spindles": profile.no_of_spindles,
        "inverter_make": profile.inverter_make,
        "inverter_model": profile.inverter_model,
        "rep_name": profile.rep_name,
        "rep_designation": profile.rep_designation,
        "rep_contact_number": profile.rep_contact_number,
        "rep_email": profile.rep_email,
        "signatory_customer_name": profile.signatory_customer_name,
        "signatory_designation": profile.signatory_designation,
        "electricity_tariff": profile.electricity_tariff,
        "annual_operating_hours": profile.annual_operating_hours,
        "motor_investment": profile.motor_investment,
        "installation_cost": profile.installation_cost,
        "replacement_motor_rating_kw": profile.replacement_motor_rating_kw,
        "replacement_motor_efficiency_pct": profile.replacement_motor_efficiency_pct,
        "idle_threshold_kw": profile.idle_threshold_kw,
        "thresholds": profile.thresholds or {},
        "email_alerts_enabled": profile.email_alerts_enabled,
        "alert_email": profile.alert_email
    }


@router.put("/{device_id}/profile")
def update_device_profile(
    device_id: str,
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin"))
):
    """Save updated device profile and mark device as configured."""
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if req.alias is not None:
        device.alias = req.alias
    device.configured = True
    if device.status == "New – not configured":
        device.status = "Normal"

    profile = device.profile
    if not profile:
        profile = DeviceProfile(device_id=device_id)
        db.add(profile)

    # Update fields
    update_data = req.model_dump(exclude_unset=True)
    if "alias" in update_data:
        del update_data["alias"]

    for k, v in update_data.items():
        setattr(profile, k, v)

    if profile.rated_efficiency_pct is None or not (0 < profile.rated_efficiency_pct <= 100):
        raise HTTPException(status_code=422, detail="Rated motor efficiency from the nameplate is required (greater than 0 and up to 100%).")
    replacement_efficiency = profile.replacement_motor_efficiency_pct
    if replacement_efficiency is not None and not (0 < replacement_efficiency <= 100):
        raise HTTPException(status_code=422, detail="Replacement motor efficiency must be greater than 0 and up to 100%.")

    profile.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Configuration saved successfully"}


@router.post("/{device_id}/mark-baseline")
def mark_installation_ok(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin"))
):
    """
    Capture installation baseline while motor is running.
    Stores per-phase current share and per-phase PF to detect future CT position changes.
    """
    require_device_access(user, device_id, db)
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    latest = (
        db.query(Reading)
        .filter(Reading.device_id == device_id)
        .order_by(desc(Reading.ts))
        .first()
    )
    if not latest or latest.i1 is None or latest.i2 is None or latest.i3 is None:
        raise HTTPException(status_code=400, detail="Cannot establish baseline: no active telemetry found")

    total_i = latest.i1 + latest.i2 + latest.i3
    if total_i < 3.0:
        raise HTTPException(status_code=400, detail="Motor must be running with active load to capture baseline")

    shares = {
        "i1_share": round(latest.i1 / total_i, 3),
        "i2_share": round(latest.i2 / total_i, 3),
        "i3_share": round(latest.i3 / total_i, 3)
    }
    pfs = {
        "pf1": round(latest.pf1 or 0.8, 3),
        "pf2": round(latest.pf2 or 0.8, 3),
        "pf3": round(latest.pf3 or 0.8, 3)
    }

    baseline = device.baseline
    if not baseline:
        baseline = DeviceBaseline(
            device_id=device_id,
            captured_at=datetime.now(timezone.utc),
            per_phase_current_share=shares,
            per_phase_pf=pfs,
            tolerance_pct=30.0
        )
        db.add(baseline)
    else:
        baseline.captured_at = datetime.now(timezone.utc)
        baseline.per_phase_current_share = shares
        baseline.per_phase_pf = pfs
        baseline.tolerance_pct = 30.0

    db.commit()
    return {
        "message": "Installation baseline established successfully",
        "captured_at": baseline.captured_at.isoformat(),
        "current_shares": shares,
        "power_factors": pfs
    }


@router.get("/{device_id}/live")
def get_live_data(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Fetch live data for the 6 cards and status banner."""
    require_device_access(user, device_id, db)
    return query_service.get_live_cards(device_id, db)


@router.get("/{device_id}/trends")
def get_trends(
    device_id: str,
    start_time: str = Query(...),
    end_time: str = Query(...),
    interval: str = Query("1-minute"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Fetch trend series for selected date range and interval."""
    require_device_access(user, device_id, db)
    try:
        s_clean = start_time.replace(" ", "+").replace("Z", "+00:00")
        e_clean = end_time.replace(" ", "+").replace("Z", "+00:00")
        t_start = datetime.fromisoformat(s_clean)
        t_end = datetime.fromisoformat(e_clean)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ISO timestamp format")

    return query_service.get_trend_charts(device_id, t_start, t_end, interval, db)


@router.get("/{device_id}/summary")
def get_summary(
    device_id: str,
    start_time: str = Query(...),
    end_time: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Fetch period summary strip for selected date range."""
    require_device_access(user, device_id, db)
    try:
        s_clean = start_time.replace(" ", "+").replace("Z", "+00:00")
        e_clean = end_time.replace(" ", "+").replace("Z", "+00:00")
        t_start = datetime.fromisoformat(s_clean)
        t_end = datetime.fromisoformat(e_clean)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ISO timestamp format")

    return query_service.get_period_summary(device_id, t_start, t_end, db)


@router.post("/{device_id}/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    device_id: str,
    alert_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst"))
):
    """Acknowledge an active open alert."""
    require_device_access(user, device_id, db)
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.device_id == device_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    now = datetime.now(timezone.utc)
    alert.acknowledged_by = user.username
    alert.acknowledged_at = now
    alert.cleared_at = now

    # If no other unacknowledged alerts remain, reset device status to Normal
    remaining = (
        db.query(Alert)
        .filter(
            Alert.device_id == device_id,
            Alert.cleared_at.is_(None),
            Alert.acknowledged_at.is_(None)
        )
        .count()
    )
    if remaining == 0:
        dev = db.query(Device).filter(Device.device_id == device_id).first()
        if dev:
            dev.status = "Normal"
            if dev.status_detail:
                chips = dict(dev.status_detail)
                for k in ["ct_l1", "ct_l2", "ct_l3", "vclip_l1", "vclip_l2", "vclip_l3"]:
                    chips[k] = "Normal"
                    chips[f"{k}_detail"] = "Normal"
                dev.status_detail = chips

    db.commit()
    return {"message": "Alert acknowledged and dismissed successfully"}
