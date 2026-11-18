"""
Device endpoints: registration, configuration, live cards, trends, period summaries, baselining, and alarms.
"""
from datetime import datetime, timezone, timedelta
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
    doff_time_min: Optional[float] = None
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
    from app.services.fault_engine import fault_engine
    now_utc = datetime.now(timezone.utc)
    devices = db.query(Device).all() if user.role.lower() == "admin" else db.query(Device).join(UserDeviceAccess).filter(UserDeviceAccess.user_id == user.id).all()
    res = []
    for d in devices:
        effective_status = fault_engine.heal_live_device_status(d, db, now_utc)
        res.append(DeviceResponse(
            device_id=d.device_id,
            alias=d.alias or d.device_id,
            fw_ver=d.fw_ver,
            first_seen=d.first_seen.isoformat() if d.first_seen else None,
            last_seen=d.last_seen.isoformat() if d.last_seen else None,
            status=effective_status,
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
        "doff_time_min": profile.doff_time_min,
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
    # Note: Do not set cleared_at = now. The fault is acknowledged, not cleared.
    # fault_engine automatically sets cleared_at when physical readings return to normal.

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
                    chips[f"{k}_label"] = "Normal"
                dev.status_detail = chips

    db.commit()
    return {"message": "Alert acknowledged and dismissed successfully"}


# ── Smart ROI & Market Intelligence Endpoints ─────────────────────────────────

class SmartRoiCalculateRequest(BaseModel):
    avg_kw: float
    current_eff: float
    candidate_eff: float
    candidate_kw: float
    rated_kw: float
    annual_hours: float
    tariff: float
    motor_investment: float
    installation_cost: float


class SmartRoiAiConsultRequest(BaseModel):
    query: Optional[str] = None
    inputs: Dict[str, Any] = {}
    include_web_search: bool = True


@router.get("/{device_id}/smart-roi")
def get_smart_roi(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Fetch smart ROI context, presets, telemetry facts, and initial calculations."""
    require_device_access(user, device_id, db)
    try:
        from app.services.smart_roi_service import get_smart_roi_context
        return get_smart_roi_context(device_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to calculate smart ROI: {exc}")


@router.post("/{device_id}/smart-roi-calculate")
def recalculate_smart_roi(
    device_id: str,
    req: SmartRoiCalculateRequest,
    user: User = Depends(get_current_user)
):
    """Instantly recalculate ROI metrics based on edited subjective inputs."""
    from app.services.smart_roi_service import calculate_roi_metrics
    return calculate_roi_metrics(
        avg_kw=req.avg_kw,
        current_eff=req.current_eff,
        candidate_eff=req.candidate_eff,
        candidate_kw=req.candidate_kw,
        rated_kw=req.rated_kw,
        annual_hours=req.annual_hours,
        tariff=req.tariff,
        motor_investment=req.motor_investment,
        installation_cost=req.installation_cost
    )


@router.post("/{device_id}/smart-roi-ai")
async def consult_smart_roi_ai(
    device_id: str,
    req: SmartRoiAiConsultRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Run AI executive analysis with web search capability for motor market pricing and payback."""
    require_device_access(user, device_id, db)
    from app.services.smart_roi_service import generate_smart_roi_ai_analysis
    return await generate_smart_roi_ai_analysis(
        device_id=device_id,
        query=req.query,
        inputs=req.inputs,
        include_web_search=req.include_web_search,
        db=db
    )


class RecordManualReadingRequest(BaseModel):
    temperature: float
    rpm: float
    target_time: Optional[str] = None


@router.post("/{device_id}/record-manual")
def record_manual_reading(
    device_id: str,
    payload: RecordManualReadingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Record on-site temperature (°C) and RPM into the database attached to the nearest timestamp row.
    If for a timestamp these values are not recorded, they remain empty (NULL).
    """
    require_device_access(user, device_id, db)

    # 1. Parse target time or default to current UTC
    target_dt = datetime.now(timezone.utc)
    if payload.target_time:
        try:
            t_str = payload.target_time.replace(" ", "+").replace("Z", "+00:00")
            target_dt = datetime.fromisoformat(t_str)
            if target_dt.tzinfo is None:
                target_dt = target_dt.replace(tzinfo=timezone.utc)
        except Exception:
            target_dt = datetime.now(timezone.utc)

    # 2. Find nearest reading row for this device in the dataset
    reading_before = (
        db.query(Reading)
        .filter(Reading.device_id == device_id, Reading.ts <= target_dt)
        .order_by(Reading.ts.desc())
        .first()
    )
    reading_after = (
        db.query(Reading)
        .filter(Reading.device_id == device_id, Reading.ts >= target_dt)
        .order_by(Reading.ts.asc())
        .first()
    )

    nearest: Optional[Reading] = None
    if reading_before and reading_after:
        t_before = reading_before.ts if reading_before.ts.tzinfo else reading_before.ts.replace(tzinfo=timezone.utc)
        t_after = reading_after.ts if reading_after.ts.tzinfo else reading_after.ts.replace(tzinfo=timezone.utc)
        dt_before = abs((target_dt - t_before).total_seconds())
        dt_after = abs((t_after - target_dt).total_seconds())
        nearest = reading_before if dt_before <= dt_after else reading_after
    elif reading_before:
        nearest = reading_before
    elif reading_after:
        nearest = reading_after
    else:
        # Fallback to the latest reading if available
        nearest = (
            db.query(Reading)
            .filter(Reading.device_id == device_id)
            .order_by(Reading.ts.desc())
            .first()
        )

    if not nearest:
        raise HTTPException(
            status_code=404,
            detail="No telemetry dataset rows exist for this device to attach manual readings to."
        )

    # 3. Store temperature and RPM to this nearest row
    nearest.temperature = round(float(payload.temperature), 2)
    nearest.rpm = round(float(payload.rpm), 2)
    db.commit()
    db.refresh(nearest)

    # Format timestamp for display in IST (+05:30)
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ts_aware = nearest.ts if nearest.ts.tzinfo else nearest.ts.replace(tzinfo=timezone.utc)
    ist_str = ts_aware.astimezone(ist_offset).strftime("%d-%b-%Y %I:%M:%S %p IST")

    return {
        "success": True,
        "device_id": device_id,
        "matched_timestamp": nearest.ts.isoformat(),
        "matched_timestamp_ist": ist_str,
        "temperature": nearest.temperature,
        "rpm": nearest.rpm,
        "message": f"Recorded Temperature ({nearest.temperature} °C) and RPM ({int(nearest.rpm) if nearest.rpm.is_integer() else nearest.rpm}) to nearest reading row at {ist_str}."
    }


class MachineScreenOcrRequest(BaseModel):
    image_base64: str
    mime_type: Optional[str] = "image/jpeg"
    target_time: Optional[str] = None


@router.post("/{device_id}/upload-machine-screen")
def upload_machine_screen(
    device_id: str,
    payload: MachineScreenOcrRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Extract machine HMI screen parameters via OpenAI Vision in-memory (no disk storage),
    immediately release image bytes after OCR, populate the nearest timestamp reading row
    at the upload time, and auto-update Machine Details in the device configuration profile.
    """
    import gc
    import json
    import re
    from openai import OpenAI
    from sqlalchemy.orm.attributes import flag_modified
    from app.config import settings
    from app.services.rag_service import build_chat_completion_kwargs

    require_device_access(user, device_id, db)

    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured on the server.")

    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    b64_data: Optional[str] = payload.image_base64 or ""
    if "," in b64_data and b64_data.strip().startswith("data:"):
        b64_data = b64_data.split(",", 1)[1]
    b64_data = b64_data.strip()

    if not b64_data:
        raise HTTPException(status_code=400, detail="Empty image payload.")
    if len(b64_data) > 10 * 1024 * 1024:
        b64_data = None
        gc.collect()
        raise HTTPException(status_code=413, detail="Image is too large. Please upload an image under 6 MB.")

    mime = payload.mime_type or "image/jpeg"
    ocr_json: Dict[str, Any] = {}

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an industrial textile machine HMI OCR assistant. Extract the displayed values from the machine screen image into strict JSON. "
                    "Rules:\n"
                    "1. Never guess or hallucinate unreadable numbers. If a value is blurry, obscured by glare, cut off, or unreadable, set it to null and add its human-readable field name to 'unclear_fields'.\n"
                    "2. If the image is not a machine screen or is too blurry/dark to read core values, set 'is_readable' to false and explain why in 'reason'.\n"
                    "3. Return ONLY valid JSON with these exact keys:\n"
                    "{\n"
                    '  "is_readable": true,\n'
                    '  "confidence": "high",\n'
                    '  "unclear_fields": [],\n'
                    '  "reason": "",\n'
                    '  "machine_make": "string or null (e.g. LMW)",\n'
                    '  "machine_name": "string or null (e.g. RINGFRAME)",\n'
                    '  "machine_model_no": "string or null (e.g. LRJ 60A - M)",\n'
                    '  "shift": "string or null (e.g. Shift - 1)",\n'
                    '  "screen_date": "string or null (e.g. 31/10/2026)",\n'
                    '  "screen_time": "string or null (e.g. 08:35:37)",\n'
                    '  "count_ne": "number or null (value next to Ne)",\n'
                    '  "spindle_rpm": "number or null (high rpm value, typically 5000-25000 rpm)",\n'
                    '  "chase_mm": "number or null (value next to mm)",\n'
                    '  "length_m": "number or null (value next to M)",\n'
                    '  "doff_time_min": "number or null (value next to min)",\n'
                    '  "front_roller_rpm": "number or null (lower rpm value, typically 50-500 rpm)",\n'
                    '  "tpi": "number or null (value next to TPI)",\n'
                    '  "delivery_speed_m_min": "number or null (value next to m/min)",\n'
                    '  "efficiency_pct": "number or null (value next to %)",\n'
                    '  "suction_pressure_mm_wc": "number or null (value next to mm WC)",\n'
                    '  "machine_status": "string or null (e.g. Machine ON)"\n'
                    "}"
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all readings from this machine HMI screen image as JSON."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64_data}", "detail": "high"}}
                ]
            }
        ]
        kwargs = build_chat_completion_kwargs(settings.OPENAI_CHAT_MODEL, messages, max_tokens=700, temperature=0.0)
        resp = client.chat.completions.create(**kwargs)
        raw_text = (resp.choices[0].message.content or "").strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
            raw_text = re.sub(r"\s*```$", "", raw_text)
        ocr_json = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "success": False,
            "needs_reupload": True,
            "reason": "Could not parse clear machine screen readings from the uploaded image. Please re-upload a clearer photo of the machine screen.",
            "unclear_fields": [],
            "extracted": {}
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI Vision OCR failed: {exc}")
    finally:
        # Immediately free image memory; never persist image bytes to disk or DB
        b64_data = None
        payload.image_base64 = ""
        gc.collect()

    def _clean_float(val: Any) -> Optional[float]:
        if val is None or val == "":
            return None
        try:
            f = float(val)
            return round(f, 2)
        except (ValueError, TypeError):
            return None

    def _clean_str(val: Any) -> Optional[str]:
        if val is None:
            return None
        s = str(val).strip()
        return s if s and s.lower() != "null" else None

    is_readable = bool(ocr_json.get("is_readable", True))
    confidence = str(ocr_json.get("confidence", "high")).lower()
    unclear_raw = ocr_json.get("unclear_fields") or []
    unclear_fields = [str(u).strip() for u in unclear_raw if str(u).strip()]
    reason = _clean_str(ocr_json.get("reason")) or ""

    screen_record: Dict[str, Any] = {
        "machine_make": _clean_str(ocr_json.get("machine_make")),
        "machine_name": _clean_str(ocr_json.get("machine_name")),
        "machine_model_no": _clean_str(ocr_json.get("machine_model_no")),
        "shift": _clean_str(ocr_json.get("shift")),
        "screen_date": _clean_str(ocr_json.get("screen_date")),
        "screen_time": _clean_str(ocr_json.get("screen_time")),
        "count_ne": _clean_float(ocr_json.get("count_ne")),
        "spindle_rpm": _clean_float(ocr_json.get("spindle_rpm")),
        "chase_mm": _clean_float(ocr_json.get("chase_mm")),
        "length_m": _clean_float(ocr_json.get("length_m")),
        "doff_time_min": _clean_float(ocr_json.get("doff_time_min")),
        "front_roller_rpm": _clean_float(ocr_json.get("front_roller_rpm")),
        "tpi": _clean_float(ocr_json.get("tpi")),
        "delivery_speed_m_min": _clean_float(ocr_json.get("delivery_speed_m_min")),
        "efficiency_pct": _clean_float(ocr_json.get("efficiency_pct")),
        "suction_pressure_mm_wc": _clean_float(ocr_json.get("suction_pressure_mm_wc")),
        "machine_status": _clean_str(ocr_json.get("machine_status")),
    }

    # Ensure any field explicitly flagged as unclear is kept None (empty)
    unclear_norm = {u.lower().replace(" ", "_") for u in unclear_fields}
    for k in list(screen_record.keys()):
        if k in unclear_norm:
            screen_record[k] = None

    numeric_keys = [
        "count_ne", "spindle_rpm", "chase_mm", "length_m", "doff_time_min",
        "front_roller_rpm", "tpi", "delivery_speed_m_min", "efficiency_pct", "suction_pressure_mm_wc"
    ]
    extracted_numeric_count = sum(1 for k in numeric_keys if screen_record.get(k) is not None)
    extracted_any_count = sum(1 for v in screen_record.values() if v is not None)

    if not is_readable or (extracted_numeric_count == 0 and extracted_any_count == 0):
        return {
            "success": False,
            "needs_reupload": True,
            "reason": reason or "The uploaded image is unclear or does not show a readable machine screen. Please upload a clearer photo.",
            "unclear_fields": unclear_fields,
            "extracted": {}
        }

    # 1. Auto-populate Machine Details in DeviceProfile (Configuration & Report)
    profile = device.profile
    if not profile:
        profile = DeviceProfile(device_id=device_id)
        db.add(profile)

    updated_profile_fields: Dict[str, Any] = {}
    if screen_record["machine_make"]:
        profile.machine_make = screen_record["machine_make"]
        updated_profile_fields["machine_make"] = profile.machine_make
    if screen_record["machine_name"]:
        profile.machine_name = screen_record["machine_name"]
        updated_profile_fields["machine_name"] = profile.machine_name
    if screen_record["machine_model_no"]:
        profile.machine_model_no = screen_record["machine_model_no"]
        updated_profile_fields["machine_model_no"] = profile.machine_model_no
    if screen_record["count_ne"] is not None:
        c_val = screen_record["count_ne"]
        c_str = f"{int(c_val)}s Ne" if float(c_val).is_integer() else f"{c_val} Ne"
        profile.machine_count = c_str
        updated_profile_fields["machine_count"] = profile.machine_count
    if screen_record["tpi"] is not None:
        profile.machine_tpi = str(screen_record["tpi"])
        updated_profile_fields["machine_tpi"] = profile.machine_tpi
    if screen_record["spindle_rpm"] is not None:
        s_rpm = float(screen_record["spindle_rpm"])
        profile.machine_rpm_avg = s_rpm
        updated_profile_fields["machine_rpm_avg"] = s_rpm
        if profile.machine_rpm_max is None or s_rpm > profile.machine_rpm_max:
            profile.machine_rpm_max = s_rpm
            updated_profile_fields["machine_rpm_max"] = s_rpm
    if screen_record["doff_time_min"] is not None:
        profile.doff_time_min = float(screen_record["doff_time_min"])
        updated_profile_fields["doff_time_min"] = profile.doff_time_min

    # 2. Match upload timestamp to nearest Reading row and attach screen_record ONLY to that row
    upload_dt = datetime.now(timezone.utc)
    if payload.target_time:
        try:
            t_str = payload.target_time.replace(" ", "+").replace("Z", "+00:00")
            parsed_dt = datetime.fromisoformat(t_str)
            if parsed_dt.tzinfo is None:
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            upload_dt = parsed_dt
        except Exception:
            upload_dt = datetime.now(timezone.utc)

    reading_before = (
        db.query(Reading)
        .filter(Reading.device_id == device_id, Reading.ts <= upload_dt)
        .order_by(Reading.ts.desc())
        .first()
    )
    reading_after = (
        db.query(Reading)
        .filter(Reading.device_id == device_id, Reading.ts >= upload_dt)
        .order_by(Reading.ts.asc())
        .first()
    )

    nearest: Optional[Reading] = None
    if reading_before and reading_after:
        t_before = reading_before.ts if reading_before.ts.tzinfo else reading_before.ts.replace(tzinfo=timezone.utc)
        t_after = reading_after.ts if reading_after.ts.tzinfo else reading_after.ts.replace(tzinfo=timezone.utc)
        dt_before = abs((upload_dt - t_before).total_seconds())
        dt_after = abs((t_after - upload_dt).total_seconds())
        nearest = reading_before if dt_before <= dt_after else reading_after
    elif reading_before:
        nearest = reading_before
    elif reading_after:
        nearest = reading_after
    else:
        nearest = (
            db.query(Reading)
            .filter(Reading.device_id == device_id)
            .order_by(Reading.ts.desc())
            .first()
        )

    matched_iso = upload_dt.isoformat()
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    ist_str = upload_dt.astimezone(ist_offset).strftime("%d-%b-%Y %I:%M:%S %p IST")
    screen_record["uploaded_at"] = matched_iso

    # If the closest telemetry reading is within 90 seconds of the upload time (device is live),
    # attach to that row; otherwise (e.g. device is currently OFF), insert a row at upload_dt
    # so the OCR reading is recorded at the exact upload timestamp instead of an old offline row.
    use_nearest = False
    if nearest:
        ts_aware = nearest.ts if nearest.ts.tzinfo else nearest.ts.replace(tzinfo=timezone.utc)
        if abs((upload_dt - ts_aware).total_seconds()) <= 90:
            use_nearest = True

    if use_nearest and nearest:
        raw_copy = dict(nearest.raw) if isinstance(nearest.raw, dict) else {}
        raw_copy["machine_screen"] = screen_record
        nearest.raw = raw_copy
        flag_modified(nearest, "raw")
        ts_aware = nearest.ts if nearest.ts.tzinfo else nearest.ts.replace(tzinfo=timezone.utc)
        matched_iso = ts_aware.isoformat()
        ist_str = ts_aware.astimezone(ist_offset).strftime("%d-%b-%Y %I:%M:%S %p IST")
    else:
        new_reading = Reading(
            device_id=device_id,
            ts=upload_dt,
            received_at=upload_dt,
            fw_ver=device.fw_ver,
            raw={"machine_screen": screen_record}
        )
        db.add(new_reading)

    db.commit()

    needs_reupload = len(unclear_fields) > 0 or confidence == "low"
    summary_parts = []
    if screen_record.get("machine_make") or screen_record.get("machine_model_no"):
        summary_parts.append(" ".join(filter(None, [screen_record.get("machine_make"), screen_record.get("machine_name"), screen_record.get("machine_model_no")])))
    if screen_record.get("count_ne") is not None:
        summary_parts.append(f"{screen_record['count_ne']} Ne")
    if screen_record.get("spindle_rpm") is not None:
        summary_parts.append(f"{int(screen_record['spindle_rpm'])} RPM")
    if screen_record.get("tpi") is not None:
        summary_parts.append(f"TPI {screen_record['tpi']}")
    if screen_record.get("doff_time_min") is not None:
        summary_parts.append(f"Doff {int(screen_record['doff_time_min'])} min")

    msg = f"Extracted machine screen data ({', '.join(summary_parts)})"
    if ist_str:
        msg += f" and recorded onto row at {ist_str}."
    else:
        msg += " and updated Machine Details configuration."

    return {
        "success": True,
        "partial": len(unclear_fields) > 0,
        "needs_reupload": needs_reupload,
        "confidence": confidence,
        "unclear_fields": unclear_fields,
        "reason": reason,
        "device_id": device_id,
        "matched_timestamp": matched_iso,
        "matched_timestamp_ist": ist_str,
        "extracted": screen_record,
        "profile_updated": updated_profile_fields,
        "message": msg
    }


