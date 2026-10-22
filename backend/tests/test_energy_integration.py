"""
Unit tests for trapezoidal energy integration with gaps and energy-weighted PF.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Device, DeviceProfile, Reading
from app.services.query_service import QueryService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dev = Device(
        device_id="002D00203335471332323632",
        alias="Test Motor",
        expected_interval_s=60,
        configured=True
    )
    prof = DeviceProfile(
        device_id="002D00203335471332323632",
        motor_rating_kw=15.0,
        idle_threshold_kw=0.75
    )
    session.add(dev)
    session.add(prof)
    session.commit()

    yield session
    session.close()


def test_trapezoidal_energy_integration_constant_power(db_session):
    """
    Constant power of 10 kW for 1 hour (60 samples at 60s intervals) must equal exactly 10.0 kWh.
    """
    service = QueryService()
    dev_id = "002D00203335471332323632"
    base_time = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)

    # Insert 61 readings (0 to 60 minutes) at 10.0 kW
    for i in range(61):
        ts = base_time + timedelta(minutes=i)
        r = Reading(
            device_id=dev_id,
            ts=ts,
            t_kw=10.0,
            t_kva=12.5,
            pf_avg=0.80,
            vln_avg=240.0,
            i_avg=17.4,
            kwh_imp=100 + i // 6
        )
        db_session.add(r)
    db_session.commit()

    end_time = base_time + timedelta(minutes=60)
    summary = service.get_period_summary(dev_id, base_time, end_time, db_session)

    # 10 kW * 1 hour = 10.0 kWh
    assert abs(summary["energy_kwh"] - 10.0) < 0.05
    assert summary["duration_hours"] == 1.0
    assert summary["avg_kw"] == 10.0
    assert summary["running_hours"] == 1.0
    assert summary["idle_hours"] == 0.0


def test_energy_integration_treats_gaps_without_interpolation(db_session):
    """
    If a gap > 3x interval (e.g. 180s) occurs (e.g. 2 hours outage),
    it must NOT interpolate power across the gap.
    """
    service = QueryService()
    dev_id = "002D00203335471332323632"
    t0 = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)

    # Sample 1: 08:00 (10 kW)
    db_session.add(Reading(device_id=dev_id, ts=t0, t_kw=10.0, t_kva=12.5, pf_avg=0.80, vln_avg=240.0, i_avg=17.4))
    # Sample 2: 08:01 (10 kW) -> 1 minute of 10 kW = 0.1667 kWh
    db_session.add(Reading(device_id=dev_id, ts=t0 + timedelta(minutes=1), t_kw=10.0, t_kva=12.5, pf_avg=0.80, vln_avg=240.0, i_avg=17.4))

    # OUTAGE FOR 1 HOUR: gap is 60 minutes (> 3 minutes)
    t_after_outage = t0 + timedelta(minutes=61)
    # Sample 3: 09:01 (10 kW)
    db_session.add(Reading(device_id=dev_id, ts=t_after_outage, t_kw=10.0, t_kva=12.5, pf_avg=0.80, vln_avg=240.0, i_avg=17.4))
    # Sample 4: 09:02 (10 kW) -> 1 minute of 10 kW = 0.1667 kWh
    db_session.add(Reading(device_id=dev_id, ts=t_after_outage + timedelta(minutes=1), t_kw=10.0, t_kva=12.5, pf_avg=0.80, vln_avg=240.0, i_avg=17.4))
    db_session.commit()

    summary = service.get_period_summary(dev_id, t0, t_after_outage + timedelta(minutes=1), db_session)

    # If it interpolated across the 60-min gap, energy would be ~10 kWh.
    # Because gap was preserved, energy is only 2 minutes = 0.33 kWh!
    assert summary["energy_kwh"] < 1.0
    assert abs(summary["energy_kwh"] - 0.33) < 0.05


def test_energy_weighted_power_factor(db_session):
    """
    Weighted PF = kWh / kVAh.
    Verify that weighted PF correctly reflects energy weighting.
    """
    service = QueryService()
    dev_id = "002D00203335471332323632"
    t0 = datetime(2026, 10, 15, 10, 0, 0, tzinfo=timezone.utc)

    # 30 mins at 10 kW, 12.5 kVA (PF = 0.80) -> 5 kWh, 6.25 kVAh
    for m in range(31):
        db_session.add(Reading(
            device_id=dev_id,
            ts=t0 + timedelta(minutes=m),
            t_kw=10.0,
            t_kva=12.5,
            pf_avg=0.80,
            vln_avg=240.0,
            i_avg=17.4
        ))

    # 30 mins at 2 kW, 4 kVA (PF = 0.50) -> 1 kWh, 2 kVAh
    t1 = t0 + timedelta(minutes=30)
    for m in range(1, 31):
        db_session.add(Reading(
            device_id=dev_id,
            ts=t1 + timedelta(minutes=m),
            t_kw=2.0,
            t_kva=4.0,
            pf_avg=0.50,
            vln_avg=240.0,
            i_avg=5.5
        ))
    db_session.commit()

    summary = service.get_period_summary(dev_id, t0, t1 + timedelta(minutes=30), db_session)
    # Total kWh = 5 + 1 = 6 kWh
    # Total kVAh = 6.25 + 2.0 = 8.25 kVAh
    # Weighted PF = 6 / 8.25 = 0.727 (approx 0.73)
    # Arithmetic mean PF would be (0.80 + 0.50) / 2 = 0.65
    assert abs(summary["weighted_pf"] - 0.73) < 0.02
    assert summary["weighted_pf"] > summary["avg_pf"]
