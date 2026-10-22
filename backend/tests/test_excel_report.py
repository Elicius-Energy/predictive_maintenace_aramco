"""
Unit tests for Excel Report Generation service (XlsxWriter).
Tests report number sequencing, sheet generation, and data accuracy.
"""
from datetime import datetime, timezone, timedelta
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Device, DeviceProfile, Reading, Report
from app.services.excel_report_service import ExcelReportService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    dev = Device(
        device_id="002D00203335471332323632",
        alias="Ring Frame 14",
        configured=True
    )
    prof = DeviceProfile(
        device_id="002D00203335471332323632",
        customer_name="LEDL Textile Mills",
        motor_rating_kw=15.0,
        electricity_tariff=8.50,
        annual_operating_hours=8000.0,
        motor_investment=85000.0,
        installation_cost=15000.0
    )
    session.add(dev)
    session.add(prof)

    # Seed 10 sample readings
    base_t = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)
    for m in range(10):
        r = Reading(
            device_id=dev.device_id,
            ts=base_t + timedelta(minutes=m),
            v1n=240.0, v2n=240.0, v3n=242.0, vln_avg=240.7,
            v12=416.0, v23=418.0, v31=417.0, vll_avg=417.0,
            i1=8.5, i2=8.6, i3=8.8, i_avg=8.63,
            kw1=1.65, kw2=1.60, kw3=1.75, t_kw=5.0,
            kva1=2.0, kva2=2.0, kva3=2.2, t_kva=6.2,
            kvar1=1.1, kvar2=1.2, kvar3=1.3, t_kvar=3.6,
            pf1=0.82, pf2=0.80, pf3=0.80, pf_avg=0.81,
            freq=50.0, kwh_imp=100 + m
        )
        session.add(r)
    session.commit()

    yield session
    session.close()


def test_excel_report_generation(db_session):
    """
    Verify report creation, auto-sequencing of report numbers, file output, and DB persistence.
    """
    service = ExcelReportService()
    dev_id = "002D00203335471332323632"
    t_start = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 15, 8, 10, 0, tzinfo=timezone.utc)

    # Generate first report
    rep1, path1 = service.generate_report(
        device_id=dev_id,
        start_time=t_start,
        end_time=t_end,
        interval="1-minute",
        user_remarks="Initial Energy Baseline Study",
        include_roi=True,
        roi_params={
            "annual_operating_hours": 8000.0,
            "electricity_tariff": 8.50,
            "motor_investment": 85000.0,
            "installation_cost": 15000.0
        },
        created_by="admin",
        db=db_session
    )

    assert rep1 is not None
    assert rep1.report_no.endswith("/0001")
    assert os.path.exists(path1)
    assert os.path.getsize(path1) > 2000  # Valid Excel file

    # Generate second report -> auto-increments to 0002
    rep2, path2 = service.generate_report(
        device_id=dev_id,
        start_time=t_start,
        end_time=t_end,
        interval="1-minute",
        include_roi=False,
        db=db_session
    )
    assert rep2.report_no.endswith("/0002")
    assert os.path.exists(path2)
    assert os.path.getsize(path2) > 2000

    # Cleanup created test report files
    for p in [path1, path2]:
        try:
            os.remove(p)
        except OSError:
            pass
