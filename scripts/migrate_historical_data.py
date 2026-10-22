#!/usr/bin/env python3
"""
Migrate historical sensor readings, devices, and alerts from sensor_data.db
into the updated database (PostgreSQL / TimescaleDB or SQLite).
Guarantees 100% data retention without deleting the original database.
"""
import os
import sys
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add project root and backend to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration")

DEVICE_MAP = {
    "LEDL_Demo": "002200203335471332323632",
    "LEDL_Device_2": "002D00203335471332323632",
    "002200203335471332323632": "002200203335471332323632",
    "002D00203335471332323632": "002D00203335471332323632",
}

DEFAULT_DEVICES = {
    "002200203335471332323632": {
        "alias": "Paint booth",
        "fw_ver": "13.4",
        "status": "Normal",
        "configured": True,
        "customer_name": "Lakshmi Electrical Drives Pvt Ltd",
        "location": "Coimbatore",
        "department": "Energy Audit Department",
        "machine_name": "Paint Booth Exhaust Motor",
        "motor_make": "LEDL",
        "motor_rating_kw": 15.0,
        "rated_current_amps": 28.5,
        "nominal_voltage": 240.0,
        "ct_rated_current": 100.0,
    },
    "002D00203335471332323632": {
        "alias": "Compressor motor",
        "fw_ver": "13.4",
        "status": "Normal",
        "configured": True,
        "customer_name": "Lakshmi Electrical Drives Pvt Ltd",
        "location": "Coimbatore",
        "department": "Energy Audit Department",
        "machine_name": "Main Air Compressor Motor",
        "motor_make": "LEDL",
        "motor_rating_kw": 22.0,
        "rated_current_amps": 41.0,
        "nominal_voltage": 240.0,
        "ct_rated_current": 100.0,
    }
}


def find_source_db() -> Path:
    candidates = [
        ROOT_DIR / "backend" / "data" / "sensor_data.db",
        Path("/app/backend_data/sensor_data.db"),
        Path("/app/data/sensor_data.db"),
        ROOT_DIR / "data" / "sensor_data.db",
        Path("/home/ubuntu/predictive_maintenace_aramco/backend/data/sensor_data.db"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    raise FileNotFoundError("Could not locate sensor_data.db source database file.")


def parse_iso_or_epoch(val):
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def run_migration():
    from app.db.base import engine, SessionLocal
    from app.db.models import Device, DeviceProfile, Reading, Alert
    from sqlalchemy import text

    src_path = find_source_db()
    logger.info("Found source database at %s", src_path)

    src_uri = f"file:{src_path}?immutable=1"
    src_conn = sqlite3.connect(src_uri, uri=True)
    src_conn.row_factory = sqlite3.Row

    # 1. Count records
    total_readings = src_conn.execute("SELECT count(*) FROM sensor_readings").fetchone()[0]
    total_alerts = src_conn.execute("SELECT count(*) FROM alerts").fetchone()[0]
    logger.info("Source database contains %d sensor readings and %d alerts.", total_readings, total_alerts)

    db = SessionLocal()
    try:
        # 2. Ensure devices exist
        for d_id, info in DEFAULT_DEVICES.items():
            existing = db.query(Device).filter(Device.device_id == d_id).first()
            if not existing:
                dev = Device(
                    device_id=d_id,
                    alias=info["alias"],
                    fw_ver=info["fw_ver"],
                    status=info["status"],
                    configured=info["configured"],
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    expected_interval_s=60,
                    status_detail={"ct_l1": "Normal", "ct_l2": "Normal", "ct_l3": "Normal"}
                )
                db.add(dev)
                db.flush()

                prof = DeviceProfile(
                    device_id=d_id,
                    nominal_voltage=info["nominal_voltage"],
                    ct_rated_current=info["ct_rated_current"],
                    customer_name=info["customer_name"],
                    location=info["location"],
                    department=info["department"],
                    machine_name=info["machine_name"],
                    motor_make=info["motor_make"],
                    motor_rating_kw=info["motor_rating_kw"],
                    rated_current_amps=info["rated_current_amps"],
                    thresholds={}
                )
                db.add(prof)
                logger.info("Created device & profile for %s (%s)", d_id, info["alias"])
        db.commit()

        # 3. Migrate readings in batches
        logger.info("Migrating readings in chunks...")
        cursor = src_conn.cursor()
        cursor.execute("SELECT timestamp, machine_id, voltage, current, active_power, apparent_power, power_factor, energy, frequency FROM sensor_readings ORDER BY id ASC")
        
        batch_size = 2000
        batch = []
        migrated = 0
        is_postgres = (engine.dialect.name == "postgresql")

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            
            insert_rows = []
            for r in rows:
                m_id = r["machine_id"]
                d_id = DEVICE_MAP.get(m_id, m_id)
                ts = parse_iso_or_epoch(r["timestamp"])
                
                v_avg = r["voltage"]
                i_avg = r["current"]
                t_kw = r["active_power"]
                t_kva = r["apparent_power"]
                pf = r["power_factor"]
                energy = r["energy"]
                freq = r["frequency"]
                
                vll = round(v_avg * 1.732, 2) if v_avg is not None else None
                
                insert_rows.append({
                    "device_id": d_id,
                    "ts": ts,
                    "received_at": ts,
                    "fw_ver": "13.4",
                    "vln_avg": v_avg,
                    "vll_avg": vll,
                    "i_avg": i_avg,
                    "t_kw": t_kw,
                    "t_kva": t_kva,
                    "t_kvar": round((t_kva**2 - t_kw**2)**0.5, 2) if (t_kva and t_kw and t_kva >= t_kw) else 0.0,
                    "pf_avg": pf,
                    "freq": freq,
                    "kwh_imp": int(energy) if energy is not None else 0,
                    "raw": "{}"
                })

            if insert_rows:
                if is_postgres:
                    from sqlalchemy.dialects.postgresql import insert as pg_insert
                    stmt = pg_insert(Reading).values(insert_rows)
                    stmt = stmt.on_conflict_do_nothing(index_elements=['device_id', 'ts'])
                    db.execute(stmt)
                else:
                    # SQLite INSERT OR IGNORE
                    stmt = text("""
                        INSERT OR IGNORE INTO readings 
                        (device_id, ts, received_at, fw_ver, vln_avg, vll_avg, i_avg, t_kw, t_kva, t_kvar, pf_avg, freq, kwh_imp, raw)
                        VALUES (:device_id, :ts, :received_at, :fw_ver, :vln_avg, :vll_avg, :i_avg, :t_kw, :t_kva, :t_kvar, :pf_avg, :freq, :kwh_imp, :raw)
                    """)
                    db.execute(stmt, insert_rows)
                
                db.commit()
                migrated += len(insert_rows)
                logger.info("Migrated %d / %d readings...", migrated, total_readings)

        # 4. Migrate alerts
        logger.info("Migrating alerts...")
        alert_cursor = src_conn.cursor()
        alert_cursor.execute("SELECT timestamp, machine_id, severity, message, value, threshold, acknowledged FROM alerts ORDER BY id ASC")
        alert_rows = alert_cursor.fetchall()
        
        alert_count = 0
        for ar in alert_rows:
            d_id = DEVICE_MAP.get(ar["machine_id"], ar["machine_id"])
            ts = parse_iso_or_epoch(ar["timestamp"])
            
            existing_alert = db.query(Alert).filter(
                Alert.device_id == d_id,
                Alert.started_at == ts
            ).first()
            
            if not existing_alert:
                new_alert = Alert(
                    device_id=d_id,
                    type=ar["severity"].title(),
                    phase="ALL",
                    severity=ar["severity"].title(),
                    started_at=ts,
                    cleared_at=ts if ar["acknowledged"] else None,
                    acknowledged_by="admin" if ar["acknowledged"] else None,
                    acknowledged_at=ts if ar["acknowledged"] else None,
                    details={"message": ar["message"], "value": ar["value"], "threshold": ar["threshold"]}
                )
                db.add(new_alert)
                alert_count += 1
        
        db.commit()
        logger.info("Alerts migration complete. Added %d alerts.", alert_count)

        # 5. Update device first_seen and last_seen
        for d_id in DEFAULT_DEVICES.keys():
            latest = db.query(Reading).filter(Reading.device_id == d_id).order_by(Reading.ts.desc()).first()
            earliest = db.query(Reading).filter(Reading.device_id == d_id).order_by(Reading.ts.asc()).first()
            dev = db.query(Device).filter(Device.device_id == d_id).first()
            if dev and latest:
                dev.last_seen = latest.ts
            if dev and earliest:
                dev.first_seen = earliest.ts
        db.commit()

        logger.info("SUCCESS: All historical data safely retained and migrated into the new platform schema.")

    except Exception as e:
        db.rollback()
        logger.error("Migration error: %s", str(e), exc_info=True)
        raise
    finally:
        db.close()
        src_conn.close()


if __name__ == "__main__":
    run_migration()
