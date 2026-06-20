"""
REST endpoints for historical data and machine metadata.
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import io
import csv
import json
from datetime import datetime, timedelta
from app.database import db
from app.models import MachineInfo, MachineStatus

router = APIRouter(prefix="/data", tags=["data"])

@router.get("/history")
async def get_history(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(10, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None
):
    """Get historical sensor readings."""
    return db.get_readings(machine_id, minutes, start_time=start_time, end_time=end_time)

@router.get("/features")
async def get_features(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(10, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None
):
    """Get historical computed features."""
    return db.get_features(machine_id, minutes, start_time=start_time, end_time=end_time)

@router.get("/alerts")
async def get_alerts(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(60, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None
):
    """Get historical alerts."""
    return db.get_alerts(machine_id, minutes, start_time=start_time, end_time=end_time)

@router.get("/download_csv")
async def download_csv(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(60, ge=1, le=10080),
    start_time: str = None,
    end_time: str = None
):
    """Download historical data as CSV with full 3-phase parameters from features table."""
    
    def csv_generator():
        if start_time and end_time:
            since = start_time
            until = end_time
        else:
            since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
            until = datetime.utcnow().isoformat()
            
        with db._get_conn() as conn:
            # Query features table which contains the full 3-phase data as JSON
            cursor = conn.execute("""
                SELECT timestamp, machine_id, feature_data
                FROM features
                WHERE machine_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp ASC
            """, (machine_id, since, until))
            
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
                    
                    csv_row = [
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
                    writer.writerow(csv_row)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    return StreamingResponse(
        csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{machine_id}_{start_time or minutes}.csv"}
    )

@router.get("/machines", response_model=List[MachineInfo])
async def get_machines():
    """Get list of monitored machines based on recent activity, sorted by most recent data first."""
    active_ids = db.get_active_machines(minutes=10)
    
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
