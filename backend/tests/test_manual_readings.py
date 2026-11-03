"""
Unit tests for Manual Physical Motor Measurements (Temperature & RPM).
Tests nearest row timestamp matching, database persistence, and empty row preservation.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.models import Device, DeviceProfile, Reading, User
from app.main import app
from app.api.auth import create_access_token


@pytest.fixture
def test_setup():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create admin user
    admin = User(username="admin", password_hash="dummy", role="admin")
    session.add(admin)

    # Create device
    dev = Device(device_id="002D00203335471332323632", alias="Test Motor", configured=True)
    session.add(dev)

    # Create 5 readings spaced 1 minute apart from 10:00 to 10:04
    base_t = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)
    for m in range(5):
        r = Reading(
            device_id=dev.device_id,
            ts=base_t + timedelta(minutes=m),
            t_kw=5.0,
            temperature=None,
            rpm=None
        )
        session.add(r)
    session.commit()

    yield session, dev.device_id, base_t
    session.close()


def test_nearest_timestamp_manual_recording(test_setup):
    session, dev_id, base_t = test_setup

    # Test direct DB logic: query target at 10:02:15 -> nearest should be 10:02:00
    target_dt = base_t + timedelta(minutes=2, seconds=15)

    reading_before = (
        session.query(Reading)
        .filter(Reading.device_id == dev_id, Reading.ts <= target_dt)
        .order_by(Reading.ts.desc())
        .first()
    )
    reading_after = (
        session.query(Reading)
        .filter(Reading.device_id == dev_id, Reading.ts >= target_dt)
        .order_by(Reading.ts.asc())
        .first()
    )

    dt_before = abs((target_dt - reading_before.ts.replace(tzinfo=timezone.utc)).total_seconds())
    dt_after = abs((reading_after.ts.replace(tzinfo=timezone.utc) - target_dt).total_seconds())
    nearest = reading_before if dt_before <= dt_after else reading_after

    assert (nearest.ts if nearest.ts.tzinfo else nearest.ts.replace(tzinfo=timezone.utc)) == base_t + timedelta(minutes=2)

    # Record values
    nearest.temperature = 54.5
    nearest.rpm = 1485.0
    session.commit()

    # Verify nearest row has values
    row_1002 = session.query(Reading).filter(Reading.device_id == dev_id, Reading.ts == base_t + timedelta(minutes=2)).first()
    assert row_1002.temperature == 54.5
    assert row_1002.rpm == 1485.0

    # Verify all other rows remain empty (None)
    other_rows = session.query(Reading).filter(Reading.device_id == dev_id, Reading.ts != base_t + timedelta(minutes=2)).all()
    assert len(other_rows) == 4
    for r in other_rows:
        assert r.temperature is None
        assert r.rpm is None
