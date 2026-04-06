"""
SQLite time-series storage with WAL mode for concurrent reads.
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for time-series sensor data storage."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def _get_conn(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    machine_id TEXT NOT NULL DEFAULT 'Machine_5',
                    source TEXT NOT NULL DEFAULT 'simulated',
                    voltage REAL, current REAL, active_power REAL,
                    apparent_power REAL, power_factor REAL, energy REAL,
                    frequency REAL,
                    ax REAL, ay REAL, az REAL,
                    gx REAL, gy REAL, gz REAL,
                    temperature REAL
                );
                
                CREATE INDEX IF NOT EXISTS idx_readings_ts 
                    ON sensor_readings(timestamp);
                CREATE INDEX IF NOT EXISTS idx_readings_machine 
                    ON sensor_readings(machine_id, timestamp);
                
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    machine_id TEXT NOT NULL DEFAULT 'Machine_5',
                    feature_data TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_features_ts 
                    ON features(timestamp);
                
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    machine_id TEXT NOT NULL DEFAULT 'Machine_5',
                    severity TEXT NOT NULL,
                    category TEXT,
                    message TEXT NOT NULL,
                    value REAL,
                    threshold REAL,
                    acknowledged INTEGER DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_alerts_ts 
                    ON alerts(timestamp);
                
                CREATE TABLE IF NOT EXISTS ai_diagnoses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    machine_id TEXT NOT NULL DEFAULT 'Machine_5',
                    fault_type TEXT,
                    confidence REAL,
                    severity TEXT,
                    explanation TEXT,
                    recommended_action TEXT,
                    physics_reasoning TEXT,
                    retrieved_context TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_diag_ts 
                    ON ai_diagnoses(timestamp);
            """)
        logger.info(f"Database initialized at {self.db_path}")
    
    # ── Insert Operations ──────────────────────────────────────────────────
    
    def insert_reading(self, reading: Dict[str, Any]):
        """Insert a sensor reading."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sensor_readings 
                (timestamp, machine_id, source, voltage, current, active_power,
                 apparent_power, power_factor, energy, frequency,
                 ax, ay, az, gx, gy, gz, temperature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reading.get("timestamp", datetime.utcnow().isoformat()),
                reading.get("machine_id", "Machine_5"),
                reading.get("source", "simulated"),
                reading.get("voltage"), reading.get("current"),
                reading.get("active_power"), reading.get("apparent_power"),
                reading.get("power_factor"), reading.get("energy"),
                reading.get("frequency"),
                reading.get("ax"), reading.get("ay"), reading.get("az"),
                reading.get("gx"), reading.get("gy"), reading.get("gz"),
                reading.get("temperature"),
            ))
    
    def insert_features(self, machine_id: str, features: Dict):
        """Insert computed features."""
        def _json_default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO features (timestamp, machine_id, feature_data)
                VALUES (?, ?, ?)
            """, (datetime.utcnow().isoformat(), machine_id, json.dumps(features, default=_json_default)))
    
    def insert_alert(self, alert: Dict[str, Any]):
        """Insert an alert."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO alerts (timestamp, machine_id, severity, category, 
                                     message, value, threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.get("timestamp", datetime.utcnow().isoformat()),
                alert.get("machine_id", "Machine_5"),
                alert.get("severity", "info"),
                alert.get("category", ""),
                alert.get("message", ""),
                alert.get("value"),
                alert.get("threshold"),
            ))
    
    def insert_diagnosis(self, diagnosis: Dict[str, Any]):
        """Insert an AI diagnosis."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO ai_diagnoses 
                (timestamp, machine_id, fault_type, confidence, severity,
                 explanation, recommended_action, physics_reasoning, retrieved_context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                diagnosis.get("timestamp", datetime.utcnow().isoformat()),
                diagnosis.get("machine_id", "Machine_5"),
                diagnosis.get("fault_type"),
                diagnosis.get("confidence"),
                diagnosis.get("severity"),
                diagnosis.get("explanation"),
                diagnosis.get("recommended_action"),
                diagnosis.get("physics_reasoning"),
                diagnosis.get("retrieved_context"),
            ))
    
    # ── Query Operations ───────────────────────────────────────────────────
    
    def get_readings(self, machine_id: str = "Machine_5",
                     minutes: int = 10, limit: int = 2000) -> List[Dict]:
        """Get recent sensor readings with adaptive sampling."""
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        
        # Simple sampling: if window > 30 mins, take every Nth row
        nth = 1
        if minutes > 30:
            nth = max(1, (minutes * 60) // 1000)
            
        with self._get_conn() as conn:
            # We use a subquery to apply sampling via ROW_NUMBER
            query = f"""
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn 
                    FROM sensor_readings 
                    WHERE machine_id = ? AND timestamp > ?
                ) WHERE rn % ? = 0
                ORDER BY timestamp DESC LIMIT ?
            """
            rows = conn.execute(query, (machine_id, since, nth, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def get_features(self, machine_id: str = "Machine_5",
                     minutes: int = 10, limit: int = 2000) -> List[Dict]:
        """Get recent computed features with adaptive sampling."""
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        
        # Simple sampling: if window > 30 mins, take every Nth row
        nth = 1
        if minutes > 30:
            nth = max(1, (minutes * 6) // 100) # Since features usually every 10s
            
        with self._get_conn() as conn:
            query = f"""
                SELECT * FROM (
                    SELECT *, ROW_NUMBER() OVER (ORDER BY timestamp DESC) as rn 
                    FROM features 
                    WHERE machine_id = ? AND timestamp > ?
                ) WHERE rn % ? = 0
                ORDER BY timestamp DESC LIMIT ?
            """
            rows = conn.execute(query, (machine_id, since, nth, limit)).fetchall()
        return [
            {**dict(r), "feature_data": json.loads(r["feature_data"])}
            for r in rows
        ]
    
    def get_alerts(self, machine_id: str = "Machine_5",
                   minutes: int = 60, limit: int = 50) -> List[Dict]:
        """Get recent alerts."""
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM alerts 
                WHERE machine_id = ? AND timestamp > ?
                ORDER BY timestamp DESC LIMIT ?
            """, (machine_id, since, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def get_diagnoses(self, machine_id: str = "Machine_5",
                      limit: int = 10) -> List[Dict]:
        """Get recent AI diagnoses."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM ai_diagnoses 
                WHERE machine_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (machine_id, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def get_latest_reading(self, machine_id: str = "Machine_5") -> Optional[Dict]:
        """Get the most recent sensor reading."""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM sensor_readings 
                WHERE machine_id = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (machine_id,)).fetchone()
        return dict(row) if row else None
    
    def get_reading_count(self, machine_id: str = "Machine_5",
                          minutes: int = 1) -> int:
        """Get count of readings in recent period (for rate calculation)."""
        since = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as cnt FROM sensor_readings 
                WHERE machine_id = ? AND timestamp > ?
            """, (machine_id, since)).fetchone()
        return row["cnt"] if row else 0
    
    # ── Cleanup ────────────────────────────────────────────────────────────
    
    def cleanup_old_data(self):
        """Remove data older than retention period."""
        cutoff = (datetime.utcnow() - timedelta(hours=settings.DATA_RETENTION_HOURS)).isoformat()
        with self._get_conn() as conn:
            for table in ["sensor_readings", "features", "alerts", "ai_diagnoses"]:
                conn.execute(f"DELETE FROM {table} WHERE timestamp < ?", (cutoff,))
        logger.info(f"Cleaned up data older than {settings.DATA_RETENTION_HOURS}h")


# Singleton instance
db = Database()
