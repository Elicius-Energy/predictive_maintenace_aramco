"""
Unit tests for Ingestion idempotency, batch processing, auto-registration, and timestamp validation.
"""
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Device, Reading
from app.services.ingest_service import IngestService

SAMPLE_READING = {
    "dID": "002D00203335471332323632",
    "dTS": 1792076074,
    "fw_ver": "13.4",
    "v1n": 240.01, "v2n": 240.33, "v3n": 245.02, "vln_avg": 241.78,
    "v12": 416.58, "v23": 421.17, "v31": 418.63, "vll_avg": 418.79,
    "i1": 8.28, "i2": 8.54, "i3": 8.98, "i_avg": 8.6,
    "kw1": 1.64, "kw2": 1.58, "kw3": 1.76, "t_kw": 4.97,
    "kvar1": 1.13, "kvar2": 1.32, "kvar3": 1.32, "t_kvar": 3.76,
    "kva1": 1.99, "kva2": 2.05, "kva3": 2.2, "t_kva": 6.24,
    "pf1": 0.82, "pf2": 0.77, "pf3": 0.8, "pf_avg": 0.8, "freq": 50.0,
    "kwh_imp": 134, "kwh_exp": 0, "kvarh_imp": 99, "kvarh_exp": 0, "t_kvah": 167,
    "md_kw": 5.38, "md_kvar": 4.17, "md_kva": 6.77
}


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    # Register the test device
    dev = Device(
        device_id="002D00203335471332323632",
        alias="Sample Motor",
        status="Normal",
        configured=True
    )
    session.add(dev)
    session.commit()
    yield session
    session.close()


def test_single_ingest_and_idempotency(db_session):
    """
    Verify that posting the same reading twice results in 1 inserted, 1 duplicate.
    Never overwrites or duplicates readings.
    """
    service = IngestService()

    # First ingest
    res1 = service.process_payload(SAMPLE_READING, db_session)
    assert res1["inserted"] == 1
    assert res1["duplicate"] == 0
    assert res1["rejected"] == 0
    assert db_session.query(Reading).count() == 1

    # Second ingest of exact same packet (replay)
    res2 = service.process_payload(SAMPLE_READING, db_session)
    assert res2["inserted"] == 0
    assert res2["duplicate"] == 1
    assert res2["rejected"] == 0
    assert db_session.query(Reading).count() == 1


def test_batch_ingest_and_backfill(db_session):
    """
    Verify batch ingestion supports up to 1000 readings and maintains idempotency.
    """
    service = IngestService()
    base_ts = 1792070000

    # Create 50 consecutive readings
    batch = []
    for i in range(50):
        item = dict(SAMPLE_READING)
        item["dTS"] = base_ts + (i * 60)
        batch.append(item)

    res = service.process_payload(batch, db_session)
    assert res["inserted"] == 50
    assert res["duplicate"] == 0
    assert db_session.query(Reading).count() == 50

    # Re-sending 25 existing + 25 new
    mixed_batch = []
    for i in range(25, 75):
        item = dict(SAMPLE_READING)
        item["dTS"] = base_ts + (i * 60)
        mixed_batch.append(item)

    res_mixed = service.process_payload(mixed_batch, db_session)
    assert res_mixed["inserted"] == 25
    assert res_mixed["duplicate"] == 25
    assert db_session.query(Reading).count() == 75


def test_unknown_device_is_rejected(db_session):
    """
    Unknown dID starting to post data must be rejected because manual registration is required.
    """
    service = IngestService()
    new_device_payload = dict(SAMPLE_READING)
    new_device_payload["dID"] = "999999999999999999999999"

    res = service.process_payload(new_device_payload, db_session)
    assert res["rejected"] == 1
    assert res["inserted"] == 0

    dev = db_session.query(Device).filter(Device.device_id == "999999999999999999999999").first()
    assert dev is None


def test_timestamp_validation_rejects_out_of_bounds(db_session):
    """
    Reject dTS before 2020 or more than 24h in the future.
    """
    service = IngestService()

    # Before 2020 (e.g. year 2018 -> epoch ~1520000000)
    old_payload = dict(SAMPLE_READING)
    old_payload["dTS"] = 1520000000
    res_old = service.process_payload(old_payload, db_session)
    assert res_old["rejected"] == 1
    assert res_old["inserted"] == 0

    # Way in future (> 24h future)
    future_ts = int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp())
    future_payload = dict(SAMPLE_READING)
    future_payload["dTS"] = future_ts
    res_future = service.process_payload(future_payload, db_session)
    assert res_future["rejected"] == 1
    assert res_future["inserted"] == 0
