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


class ThreePhaseEnergyData(BaseModel):
    """3-phase energy meter data from the 'ledl' MQTT topic."""
    dID: str = Field("", description="Device ID")
    dTS: int = Field(0, description="Device timestamp (epoch)")
    # Phase-to-neutral voltages
    v1n: float = Field(0.0, description="L1-N Voltage")
    v2n: float = Field(0.0, description="L2-N Voltage")
    v3n: float = Field(0.0, description="L3-N Voltage")
    vln_avg: float = Field(0.0, description="Average L-N Voltage")
    # Line-to-line voltages
    v12: float = Field(0.0, description="L1-L2 Voltage")
    v23: float = Field(0.0, description="L2-L3 Voltage")
    v31: float = Field(0.0, description="L3-L1 Voltage")
    vll_avg: float = Field(0.0, description="Average L-L Voltage")
    # Currents
    i1: float = Field(0.0, description="L1 Current")
    i2: float = Field(0.0, description="L2 Current")
    i3: float = Field(0.0, description="L3 Current")
    i_avg: float = Field(0.0, description="Average Current")
    # Active Power (kW)
    kw1: float = Field(0.0, description="L1 Active Power")
    kw2: float = Field(0.0, description="L2 Active Power")
    kw3: float = Field(0.0, description="L3 Active Power")
    # Reactive Power (kVAR)
    kvar1: float = Field(0.0, description="L1 Reactive Power")
    kvar2: float = Field(0.0, description="L2 Reactive Power")
    kvar3: float = Field(0.0, description="L3 Reactive Power")
    # Apparent Power (kVA)
    kva1: float = Field(0.0, description="L1 Apparent Power")
    kva2: float = Field(0.0, description="L2 Apparent Power")
    kva3: float = Field(0.0, description="L3 Apparent Power")
    # Totals
    t_kw: float = Field(0.0, description="Total Active Power")
    t_kvar: float = Field(0.0, description="Total Reactive Power")
    t_kva: float = Field(0.0, description="Total Apparent Power")
    # Power Factor
    pf1: float = Field(1.0, description="L1 Power Factor")
    pf2: float = Field(1.0, description="L2 Power Factor")
    pf3: float = Field(1.0, description="L3 Power Factor")
    pf_avg: float = Field(1.0, description="Average Power Factor")
    # Frequency
    freq: float = Field(50.0, description="Frequency (Hz)")
    # Energy counters
    kwh_imp: float = Field(0.0, description="kWh Import")
    kwh_exp: float = Field(0.0, description="kWh Export")
    kvarh_imp: float = Field(0.0, description="kVARh Import")
    kvarh_exp: float = Field(0.0, description="kVARh Export")
    t_kvah: float = Field(0.0, description="Total kVAh")
    # Max Demand
    md_kw: float = Field(0.0, description="Max Demand kW")
    md_kvar: float = Field(0.0, description="Max Demand kVAR")
    md_kva: float = Field(0.0, description="Max Demand kVA")


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
    """Computed electrical features (supports both single-phase and 3-phase)."""
    voltage: float = 0.0
    current: float = 0.0
    active_power: float = 0.0
    apparent_power: float = 0.0
    power_factor: float = 0.0
    frequency: float = 0.0
    efficiency: float = 0.0
    load_percentage: float = 0.0
    energy_cumulative: float = 0.0
    # ── 3-Phase Fields ─────────────────────────────────────────────────
    is_three_phase: bool = False
    dTS: int = 0
    # Phase-to-neutral voltages
    v1n: float = 0.0
    v2n: float = 0.0
    v3n: float = 0.0
    vln_avg: float = 0.0
    # Line-to-line voltages
    v12: float = 0.0
    v23: float = 0.0
    v31: float = 0.0
    vll_avg: float = 0.0
    # Per-phase currents
    i1: float = 0.0
    i2: float = 0.0
    i3: float = 0.0
    i_avg: float = 0.0
    # Per-phase Active Power (kW)
    kw1: float = 0.0
    kw2: float = 0.0
    kw3: float = 0.0
    # Per-phase Reactive Power (kVAR)
    kvar1: float = 0.0
    kvar2: float = 0.0
    kvar3: float = 0.0
    # Per-phase Apparent Power (kVA)
    kva1: float = 0.0
    kva2: float = 0.0
    kva3: float = 0.0
    # Totals
    t_kw: float = 0.0
    t_kvar: float = 0.0
    t_kva: float = 0.0
    # Per-phase Power Factor
    pf1: float = 1.0
    pf2: float = 1.0
    pf3: float = 1.0
    pf_avg: float = 1.0
    # Energy counters
    kwh_imp: float = 0.0
    kwh_exp: float = 0.0
    kvarh_imp: float = 0.0
    kvarh_exp: float = 0.0
    t_kvah: float = 0.0
    # Max Demand
    md_kw: float = 0.0
    md_kvar: float = 0.0
    md_kva: float = 0.0


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
