"""
Unit tests for the Fault Detection Engine and status precedence logic.
Tests all rules specified in Section 5 of the LEDL Specification.
"""
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Device, DeviceProfile, DeviceBaseline, Alert
from app.services.fault_engine import FaultEngine

# Sample Normal Payload from Section 3 contract
SAMPLE_NORMAL_PAYLOAD = {
    "dID": "002D00203335471332323632",
    "dTS": 1792076074,
    "fw_ver": "13.4",
    "v1n": 240.01, "v2n": 240.33, "v3n": 245.02, "vln_avg": 241.78,
    "v12": 416.58, "v23": 421.17, "v31": 418.63, "vll_avg": 418.79,
    "i1": 8.28, "i2": 8.54, "i3": 8.98, "i_avg": 8.6,
    "kw1": 1.64, "kw2": 1.58, "kw3": 1.76,
    "kvar1": 1.13, "kvar2": 1.32, "kvar3": 1.32,
    "kva1": 1.99, "kva2": 2.05, "kva3": 2.2,
    "t_kw": 4.97, "t_kvar": 3.76, "t_kva": 6.24,
    "pf1": 0.82, "pf2": 0.77, "pf3": 0.8, "pf_avg": 0.8, "freq": 50.0,
    "kwh_imp": 134, "kwh_exp": 0, "kvarh_imp": 99, "kvarh_exp": 0, "t_kvah": 167,
    "md_kw": 5.38, "md_kvar": 4.17, "md_kva": 6.77
}


@pytest.fixture
def db_session():
    """In-memory SQLite database session for unit tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed device and profile
    dev = Device(
        device_id="002D00203335471332323632",
        alias="Test Motor",
        fw_ver="13.4",
        status="Normal",
        status_detail={},
        configured=True
    )
    prof = DeviceProfile(
        device_id="002D00203335471332323632",
        nominal_voltage=240.0,
        motor_rating_kw=15.0,
        thresholds={
            "active_current_a": 1.0,
            "debounce_raise_count": 3,
            "debounce_clear_count": 3,
            "v_min_present": 50.0,
            "i_min_present": 0.05,
            "ct_swap_pf_diff": 0.25,
            "v_line_tol_pct": 6.0,
            "nominal_voltage": 240.0,
        }
    )
    session.add(dev)
    session.add(prof)
    session.commit()

    yield session
    session.close()


def test_normal_payload_stays_normal(db_session):
    """Verify that sample contract payload yields Normal status and raises no alerts."""
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    # Send 3 normal samples
    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, SAMPLE_NORMAL_PAYLOAD, now, db_session)

    assert status == "Normal"
    assert chips["ct_l1"] == "Normal"
    assert chips["ct_l2"] == "Normal"
    assert chips["ct_l3"] == "Normal"
    assert chips["vclip_l1"] == "Normal"
    assert chips["vclip_l2"] == "Normal"
    assert chips["vclip_l3"] == "Normal"
    assert db_session.query(Alert).count() == 0


def test_rule1_ct_polarity_negative_power(db_session):
    """
    Rule 1: kw_n < -0.02 kW while i_n > 1.0 A.
    Must flag exactly that phase as wrong direction after 3 samples.
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    # Reverse Phase L2 only: kw2 = -1.58
    faulty_payload = dict(SAMPLE_NORMAL_PAYLOAD)
    faulty_payload["kw2"] = -1.58
    faulty_payload["t_kw"] = round(faulty_payload["kw1"] + faulty_payload["kw2"] + faulty_payload["kw3"], 2)

    # Sample 1 & 2 (debouncing: should not raise alert yet)
    for _ in range(2):
        status, chips = engine.evaluate_reading(dev, prof, None, faulty_payload, now, db_session)
    assert db_session.query(Alert).filter(Alert.cleared_at.is_(None)).count() == 0

    # Sample 3 (debounce met: raises alert)
    status, chips = engine.evaluate_reading(dev, prof, None, faulty_payload, now, db_session)
    assert status == "Incorrect connection"
    assert chips["ct_l2"] == "Incorrect connection"
    assert "wrong direction" in chips["ct_l2_detail"]
    assert chips["ct_l1"] == "Normal"
    assert chips["ct_l3"] == "Normal"

    alert = db_session.query(Alert).filter(Alert.cleared_at.is_(None)).first()
    assert alert is not None
    assert alert.type == "ct_polarity_incorrect"
    assert alert.phase == "L2"
    assert alert.severity == "Incorrect connection"


def test_rule1_all_cts_reversed(db_session):
    """
    If all three phases have negative power, note 'all CTs reversed or reverse power flow'.
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    faulty_payload = dict(SAMPLE_NORMAL_PAYLOAD)
    faulty_payload["kw1"] = -1.64
    faulty_payload["kw2"] = -1.58
    faulty_payload["kw3"] = -1.76
    faulty_payload["t_kw"] = round(faulty_payload["kw1"] + faulty_payload["kw2"] + faulty_payload["kw3"], 2)

    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, faulty_payload, now, db_session)

    assert status == "Incorrect connection"
    assert "All CTs reversed" in chips["ct_l1_detail"]


def test_rule2_ct_disconnected_vs_stopped_motor(db_session):
    """
    Rule 2: Voltage present, i_n < 0.05 A, at least one other active.
    If all 3 currents ~0, motor is stopped (NOT a fault).
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    # Case A: CT L3 disconnected (i3 = 0.01 A, i1 and i2 are active)
    payload_ct_off = dict(SAMPLE_NORMAL_PAYLOAD)
    payload_ct_off["i3"] = 0.01
    payload_ct_off["kw3"] = 0.00
    payload_ct_off["t_kw"] = round(payload_ct_off["kw1"] + payload_ct_off["kw2"], 2)

    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, payload_ct_off, now, db_session)

    assert status == "Disconnected"
    assert chips["ct_l3"] == "Disconnected"
    assert "disconnected" in chips["ct_l3_detail"].lower()
    assert chips["ct_l1"] == "Normal"

    # Reset engine
    engine2 = FaultEngine()
    # Case B: All three currents near zero (Motor stopped / idle)
    payload_stopped = dict(SAMPLE_NORMAL_PAYLOAD)
    payload_stopped["i1"] = 0.02
    payload_stopped["i2"] = 0.01
    payload_stopped["i3"] = 0.01
    payload_stopped["kw1"] = 0.0
    payload_stopped["kw2"] = 0.0
    payload_stopped["kw3"] = 0.0
    payload_stopped["t_kw"] = 0.0

    for _ in range(3):
        status, chips = engine2.evaluate_reading(dev, prof, None, payload_stopped, now, db_session)

    assert status == "Normal"
    assert chips["ct_l1"] == "Normal"
    assert chips["ct_l2"] == "Normal"
    assert chips["ct_l3"] == "Normal"


def test_rule3_ct_swap_connection_incorrect(db_session):
    """
    Rule 3: Phase swap (PF differs from median of other two by > 0.25).
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    payload_swap = dict(SAMPLE_NORMAL_PAYLOAD)
    # pf1 = 0.82, pf3 = 0.80. If pf2 = 0.40, diff from 0.81 is 0.41 > 0.25
    payload_swap["pf2"] = 0.40

    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, payload_swap, now, db_session)

    assert status == "Warning"
    assert chips["ct_l2"] == "Warning"
    assert "phase swap" in chips["ct_l2_detail"]


def test_rule5_voltage_clip_disconnected(db_session):
    """
    Rule 5: Voltage on phase drops below 50 V while device is online.
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    payload_clip = dict(SAMPLE_NORMAL_PAYLOAD)
    payload_clip["v1n"] = 12.4  # Clip fallen off

    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, payload_clip, now, db_session)

    assert status == "Disconnected"
    assert chips["vclip_l1"] == "Disconnected"
    assert "disconnected" in chips["vclip_l1_detail"].lower()


def test_rule6_voltage_connection_incorrect(db_session):
    """
    Rule 6: Line-to-line voltage differs from sqrt(3)*line-to-neutral by > 6%.
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    # v1n = 240 V -> ideal v12 = ~415.7 V. Set v12 = 320 V (>20% error)
    payload_vll = dict(SAMPLE_NORMAL_PAYLOAD)
    payload_vll["v12"] = 320.0

    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, payload_vll, now, db_session)

    assert status == "Incorrect connection"


def test_rule9_sensor_comm_failure_power_mismatch(db_session):
    """
    Rule 9: t_kw differs from kw1+kw2+kw3 by > 5% + 0.05 kW.
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    payload_err = dict(SAMPLE_NORMAL_PAYLOAD)
    payload_err["kw1"] = 1.0
    payload_err["kw2"] = 1.0
    payload_err["kw3"] = 1.0
    payload_err["t_kw"] = 10.0  # Big mismatch (10 vs 3)

    for _ in range(3):
        status, chips = engine.evaluate_reading(dev, prof, None, payload_err, now, db_session)

    assert status == "Communication failure"


def test_debounce_clear_logic(db_session):
    """
    Verify that after raising an alert (3 bad samples), 3 good samples clear the alert.
    """
    engine = FaultEngine()
    dev = db_session.query(Device).first()
    prof = dev.profile
    now = datetime.now(timezone.utc)

    bad_payload = dict(SAMPLE_NORMAL_PAYLOAD)
    bad_payload["kw1"] = -2.0

    # 3 bad samples -> alert raised
    for _ in range(3):
        engine.evaluate_reading(dev, prof, None, bad_payload, now, db_session)

    open_alert = db_session.query(Alert).filter(Alert.cleared_at.is_(None)).first()
    assert open_alert is not None

    # 2 good samples -> still clearing (debounce not yet reached)
    for _ in range(2):
        engine.evaluate_reading(dev, prof, None, SAMPLE_NORMAL_PAYLOAD, now, db_session)
    assert db_session.query(Alert).filter(Alert.cleared_at.is_(None)).count() == 1

    # 3rd good sample -> alert cleared
    status, chips = engine.evaluate_reading(dev, prof, None, SAMPLE_NORMAL_PAYLOAD, now, db_session)
    assert status == "Normal"
    assert db_session.query(Alert).filter(Alert.cleared_at.is_(None)).count() == 0
