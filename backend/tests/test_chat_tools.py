"""
Unit tests for safe read-only parameterized chat tools.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Device, DeviceProfile, Reading, Alert, Report
from app.services.rag_service import (
    tool_get_latest_reading,
    tool_get_device_status_and_alerts,
    tool_get_period_summary,
    tool_list_reports,
    tool_compare_periods
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dev = Device(
        device_id="002D00203335471332323632",
        alias="Ring Frame 14",
        status="Normal",
        configured=True
    )
    prof = DeviceProfile(device_id="002D00203335471332323632", motor_rating_kw=15.0)
    session.add(dev)
    session.add(prof)

    base_t = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)
    for m in range(5):
        session.add(Reading(
            device_id=dev.device_id,
            ts=base_t + timedelta(minutes=m),
            t_kw=10.0,
            vln_avg=240.0,
            i_avg=17.4,
            pf_avg=0.82
        ))
    session.commit()

    yield session
    session.close()


def test_tool_get_latest_reading(db_session):
    res = tool_get_latest_reading("002D00203335471332323632", db_session)
    assert res["device_id"] == "002D00203335471332323632"
    assert res["total_kw"] == 10.0
    assert res["voltage_avg"] == 240.0


def test_tool_get_device_status_and_alerts(db_session):
    res = tool_get_device_status_and_alerts("002D00203335471332323632", db_session)
    assert res["overall_status"] == "Normal"
    assert res["active_alerts_count"] == 0


def test_tool_get_period_summary(db_session):
    res = tool_get_period_summary(
        "002D00203335471332323632",
        "2026-10-15T08:00:00Z",
        "2026-10-15T08:04:00Z",
        db_session
    )
    assert res["energy_kwh"] > 0.0
    assert res["avg_kw"] == 10.0


def test_tool_compare_periods(db_session):
    res = tool_compare_periods(
        "002D00203335471332323632",
        "2026-10-15T08:00:00Z", "2026-10-15T08:02:00Z",
        "2026-10-15T08:02:00Z", "2026-10-15T08:04:00Z",
        db_session
    )
    assert "period_a" in res
    assert "period_b" in res
    assert "energy_delta_kwh" in res
