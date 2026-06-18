"""
REST endpoints for historical data and machine metadata.
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import io
import csv
from datetime import datetime, timedelta
from app.database import db
from app.models import MachineInfo, MachineStatus

router = APIRouter(prefix="/data", tags=["data"])

@router.get("/history")
async def get_history(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(10, ge=1, le=10080)
):
    """Get historical sensor readings."""
    return db.get_readings(machine_id, minutes)

@router.get("/features")
async def get_features(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(10, ge=1, le=10080)
):
    """Get historical computed features."""
    return db.get_features(machine_id, minutes)

@router.get("/alerts")
async def get_alerts(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(60, ge=1, le=10080)
):
    """Get historical alerts."""
    return db.get_alerts(machine_id, minutes)

@router.get("/download_csv")
async def download_csv(
    machine_id: str = "sim-pump-001",
    minutes: int = Query(60, ge=1, le=10080)
):
    """Download historical data as CSV, streamed directly from DB."""
    
    def csv_generator():
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        with db._get_conn() as conn:
            cursor = conn.execute("""
                SELECT timestamp, machine_id, source, voltage, current, active_power,
                       apparent_power, power_factor, energy, frequency,
                       ax, ay, az, gx, gy, gz, temperature
                FROM sensor_readings
                WHERE machine_id = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (machine_id, since))
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = [d[0] for d in cursor.description]
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
                    writer.writerow(row)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    return StreamingResponse(
        csv_generator(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{machine_id}_{minutes}m.csv"}
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
