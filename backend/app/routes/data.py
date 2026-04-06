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
    """Get list of monitored machines.
    Returns the same IDs used by the simulation engine so data is consistent.
    """
    return [
        MachineInfo(
            machine_id="sim-pump-001",
            name="Centrifugal Pump P-101",
            type="Centrifugal Pump",
            location="Ras Tanura Refinery",
            unit="Processing Unit 3",
            plant="Ras Tanura",
            status=MachineStatus.HEALTHY,
            health_score=94.2,
            uptime_hours=2847.3,
        ),
        MachineInfo(
            machine_id="sim-pump-002",
            name="Booster Pump P-202",
            type="Reciprocating Pump",
            location="Jubail Industrial Complex",
            unit="Processing Unit 5",
            plant="Jubail",
            status=MachineStatus.WARNING,
            health_score=72.8,
            uptime_hours=8760.0,
        ),
        MachineInfo(
            machine_id="sim-motor-003",
            name="Compressor Motor M-301",
            type="Induction Motor",
            location="Yanbu Integrated",
            unit="Gas Processing Unit 1",
            plant="Yanbu",
            status=MachineStatus.HEALTHY,
            health_score=88.5,
            uptime_hours=6500.0,
        ),
        MachineInfo(
            machine_id="Machine_10",
            name="Actual MQTT Device",
            type="Unknown Asset Type",
            location="Field Operations",
            unit="Remote Unit 10",
            plant="Remote Substation",
            status=MachineStatus.HEALTHY,
            health_score=100.0,
            uptime_hours=100.0,
        ),
    ]
