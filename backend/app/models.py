"""
Pydantic data models for sensor data, features, alerts, and AI diagnoses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Enums ──────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"

class MachineStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"

class DataSource(str, Enum):
    MQTT = "mqtt"
    SIMULATED = "simulated"

class FaultType(str, Enum):
    NONE = "none"
    BEARING_FAULT = "bearing_fault"
    IMBALANCE = "imbalance"
    MISALIGNMENT = "misalignment"
    LOOSENESS = "looseness"
    ELECTRICAL_FAULT = "electrical_fault"
    OVERLOAD = "overload"
    OVERHEATING = "overheating"
    UNKNOWN = "unknown"

class SimulationMode(str, Enum):
    NORMAL = "normal"
    BEARING_DEGRADATION = "bearing_degradation"
    SUDDEN_ANOMALY = "sudden_anomaly"


# ── Sensor Data Models ─────────────────────────────────────────────────────

class EnergyData(BaseModel):
    """Electrical parameters from energy/Machine_10 topic."""
    V: float = Field(0.0, description="Voltage (V)")
    I: float = Field(0.0, description="Current (A)")
    P: float = Field(0.0, description="Active Power (W)")
    KVA: float = Field(0.0, description="Apparent Power (KVA)")
    pf: float = Field(1.0, description="Power Factor")
    Energy: float = Field(0.0, description="Cumulative Energy (kWh)")
    Freq: float = Field(50.0, description="Frequency (Hz)")


class AccelData(BaseModel):
    """Acceleration and gyroscope data from energy/Machine_5/accel topic."""
    ax: float = Field(..., description="X-axis acceleration (g)")
    ay: float = Field(..., description="Y-axis acceleration (g)")
    az: float = Field(..., description="Z-axis acceleration (g)")
    gx: float = Field(..., description="X-axis gyroscope (deg/s)")
    gy: float = Field(..., description="Y-axis gyroscope (deg/s)")
    gz: float = Field(..., description="Z-axis gyroscope (deg/s)")
    temp: Optional[float] = Field(None, description="Temperature (degC)")


class SensorReading(BaseModel):
    """Combined sensor reading with timestamp and source info."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    machine_id: str = "Machine_10"
    source: DataSource = DataSource.SIMULATED
    energy: Optional[EnergyData] = None
    accel: Optional[AccelData] = None
    temperature: Optional[float] = None  # Simulated


# ── Feature Models ─────────────────────────────────────────────────────────

class VibrationFeatures(BaseModel):
    """Computed vibration features."""
    rms_x: float = 0.0
    rms_y: float = 0.0
    rms_z: float = 0.0
    rms_overall: float = 0.0
    peak_x: float = 0.0
    peak_y: float = 0.0
    peak_z: float = 0.0
    kurtosis_x: float = 0.0
    kurtosis_y: float = 0.0
    kurtosis_z: float = 0.0
    crest_factor: float = 0.0
    dominant_freq: float = 0.0
    fft_magnitudes: List[float] = Field(default_factory=list)
    fft_frequencies: List[float] = Field(default_factory=list)


class ElectricalFeatures(BaseModel):
    """Computed electrical features."""
    voltage: float = 0.0
    current: float = 0.0
    active_power: float = 0.0
    apparent_power: float = 0.0
    power_factor: float = 0.0
    frequency: float = 0.0
    efficiency: float = 0.0
    load_percentage: float = 0.0
    energy_cumulative: float = 0.0


class FeatureVector(BaseModel):
    """Complete feature vector for ML and AI analysis."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    machine_id: str = "Machine_10"
    vibration: VibrationFeatures = Field(default_factory=VibrationFeatures)
    electrical: ElectricalFeatures = Field(default_factory=ElectricalFeatures)
    temperature: float = 0.0
    anomaly_score: float = 0.0
    health_score: float = 100.0
    iso_zone: str = "A"


# ── Health Indicators ──────────────────────────────────────────────────────

class HealthIndicator(BaseModel):
    """Individual health indicator with probability."""
    name: str
    probability: float = Field(0.0, ge=0.0, le=1.0)
    status: MachineStatus = MachineStatus.HEALTHY
    description: str = ""


class MachineHealth(BaseModel):
    """Overall machine health assessment."""
    machine_id: str
    overall_status: MachineStatus = MachineStatus.HEALTHY
    health_score: float = 100.0
    indicators: List[HealthIndicator] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ── Alert Model ────────────────────────────────────────────────────────────

class Alert(BaseModel):
    """System alert."""
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    machine_id: str = "Machine_10"
    severity: Severity = Severity.INFO
    category: str = ""
    message: str = ""
    value: Optional[float] = None
    threshold: Optional[float] = None
    acknowledged: bool = False


# ── AI Diagnosis ───────────────────────────────────────────────────────────

class FaultDiagnosis(BaseModel):
    """AI-generated fault diagnosis from RAG pipeline."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    machine_id: str = "Machine_10"
    fault_type: str = "none"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    severity: Severity = Severity.INFO
    explanation: str = ""
    recommended_action: str = ""
    physics_reasoning: str = ""
    retrieved_context_summary: str = ""


# ── WebSocket Message Models ──────────────────────────────────────────────

class WSMessage(BaseModel):
    """WebSocket message envelope."""
    type: str  # sensor_data, features, alerts, ai_diagnosis, system_status
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Machine Info ───────────────────────────────────────────────────────────

class MachineInfo(BaseModel):
    """Machine metadata."""
    machine_id: str
    name: str
    type: str
    location: str
    unit: str
    plant: str
    status: MachineStatus = MachineStatus.HEALTHY
    health_score: float = 100.0
    uptime_hours: float = 0.0
    last_maintenance: Optional[datetime] = None


# ── System Status ──────────────────────────────────────────────────────────

class SystemStatus(BaseModel):
    """Overall system status."""
    mqtt_connected: bool = False
    data_source: DataSource = DataSource.SIMULATED
    active_connections: int = 0
    uptime_seconds: float = 0.0
    last_reading: Optional[datetime] = None
    readings_per_second: float = 0.0
