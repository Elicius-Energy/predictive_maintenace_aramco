"""
REST endpoints for historical data and machine metadata.
"""
import re
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import io
import csv
import json
from datetime import datetime, timedelta, timezone
from app.database import db
from app.models import MachineInfo, MachineStatus
from app.auth import get_current_user

router = APIRouter(prefix="/data", tags=["data"])

# Dependency to validate and sanitize machine_id input
def validate_machine_id(machine_id: str) -> str:
    # Only allow alphanumeric, hyphen, and underscore
    if not re.match(r"^[a-zA-Z0-9_-]+$", machine_id):
        raise HTTPException(status_code=400, detail="Invalid machine_id format")
    return machine_id

def sanitize_csv_cell(value: Any) -> Any:
    """Prevent CSV injection attacks by prefixing dangerous starting chars with a single quote."""
    if isinstance(value, str) and value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{value}"
    return value

@router.get("/history")
async def get_history(
    machine_id: str = Query("sim-pump-001", description="ID of the machine"),
    minutes: int = Query(10, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get historical sensor readings."""
    safe_id = validate_machine_id(machine_id)
    return db.get_readings(safe_id, minutes, start_time=start_time, end_time=end_time)

@router.get("/features")
async def get_features(
    machine_id: str = Query("sim-pump-001", description="ID of the machine"),
    minutes: int = Query(10, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get historical computed features."""
    safe_id = validate_machine_id(machine_id)
    return db.get_features(safe_id, minutes, start_time=start_time, end_time=end_time)

@router.get("/alerts")
async def get_alerts(
    machine_id: str = Query("sim-pump-001", description="ID of the machine"),
    minutes: int = Query(60, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get historical alerts."""
    safe_id = validate_machine_id(machine_id)
    return db.get_alerts(safe_id, minutes, start_time=start_time, end_time=end_time)

@router.get("/download_csv")
async def download_csv(
    machine_id: str = Query("sim-pump-001", description="ID of the machine"),
    minutes: int = Query(60, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Download historical data as CSV with full 3-phase parameters from features table."""
    safe_id = validate_machine_id(machine_id)
    
    def csv_generator():
        if start_time and end_time:
            since = start_time
            until = end_time
        else:
            since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
            until = datetime.now(timezone.utc).isoformat()
            
        with db._get_conn() as conn:
            # Query features table which contains the full 3-phase data as JSON
            cursor = conn.execute("""
                SELECT timestamp, machine_id, feature_data
                FROM features
                WHERE machine_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (safe_id, since, until))
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write comprehensive headers including per-phase data
            headers = [
                "timestamp", "machine_id",
                # Per-phase voltages (L-N)
                "v1n", "v2n", "v3n", "vln_avg",
                # Line-to-line voltages
                "v12", "v23", "v31", "vll_avg",
                # Per-phase currents
                "i1", "i2", "i3", "i_avg",
                # Per-phase active power (kW)
                "kw1", "kw2", "kw3", "t_kw",
                # Per-phase reactive power (kVAR)
                "kvar1", "kvar2", "kvar3", "t_kvar",
                # Per-phase apparent power (kVA)
                "kva1", "kva2", "kva3", "t_kva",
                # Per-phase power factor
                "pf1", "pf2", "pf3", "pf_avg",
                # Energy
                "kwh_imp", "kwh_exp", "kvarh_imp", "kvarh_exp", "t_kvah",
                # Max demand
                "md_kw", "md_kvar", "md_kva",
                # Frequency
                "frequency",
                # Other
                "temperature"
            ]
            writer.writerow(headers)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            
            # Fetch in chunks and stream
            while True:
                rows = cursor.fetchmany(1000)
                if not rows:
                    break
                for row in rows:
                    fd = json.loads(row["feature_data"]) if isinstance(row["feature_data"], str) else row["feature_data"]
                    el = fd.get("electrical", {})
                    vib = fd.get("vibration", {})
                    
                    raw_csv_row = [
                        row["timestamp"], row["machine_id"],
                        # Per-phase voltages (L-N)
                        el.get("v1n", ""), el.get("v2n", ""), el.get("v3n", ""), el.get("vln_avg", ""),
                        # Line-to-line voltages
                        el.get("v12", ""), el.get("v23", ""), el.get("v31", ""), el.get("vll_avg", ""),
                        # Per-phase currents
                        el.get("i1", ""), el.get("i2", ""), el.get("i3", ""), el.get("i_avg", ""),
                        # Per-phase active power
                        el.get("kw1", ""), el.get("kw2", ""), el.get("kw3", ""), el.get("t_kw", ""),
                        # Per-phase reactive power
                        el.get("kvar1", ""), el.get("kvar2", ""), el.get("kvar3", ""), el.get("t_kvar", ""),
                        # Per-phase apparent power
                        el.get("kva1", ""), el.get("kva2", ""), el.get("kva3", ""), el.get("t_kva", ""),
                        # Per-phase PF
                        el.get("pf1", ""), el.get("pf2", ""), el.get("pf3", ""), el.get("pf_avg", ""),
                        # Energy
                        el.get("kwh_imp", ""), el.get("kwh_exp", ""),
                        el.get("kvarh_imp", ""), el.get("kvarh_exp", ""), el.get("t_kvah", ""),
                        # Max demand
                        el.get("md_kw", ""), el.get("md_kvar", ""), el.get("md_kva", ""),
                        # Frequency
                        el.get("frequency", ""),
                        # Other
                        fd.get("temperature", ""),
                    ]
                    # Sanitize before writing
                    safe_csv_row = [sanitize_csv_cell(cell) for cell in raw_csv_row]
                    writer.writerow(safe_csv_row)
                    
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    # Make the filename strictly safe
    safe_filename = f"export_{safe_id}_{start_time or minutes}.csv"
    # Basic sanitize against directory traversal in headers
    safe_filename = safe_filename.replace("/", "_").replace("\\", "_")
    
    return StreamingResponse(
        csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )

@router.get("/machines", response_model=List[MachineInfo])
async def get_machines(current_user: dict = Depends(get_current_user)):
    """Get list of all monitored machines, sorted by most recent data first."""
    active_ids = db.get_all_machines()
    
    # Map device IDs to friendly names
    DEVICE_NAME_MAP = {
        "002200203335471332323632": "LEDL_Demo",
    }
    
    # Sort by most recent feature data so the actively-producing machine is first
    machines_with_activity = []
    for mid in active_ids:
        latest = db.get_latest_reading(machine_id=mid)
        last_ts = latest.get("timestamp", "") if latest else ""
        machines_with_activity.append((mid, last_ts))
    
    # Sort descending by timestamp (most recent first)
    machines_with_activity.sort(key=lambda x: x[1], reverse=True)
    
    machines = []
    for mid, _ in machines_with_activity:
        mapped_name = DEVICE_NAME_MAP.get(mid, f"Device {mid}")
        machines.append(
            MachineInfo(
                machine_id=mid,
                name=mapped_name,
                type="MQTT Device",
                location="Field Operations",
                unit="Remote Unit",
                plant="Site",
                status=MachineStatus.HEALTHY,
                health_score=100.0,
                uptime_hours=0.0,
            )
        )
    return machines

@router.get("/machines/{machine_id}/config")
async def get_motor_config(machine_id: str, current_user: dict = Depends(get_current_user)):
    """Get motor configuration for a specific machine."""
    safe_id = validate_machine_id(machine_id)
    config = db.get_motor_config(safe_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config

@router.post("/machines/{machine_id}/config")
async def save_motor_config(machine_id: str, config: dict, current_user: dict = Depends(get_current_user)):
    """Save or update motor configuration for a specific machine."""
    safe_id = validate_machine_id(machine_id)
    db.upsert_motor_config(safe_id, config)
    return {"status": "success", "message": "Configuration saved"}

@router.delete("/machines/{machine_id}/config")
async def delete_motor_config(machine_id: str, current_user: dict = Depends(get_current_user)):
    """Delete motor configuration for a specific machine."""
    safe_id = validate_machine_id(machine_id)
    db.delete_motor_config(safe_id)
    return {"status": "success", "message": "Configuration deleted"}
