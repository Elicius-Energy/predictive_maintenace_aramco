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
from app.db.models import Device, DeviceProfile, Reading, Report, PowerStudy
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

    import openpyxl
    wb1 = openpyxl.load_workbook(path1)
    assert "Energy Reading Report" in wb1.sheetnames
    assert "Energy Saving & ROI" in wb1.sheetnames
    assert "Analysis" in wb1.sheetnames
    assert "Data" in wb1.sheetnames
    assert "Data Summery sheet" in wb1.sheetnames
    assert "Charts" in wb1.sheetnames

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


def test_excel_report_before_study_dropdown_wrapping_and_full_ai_summary(db_session, monkeypatch):
    """
    Verify:
    1. Selecting a recorded PowerStudy (e.g. LEDL0001) for 'before_study_id' populates
       Before Motor Consumption (kWh/hr) on 'Energy Saving & ROI' and cites LEDL0001 + Customer Name.
    2. Cells across sheets have wrap_text enabled and dynamic row heights so multi-line text
       (Observed duty pattern, Observations/Remarks, and AI Power Study Summary) is never clipped/hidden.
    3. AI summary is fully visible (both on 'Energy Reading Report' and 'AI Insights' sheet) with
       sufficient row height to display the entire multi-line summary.
    """
    import openpyxl

    dev_id = "002D00203335471332323632"
    t_start = datetime(2026, 10, 15, 8, 0, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 10, 15, 8, 10, 0, tzinfo=timezone.utc)

    # Create a completed Before PowerStudy (LEDL0001) with measured 14.5 kWh/hr
    before_study = PowerStudy(
        study_code="LEDL0001",
        device_id=dev_id,
        customer_name="LEDL Textile Mills",
        status="completed",
        started_at=t_start - timedelta(days=1),
        stopped_at=t_end - timedelta(days=1),
        duration_seconds=600,
        energy_kwh=2.42,
        running_hours=0.167,
        avg_kw=14.5,
        kwh_per_running_hour=14.5,
        started_by="admin",
        stopped_by="admin",
    )
    db_session.add(before_study)
    db_session.commit()
    db_session.refresh(before_study)

    long_ai_text = "\n".join([
        f"• Executive Insight Line {i}: Measured active power averaged 5.00 kW across the study period with significant IE4 right-sizing and VFD optimization potential."
        for i in range(1, 16)
    ])
    service = ExcelReportService()
    monkeypatch.setattr(
        service,
        "_generate_ai_report_summary",
        lambda *args, **kwargs: long_ai_text,
    )

    rep, path = service.generate_report(
        device_id=dev_id,
        start_time=t_start,
        end_time=t_end,
        interval="1-minute",
        user_remarks="Line 1 of engineer remarks.\nLine 2 of engineer remarks with detailed mechanical observations.\nLine 3 of engineer remarks.",
        include_roi=True,
        include_ai_summary=True,
        roi_params={
            "before_study_id": before_study.id,
            "annual_operating_hours": 8000.0,
            "electricity_tariff": 8.50,
            "motor_investment": 85000.0,
            "installation_cost": 15000.0,
        },
        created_by="admin",
        db=db_session,
    )

    try:
        wb = openpyxl.load_workbook(path)
        ws_main = wb["Energy Reading Report"]
        ws_roi = wb["Energy Saving & ROI"]
        ws_ai = wb["AI Insights"]

        # 1. Verify Before Study kWh/hr (14.5) and study code LEDL0001 + customer name on ROI sheet
        assert ws_roi["C4"].value == pytest.approx(14.5, rel=1e-2)
        baseline_note = str(ws_roi["C19"].value or "")
        assert "LEDL0001" in baseline_note
        assert "LEDL Textile Mills" in baseline_note

        # 2. Verify wrap_text is enabled on key cells in Energy Reading Report & ROI
        assert ws_main["A5"].alignment.wrap_text is True
        assert ws_main["B6"].alignment.wrap_text is True
        assert ws_main["C6"].alignment.wrap_text is True
        assert ws_roi["C19"].alignment.wrap_text is True

        # 3. Verify AI Summary is present and fully visible (not hidden in a tiny fixed box)
        # Check on AI Insights sheet: total height allocated to the AI summary rows must be >= 240pt for 15 lines
        ai_found_on_ai_sheet = False
        ai_total_height_ai_sheet = 0.0
        for row_idx in range(1, ws_ai.max_row + 1):
            for col_idx in range(1, ws_ai.max_column + 1):
                val = ws_ai.cell(row=row_idx, column=col_idx).value
                if isinstance(val, str) and "Executive Insight Line 1:" in val and "Executive Insight Line 15:" in val:
                    ai_found_on_ai_sheet = True
                    assert ws_ai.cell(row=row_idx, column=col_idx).alignment.wrap_text is True
                    # Sum row heights covering the AI summary block
                    for r_h in range(row_idx, min(row_idx + 5, ws_ai.max_row + 1)):
                        h = ws_ai.row_dimensions[r_h].height
                        if h:
                            ai_total_height_ai_sheet += h
        assert ai_found_on_ai_sheet is True
        assert ai_total_height_ai_sheet >= 240.0

        # Check that the AI summary is also visible on the main Energy Reading Report sheet
        ai_found_on_main_sheet = False
        for row_idx in range(1, ws_main.max_row + 1):
            for col_idx in range(1, ws_main.max_column + 1):
                val = ws_main.cell(row=row_idx, column=col_idx).value
                if isinstance(val, str) and "Executive Insight Line 1:" in val and "Executive Insight Line 15:" in val:
                    ai_found_on_main_sheet = True
                    assert ws_main.cell(row=row_idx, column=col_idx).alignment.wrap_text is True
                    row_h = ws_main.row_dimensions[row_idx].height or 0
                    assert row_h >= 240.0
        assert ai_found_on_main_sheet is True
    finally:
        if os.path.exists(path):
            os.remove(path)

