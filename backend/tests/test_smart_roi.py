"""
Unit tests for Smart ROI calculation service and endpoints.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Device, DeviceProfile, Reading
from app.services.smart_roi_service import (
    calculate_roi_metrics,
    get_smart_roi_context,
)
from app.services.web_search_service import search_web_for_motor_roi


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dev = Device(
        device_id="test_motor_22kw",
        alias="Main Air Compressor Motor",
        configured=True
    )
    prof = DeviceProfile(
        device_id="test_motor_22kw",
        customer_name="Lakshmi Electrical Drives Ltd",
        motor_rating_kw=22.0,
        rated_efficiency_pct=90.0,
        electricity_tariff=10.0,
        annual_operating_hours=4500.0,
        motor_investment=55000.0,
        installation_cost=5000.0
    )
    session.add(dev)
    session.add(prof)

    base_t = datetime(2026, 10, 28, 5, 0, 0, tzinfo=timezone.utc)
    for i in range(20):
        r = Reading(
            device_id=dev.device_id,
            ts=base_t + timedelta(minutes=i),
            t_kw=4.72,
            vll_avg=415.0,
            i_avg=8.2,
            pf_avg=0.82,
            freq=50.0,
            kwh_imp=100 + i * 0.08
        )
        session.add(r)
    session.commit()

    yield session
    session.close()


def test_calculate_roi_metrics():
    res = calculate_roi_metrics(
        avg_kw=4.72,
        current_eff=90.0,
        candidate_eff=94.5,
        candidate_kw=22.0,
        rated_kw=22.0,
        annual_hours=4500.0,
        tariff=10.0,
        motor_investment=55000.0,
        installation_cost=5000.0,
    )
    assert res["saving_kw"] > 0.2
    assert res["annual_saving_kwh"] > 900
    assert res["annual_saving_cost"] > 9000
    assert res["simple_payback_years"] > 0
    assert res["co2_reduction_tons"] > 0


def test_get_smart_roi_context(test_db):
    context = get_smart_roi_context("test_motor_22kw", test_db)
    assert context["device"]["motor_rating_kw"] == 22.0
    assert context["telemetry_metrics"]["loading_pct"] < 30.0  # ~21.5% underloaded
    assert len(context["presets"]) >= 3
    # Check that presets include IE3, IE4, and Right-Sizing
    preset_ids = [p["id"] for p in context["presets"]]
    assert "ie3_upgrade" in preset_ids
    assert "ie4_upgrade" in preset_ids
    assert "right_size_ie4" in preset_ids


def test_web_search_helper():
    sources = search_web_for_motor_roi("22 kW IE4 motor price India", 22.0)
    assert len(sources) >= 1
    assert "22.0 kW" in sources[0]["title"] or "22 kW" in sources[0]["title"] or "Price" in sources[0]["title"]

