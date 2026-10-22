"""
SQLAlchemy ORM models for Elicius Energy IoT Monitoring Dashboard.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean,
    DateTime, ForeignKey, PrimaryKeyConstraint, Index, Text, JSON
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    session_version = Column(Integer, default=0, nullable=False)
    mfa_secret = Column(String(64), nullable=True)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    device_access = relationship("UserDeviceAccess", cascade="all, delete-orphan", back_populates="user")


class UserDeviceAccess(Base):
    __tablename__ = "user_device_access"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True, index=True)
    user = relationship("User", back_populates="device_access")
    device = relationship("Device")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(100), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    target = Column(String(255), nullable=True)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class Device(Base):
    __tablename__ = "devices"
    
    device_id = Column(String(64), primary_key=True, index=True)
    alias = Column(String(100), nullable=True)
    fw_ver = Column(String(32), nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    expected_interval_s = Column(Integer, default=60, nullable=False)
    status = Column(String(50), default="Normal", nullable=False)  # Normal, Warning, Incorrect connection, Disconnected, Communication failure, New – not configured
    status_detail = Column(JSON, default=dict, nullable=False)
    configured = Column(Boolean, default=False, nullable=False)
    
    profile = relationship("DeviceProfile", back_populates="device", uselist=False, cascade="all, delete-orphan")
    baseline = relationship("DeviceBaseline", back_populates="device", uselist=False, cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="device", cascade="all, delete-orphan")


class DeviceProfile(Base):
    __tablename__ = "device_profiles"
    
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    
    # 1. Device Section
    nominal_voltage = Column(Float, default=240.0, nullable=False)
    ct_rated_current = Column(Float, default=100.0, nullable=False)
    
    # 2. Customer Information
    customer_name = Column(String(255), default="", nullable=True)
    location = Column(String(255), default="Coimbatore", nullable=True)
    department = Column(String(255), default="Energy Audit Department", nullable=True)
    contact_person = Column(String(255), default="", nullable=True)
    contact_number = Column(String(100), default="", nullable=True)
    
    # 3. Motor Name Plate Details
    motor_make = Column(String(255), default="", nullable=True)
    motor_rating_kw = Column(Float, nullable=True)
    frame_size = Column(String(100), default="", nullable=True)
    rated_current_amps = Column(Float, nullable=True)
    rated_speed_rpm = Column(Float, nullable=True)
    rated_voltage = Column(Float, nullable=True)
    rated_efficiency_pct = Column(Float, nullable=True)
    motor_connection = Column(String(50), default="", nullable=True)
    motor_duty = Column(String(50), default="", nullable=True)
    insulation_class = Column(String(50), default="", nullable=True)
    motor_type = Column(String(100), default="", nullable=True)
    serial_number = Column(String(100), default="", nullable=True)
    
    # 4. Machine Details
    machine_name = Column(String(255), default="Ring Frame 14", nullable=True)
    machine_make = Column(String(255), default="Lakshmi Machine Works", nullable=True)
    machine_model_no = Column(String(100), default="LR9/AXL", nullable=True)
    machine_count = Column(String(100), default="40s Ne", nullable=True)
    machine_tpi = Column(String(100), default="28.5", nullable=True)
    raw_material = Column(String(100), default="100% Combed Cotton", nullable=True)
    machine_rpm_max = Column(Float, default=18000.0, nullable=True)
    machine_rpm_avg = Column(Float, default=16500.0, nullable=True)
    no_of_spindles = Column(Integer, default=1200, nullable=True)
    
    # 5. Inverter Details
    inverter_make = Column(String(255), default="Danfoss", nullable=True)
    inverter_model = Column(String(255), default="VLT AutomationDrive", nullable=True)
    
    # 6. LEDL Representative
    rep_name = Column(String(255), default="K. Senthil Kumar", nullable=True)
    rep_designation = Column(String(255), default="Sr. Energy Audit Engineer", nullable=True)
    rep_contact_number = Column(String(100), default="+91 98422 12345", nullable=True)
    rep_email = Column(String(255), default="senthil.k@ledl.in", nullable=True)
    
    # 7. Customer Confirmation Signatory
    signatory_customer_name = Column(String(255), default="Plant Manager", nullable=True)
    signatory_designation = Column(String(255), default="General Manager - Engineering", nullable=True)
    
    # 8. Commercial Inputs
    electricity_tariff = Column(Float, nullable=True)
    annual_operating_hours = Column(Float, nullable=True)
    motor_investment = Column(Float, default=0.0, nullable=False)
    installation_cost = Column(Float, default=0.0, nullable=False)
    replacement_motor_rating_kw = Column(Float, nullable=True)
    replacement_motor_efficiency_pct = Column(Float, nullable=True)
    
    # 9. Advanced & Thresholds
    idle_threshold_kw = Column(Float, nullable=True)  # Defaults to 5% of motor_rating_kw or 0.2 kW
    thresholds = Column(JSON, default=dict, nullable=False)
    email_alerts_enabled = Column(Boolean, default=False, nullable=False)
    alert_email = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    device = relationship("Device", back_populates="profile")


class DeviceBaseline(Base):
    __tablename__ = "device_baseline"
    
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    per_phase_pf = Column(JSON, default=dict, nullable=False)  # {"pf1": ..., "pf2": ..., "pf3": ...}
    per_phase_current_share = Column(JSON, default=dict, nullable=False)  # {"i1_share": ..., "i2_share": ..., "i3_share": ...}
    tolerance_pct = Column(Float, default=30.0, nullable=False)
    
    device = relationship("Device", back_populates="baseline")


class Reading(Base):
    __tablename__ = "readings"
    
    device_id = Column(String(64), nullable=False, index=True)
    ts = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    fw_ver = Column(String(32), nullable=True)
    
    # Phase-to-neutral voltages
    v1n = Column(Float, nullable=True)
    v2n = Column(Float, nullable=True)
    v3n = Column(Float, nullable=True)
    vln_avg = Column(Float, nullable=True)
    
    # Line-to-line voltages
    v12 = Column(Float, nullable=True)
    v23 = Column(Float, nullable=True)
    v31 = Column(Float, nullable=True)
    vll_avg = Column(Float, nullable=True)
    
    # Currents
    i1 = Column(Float, nullable=True)
    i2 = Column(Float, nullable=True)
    i3 = Column(Float, nullable=True)
    i_avg = Column(Float, nullable=True)
    
    # Active Power (kW)
    kw1 = Column(Float, nullable=True)
    kw2 = Column(Float, nullable=True)
    kw3 = Column(Float, nullable=True)
    t_kw = Column(Float, nullable=True)
    
    # Reactive Power (kVAR)
    kvar1 = Column(Float, nullable=True)
    kvar2 = Column(Float, nullable=True)
    kvar3 = Column(Float, nullable=True)
    t_kvar = Column(Float, nullable=True)
    
    # Apparent Power (kVA)
    kva1 = Column(Float, nullable=True)
    kva2 = Column(Float, nullable=True)
    kva3 = Column(Float, nullable=True)
    t_kva = Column(Float, nullable=True)
    
    # Power Factor
    pf1 = Column(Float, nullable=True)
    pf2 = Column(Float, nullable=True)
    pf3 = Column(Float, nullable=True)
    pf_avg = Column(Float, nullable=True)
    
    # Frequency
    freq = Column(Float, nullable=True)
    
    # Energy Counters
    kwh_imp = Column(BigInteger, nullable=True)
    kwh_exp = Column(BigInteger, nullable=True)
    kvarh_imp = Column(BigInteger, nullable=True)
    kvarh_exp = Column(BigInteger, nullable=True)
    t_kvah = Column(BigInteger, nullable=True)
    
    # Max Demand
    md_kw = Column(Float, nullable=True)
    md_kvar = Column(Float, nullable=True)
    md_kva = Column(Float, nullable=True)
    
    # Full Raw JSON
    raw = Column(JSON, nullable=True)
    
    __table_args__ = (
        PrimaryKeyConstraint("device_id", "ts"),
        Index("idx_readings_device_ts", "device_id", "ts"),
    )


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    phase = Column(String(10), nullable=True)  # L1, L2, L3, ALL, or null
    severity = Column(String(50), nullable=False)  # Communication failure, Disconnected, Incorrect connection, Warning
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    cleared_at = Column(DateTime(timezone=True), nullable=True, index=True)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    details = Column(JSON, default=dict, nullable=False)
    
    device = relationship("Device", back_populates="alerts")
    
    __table_args__ = (
        Index("idx_alerts_open", "device_id", "type", "phase", "cleared_at"),
    )


class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_no = Column(String(100), unique=True, nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(String(100), default="admin", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    params = Column(JSON, nullable=False)
    config_snapshot = Column(JSON, nullable=False)
    summary = Column(JSON, nullable=False)
    file_path = Column(String(512), nullable=False)
    
    device = relationship("Device", back_populates="reports")


class KBChunk(Base):
    __tablename__ = "kb_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # Stores float list embedding (1536 dims)
    metadata_json = Column(JSON, default=dict, nullable=False)
