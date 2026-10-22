"""
Excel Report Generation Service for LEDL Motor Energy Monitoring.
Generates comprehensive 5-sheet workbooks conforming to the LEDL Motor Energy Reading Report standard,
featuring native Excel charts, live formulas for ROI, and print-ready A4 landscape styling.
"""
import os
import logging
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import xlsxwriter
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.config import settings
from app.db.models import Device, DeviceProfile, Reading, Report, Alert
from app.services.query_service import query_service
from app.services.rag_service import rag_service

IST = timezone(timedelta(hours=5, minutes=30))
logger = logging.getLogger(__name__)


def _json_safe(value: Any) -> Any:
    """Convert nested report values to JSON-compatible primitives."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value

def _to_ist_str(dt_or_iso: Any) -> str:
    if not dt_or_iso:
        return ""
    if isinstance(dt_or_iso, str):
        try:
            dt = datetime.fromisoformat(dt_or_iso.replace("Z", "+00:00"))
        except Exception:
            return dt_or_iso
    elif isinstance(dt_or_iso, datetime):
        dt = dt_or_iso
    else:
        return str(dt_or_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")


class ExcelReportService:
    """Generates professional Microsoft Excel reports using XlsxWriter."""

    def generate_report(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        user_remarks: str = "",
        include_roi: bool = True,
        include_ai_summary: bool = False,
        roi_params: Optional[Dict[str, Any]] = None,
        created_by: str = "admin",
        db: Session = None
    ) -> Tuple[Report, str]:
        """
        Generate complete Excel workbook with all 5 sheets and save to disk.
        Returns: (Report ORM instance, file_path)
        """
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")
        profile = device.profile or DeviceProfile(device_id=device_id)

        # 1. Generate Report Number: LEDL/ER/YYYY/XXXX
        year = datetime.now(timezone.utc).year
        last_report = (
            db.query(Report)
            .filter(Report.report_no.like(f"LEDL/ER/{year}/%"))
            .order_by(desc(Report.id))
            .first()
        )
        seq = 1
        if last_report and last_report.report_no:
            try:
                parts = last_report.report_no.split("/")
                seq = int(parts[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        report_no = f"LEDL/ER/{year}/{seq:04d}"

        # 2. Compute study summary and telemetry points
        summary = query_service.get_period_summary(device_id, start_time, end_time, db)
        summary["nameplate_duty"] = profile.motor_duty or None
        trends_data = query_service.get_trend_charts(device_id, start_time, end_time, interval, db)
        points = trends_data.get("points", [])

        # Alerts in period
        alerts = (
            db.query(Alert)
            .filter(
                Alert.device_id == device_id,
                Alert.started_at <= end_time,
                (Alert.cleared_at.is_(None) | (Alert.cleared_at >= start_time))
            )
            .all()
        )

        # Auto-generated observations
        auto_obs = []
        if profile.rated_efficiency_pct is not None and profile.rated_efficiency_pct < 85:
            auto_obs.append(f"Nameplate rated efficiency is {profile.rated_efficiency_pct:.2f}%; assess replacement options using measured load and a verified candidate efficiency.")
        if summary.get("weighted_pf") is not None and summary["weighted_pf"] < 0.85:
            auto_obs.append(f"Energy-weighted Power Factor ({summary.get('weighted_pf'):.2f}) is below the recommended 0.85 threshold. Capacitor bank optimization advised.")
        if summary.get("voltage_unbalance_pct") is not None and summary["voltage_unbalance_pct"] > 2.0:
            auto_obs.append(f"Voltage unbalance ({summary.get('voltage_unbalance_pct'):.1f}%) exceeds the 2.0% IEEE guideline. Check supply phase loading.")
        if summary.get("current_unbalance_pct") is not None and summary["current_unbalance_pct"] > 10.0:
            auto_obs.append(f"Current unbalance is high ({summary.get('current_unbalance_pct'):.1f}%). Motor winding temperature derating recommended.")
        if summary.get("idle_pct") is not None and summary.get("idle_pct", 0.0) > 20.0:
            auto_obs.append(f"Motor spent {summary.get('idle_pct'):.1f}% of study period idle ({summary.get('idle_hours'):.1f} hours). Interlocking or auto-sleep control recommended.")
        if summary.get("data_completeness_pct") is not None and summary.get("data_completeness_pct", 100.0) < 95.0:
            auto_obs.append(f"Telemetry data completeness was {summary.get('data_completeness_pct'):.1f}%. Telemetry communication gaps were observed.")

        # ROI Before / After parameters
        roi_data = {}
        roi_data = self._compute_roi_data(device_id, start_time, end_time, summary, profile, roi_params or {}, db)

        replacement_analysis = self._calculate_replacement_scenarios(summary, profile, roi_data)
        ai_summary = None
        if include_ai_summary:
            ai_summary = self._generate_ai_report_summary(
                device, profile, summary, auto_obs, replacement_analysis, start_time, end_time, db
            )

        # 3. Create Excel File on disk
        reports_dir = Path(settings.REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"Motor_Energy_Report_{device_id[-6:]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path = str(reports_dir / filename)

        workbook = xlsxwriter.Workbook(file_path, {"remove_timezone": True})

        # Workbook formatting styles (LEDL Navy palette)
        NAVY = "#1F3A8A"
        LIGHT_BG = "#F8FAFC"
        BORDER_COLOR = "#CBD5E1"

        fmt_title = workbook.add_format({
            "bold": True, "font_size": 16, "font_color": "white",
            "bg_color": NAVY, "align": "center", "valign": "vcenter"
        })
        fmt_subtitle = workbook.add_format({
            "bold": True, "font_size": 12, "font_color": "white",
            "bg_color": NAVY, "align": "center", "valign": "vcenter"
        })
        fmt_section = workbook.add_format({
            "bold": True, "font_size": 11, "font_color": "white",
            "bg_color": NAVY, "align": "left", "valign": "vcenter", "border": 1, "border_color": BORDER_COLOR
        })
        fmt_header = workbook.add_format({
            "bold": True, "font_size": 10, "bg_color": "#E2E8F0",
            "border": 1, "border_color": BORDER_COLOR, "align": "center", "valign": "vcenter"
        })
        fmt_cell = workbook.add_format({
            "font_size": 10, "border": 1, "border_color": BORDER_COLOR, "valign": "vcenter"
        })
        fmt_cell_bold = workbook.add_format({
            "bold": True, "font_size": 10, "border": 1, "border_color": BORDER_COLOR, "valign": "vcenter"
        })
        fmt_num = workbook.add_format({
            "font_size": 10, "border": 1, "border_color": BORDER_COLOR, "num_format": "#,##0.00", "align": "right", "valign": "vcenter"
        })
        fmt_num_int = workbook.add_format({
            "font_size": 10, "border": 1, "border_color": BORDER_COLOR, "num_format": "#,##0", "align": "right", "valign": "vcenter"
        })
        fmt_pct = workbook.add_format({
            "font_size": 10, "border": 1, "border_color": BORDER_COLOR, "num_format": "0.0%", "align": "right", "valign": "vcenter"
        })
        fmt_datetime = workbook.add_format({
            "font_size": 10, "border": 1, "border_color": BORDER_COLOR, "num_format": "yyyy-mm-dd hh:mm:ss", "align": "center", "valign": "vcenter"
        })

        # ── SHEET 1: Energy Reading Report (Client Template) ─────────────
        ws1 = workbook.add_worksheet("Energy Reading Report")
        ws1.set_landscape()
        ws1.set_paper(9)  # A4
        ws1.fit_to_pages(1, 0)
        self._write_sheet1_reading_report(
            ws1, workbook, report_no, profile, summary, user_remarks, auto_obs, roi_data,
            fmt_title, fmt_subtitle, fmt_section, fmt_header, fmt_cell, fmt_cell_bold, fmt_num, fmt_datetime
        )

        # ── SHEET 2: Energy Saving & ROI ──────────────────────────────────
        ws2 = workbook.add_worksheet("Energy Saving & ROI")
        ws2.set_landscape()
        self._write_sheet2_roi(
            ws2, workbook, roi_data, profile, replacement_analysis, fmt_title, fmt_section, fmt_header, fmt_cell, fmt_cell_bold, fmt_num, fmt_pct
        )

        if include_ai_summary:
            ws_ai = workbook.add_worksheet("AI Insights")
            ws_ai.set_landscape()
            self._write_ai_summary(
                ws_ai, workbook, ai_summary, replacement_analysis, summary, roi_data,
                fmt_title, fmt_section,
                fmt_header, fmt_cell, fmt_cell_bold, fmt_num
            )

        # ── SHEET 3: Analysis ─────────────────────────────────────────────
        ws3 = workbook.add_worksheet("Analysis")
        ws3.set_landscape()
        self._write_sheet3_analysis(
            ws3, summary, points, alerts, auto_obs, profile,
            fmt_title, fmt_section, fmt_header, fmt_cell, fmt_cell_bold, fmt_num, fmt_pct
        )

        # ── SHEET 4: Data ─────────────────────────────────────────────────
        ws4 = workbook.add_worksheet("Data")
        ws4.freeze_panes(1, 0)
        self._write_sheet4_data(
            ws4, points, fmt_header, fmt_cell, fmt_num, fmt_datetime
        )

        # ── SHEET 5: Charts ───────────────────────────────────────────────
        ws5 = workbook.add_worksheet("Charts")
        self._write_sheet5_charts(
            ws5, workbook, points, len(points)
        )

        workbook.close()

        # 4. Save record to `reports` database table
        config_snapshot = {
            column.name: getattr(profile, column.name)
            for column in DeviceProfile.__table__.columns
            if column.name != "device_id"
        }
        config_snapshot = _json_safe(config_snapshot)

        report_record = Report(
            report_no=report_no,
            device_id=device_id,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "interval": interval,
                "include_roi": include_roi,
                "include_ai_summary": include_ai_summary,
                "user_remarks": user_remarks,
                "roi_params": _json_safe(roi_params or {})
            },
            config_snapshot=config_snapshot,
            summary=_json_safe(summary),
            file_path=file_path
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)

        return report_record, file_path

    def _write_sheet1_reading_report(
        self, ws, wb, report_no, profile, summary, remarks, auto_obs, roi_data,
        f_title, f_sub, f_sec, f_hdr, f_cell, f_bold, f_num, f_dt
    ):
        ws.set_column("A:A", 5)
        ws.set_column("B:B", 24)
        ws.set_column("C:C", 24)
        ws.set_column("D:D", 24)
        ws.set_column("E:E", 24)

        # Header Titles
        ws.merge_range("A1:E1", "LAKSHMI ELECTRICAL DRIVES LTD.", f_title)
        ws.merge_range("A2:E2", "MOTOR ENERGY READING REPORT", f_sub)
        ws.write("B3", "Report No:", f_bold)
        ws.write("C3", report_no, f_cell)
        ws.write("D3", "Date:", f_bold)
        ws.write("E3", datetime.now(timezone.utc).astimezone(IST).strftime("%d-%b-%Y"), f_cell)

        row = 4
        # 1. CUSTOMER INFORMATION
        ws.merge_range(row, 0, row, 4, "1. CUSTOMER INFORMATION", f_sec)
        row += 1
        ws.write(row, 1, "Customer:", f_bold); ws.write(row, 2, profile.customer_name or "", f_cell)
        ws.write(row, 3, "Contact Person:", f_bold); ws.write(row, 4, profile.contact_person or "", f_cell)
        row += 1
        ws.write(row, 1, "Location:", f_bold); ws.write(row, 2, profile.location or "", f_cell)
        ws.write(row, 3, "Contact Number:", f_bold); ws.write(row, 4, profile.contact_number or "", f_cell)
        row += 1
        ws.write(row, 1, "Department:", f_bold); ws.write(row, 2, profile.department or "", f_cell)
        ws.write(row, 3, "", f_cell); ws.write(row, 4, "", f_cell)
        row += 2

        # 2. MOTOR NAME PLATE DETAILS
        ws.merge_range(row, 0, row, 4, "2. MOTOR NAME PLATE DETAILS", f_sec)
        row += 1
        ws.write(row, 1, "Make:", f_bold); ws.write(row, 2, profile.motor_make or "", f_cell)
        ws.write(row, 3, "Motor Rating (kW):", f_bold); ws.write(row, 4, profile.motor_rating_kw if profile.motor_rating_kw is not None else "", f_num if profile.motor_rating_kw is not None else f_cell)
        row += 1
        ws.write(row, 1, "Frame Size:", f_bold); ws.write(row, 2, profile.frame_size or "", f_cell)
        ws.write(row, 3, "Rated Current (Amps):", f_bold); ws.write(row, 4, profile.rated_current_amps if profile.rated_current_amps is not None else "", f_num if profile.rated_current_amps is not None else f_cell)
        row += 1
        ws.write(row, 1, "Rated Speed (RPM):", f_bold); ws.write(row, 2, profile.rated_speed_rpm if profile.rated_speed_rpm is not None else "", f_num if profile.rated_speed_rpm is not None else f_cell)
        ws.write(row, 3, "Rated Voltage (V):", f_bold); ws.write(row, 4, profile.rated_voltage if profile.rated_voltage is not None else "", f_num if profile.rated_voltage is not None else f_cell)
        row += 1
        ws.write(row, 1, "Rated Efficiency (%):", f_bold); ws.write(row, 2, profile.rated_efficiency_pct if profile.rated_efficiency_pct is not None else "", f_num if profile.rated_efficiency_pct is not None else f_cell)
        ws.write(row, 3, "Replacement Motor Efficiency (%):", f_bold); ws.write(row, 4, profile.replacement_motor_efficiency_pct if profile.replacement_motor_efficiency_pct is not None else "", f_num if profile.replacement_motor_efficiency_pct is not None else f_cell)
        row += 1
        ws.write(row, 1, "Connection:", f_bold); ws.write(row, 2, profile.motor_connection or "", f_cell)
        ws.write(row, 3, "Duty:", f_bold); ws.write(row, 4, profile.motor_duty or "", f_cell)
        row += 1
        ws.write(row, 1, "Insulation Class:", f_bold); ws.write(row, 2, profile.insulation_class or "", f_cell)
        ws.write(row, 3, "Motor Type:", f_bold); ws.write(row, 4, profile.motor_type or "", f_cell)
        row += 1
        ws.write(row, 1, "Serial Number:", f_bold); ws.write(row, 2, profile.serial_number or "", f_cell)
        ws.write(row, 3, "", f_cell); ws.write(row, 4, "", f_cell)
        row += 2

        # 3. MACHINE DETAILS
        ws.merge_range(row, 0, row, 4, "3. MACHINE DETAILS", f_sec)
        row += 1
        ws.write(row, 1, "Machine Name:", f_bold); ws.write(row, 2, profile.machine_name or "", f_cell)
        ws.write(row, 3, "Make:", f_bold); ws.write(row, 4, profile.machine_make or "", f_cell)
        row += 1
        ws.write(row, 1, "Model No.:", f_bold); ws.write(row, 2, profile.machine_model_no or "", f_cell)
        ws.write(row, 3, "Count:", f_bold); ws.write(row, 4, profile.machine_count or "", f_cell)
        row += 1
        ws.write(row, 1, "TPI:", f_bold); ws.write(row, 2, profile.machine_tpi or "", f_cell)
        ws.write(row, 3, "Raw Material:", f_bold); ws.write(row, 4, profile.raw_material or "", f_cell)
        row += 1
        ws.write(row, 1, "Machine RPM – Maximum:", f_bold); ws.write(row, 2, profile.machine_rpm_max if profile.machine_rpm_max is not None else "", f_num if profile.machine_rpm_max is not None else f_cell)
        ws.write(row, 3, "Machine RPM – Average:", f_bold); ws.write(row, 4, profile.machine_rpm_avg if profile.machine_rpm_avg is not None else "", f_num if profile.machine_rpm_avg is not None else f_cell)
        row += 1
        ws.write(row, 1, "No. of Spindles:", f_bold); ws.write(row, 2, profile.no_of_spindles if profile.no_of_spindles is not None else "", f_num if profile.no_of_spindles is not None else f_cell)
        row += 2

        # 4. INVERTER DETAILS
        ws.merge_range(row, 0, row, 4, "4. INVERTER DETAILS", f_sec)
        row += 1
        ws.write(row, 1, "Make:", f_bold); ws.write(row, 2, profile.inverter_make or "-", f_cell)
        ws.write(row, 3, "Model:", f_bold); ws.write(row, 4, profile.inverter_model or "-", f_cell)
        row += 2

        # 5. MEASURED ENERGY DATA (Audit Results)
        ws.merge_range(row, 0, row, 4, "5. MEASURED ENERGY DATA", f_sec)
        row += 1
        ws.write(row, 1, "Parameter", f_hdr); ws.write(row, 2, "Average", f_hdr)
        ws.write(row, 3, "Minimum", f_hdr); ws.write(row, 4, "Maximum / Total", f_hdr)
        row += 1

        measured = [
            ("Start Time (IST)", _to_ist_str(summary.get("start_time", "")), "-", "-"),
            ("End Time (IST)", _to_ist_str(summary.get("end_time", "")), "-", "-"),
            ("Analysis Period", summary.get("duration_str", ""), "-", "-"),
            ("Idle Time", summary.get("idle_time_str", ""), "-", "-"),
            ("Energy Consumption (kWh)", f"{summary.get('energy_kwh', 0.0):.2f}" if summary.get("samples_count", 0) else "Not available", "-", "-"),
            ("Active Power (kW)", f"{summary.get('avg_kw'):.2f}" if summary.get("avg_kw") is not None else "Not available", f"{summary.get('min_kw'):.2f}" if summary.get("min_kw") is not None else "-", f"{summary.get('max_kw'):.2f}" if summary.get("max_kw") is not None else "-"),
            ("Voltage (Line-Line, V)", f"{summary.get('avg_voltage'):.1f}" if summary.get("avg_voltage") is not None else "Not available", "-", "-"),
            ("Current (A)", f"{summary.get('avg_current'):.2f}" if summary.get("avg_current") is not None else "Not available", "-", "-"),
            ("Power Factor (Weighted)", f"{summary.get('weighted_pf'):.2f}" if summary.get("weighted_pf") is not None else "Not available", "-", f"Avg: {summary.get('avg_pf'):.2f}" if summary.get("avg_pf") is not None else "-"),
            ("Frequency (Hz)", f"{summary.get('avg_frequency'):.2f}" if summary.get("avg_frequency") is not None else "Not available", "-", "-")
        ]
        for param, avg_val, min_val, max_val in measured:
            ws.write(row, 1, param, f_bold)
            ws.write(row, 2, avg_val, f_cell)
            ws.write(row, 3, min_val, f_cell)
            ws.write(row, 4, max_val, f_cell)
            row += 1
        row += 1

        # Calculated duty classification and measured nameplate loading.
        ws.merge_range(row, 0, row, 4, "POWER STUDY CALCULATIONS", f_sec)
        row += 1
        duty = self._classify_observed_duty(summary)
        ws.write(row, 1, "Observed duty pattern:", f_bold); ws.merge_range(row, 2, row + 1, 4, duty, f_cell)
        row += 1
        rated_kw = profile.motor_rating_kw
        avg_kw = summary.get("avg_kw")
        max_kw = summary.get("max_kw")
        ws.write(row, 1, "Average loading (% of motor rating):", f_bold)
        avg_loading = (avg_kw / rated_kw * 100.0) if avg_kw is not None and rated_kw and rated_kw > 0 else None
        ws.write(row, 2, avg_loading if avg_loading is not None else "Not available", f_num if avg_loading is not None else f_cell)
        ws.write(row, 3, "Maximum loading (%):", f_bold)
        max_loading = (max_kw / rated_kw * 100.0) if max_kw is not None and rated_kw and rated_kw > 0 else None
        ws.write(row, 4, max_loading if max_loading is not None else "Not available", f_num if max_loading is not None else f_cell)
        row += 1
        ws.write(row, 1, "Measured consumption while running:", f_bold)
        ws.write(row, 2, roi_data.get("after_kwh_hr") if roi_data.get("after_kwh_hr") is not None else "Not available", f_num if roi_data.get("after_kwh_hr") is not None else f_cell)
        ws.write(row, 3, "kWh per running hour", f_cell); ws.write(row, 4, "", f_cell)
        row += 2

        # 6. OBSERVATION / REMARKS
        ws.merge_range(row, 0, row, 4, "6. OBSERVATION / REMARKS", f_sec)
        row += 1
        full_remarks = remarks
        if auto_obs:
            auto_str = "Automated Observations:\n" + "\n".join(f"• {o}" for o in auto_obs)
            full_remarks = f"{remarks}\n\n{auto_str}" if remarks else auto_str
        if full_remarks:
            full_remarks = f"{full_remarks}\n\n" if full_remarks else ""
        full_remarks += f"Study window: {_to_ist_str(summary.get('start_time'))} to {_to_ist_str(summary.get('end_time'))} IST. "
        full_remarks += f"Telemetry samples: {summary.get('samples_count', 0)}; data completeness: {summary.get('data_completeness_pct', 'n/a')}%. "
        full_remarks += f"Duty pattern: {duty}"
        ws.merge_range(row, 1, row + 2, 4, full_remarks or "", f_cell)
        row += 4

        # 7. CUSTOMER CONFIRMATION & 8. LEDL REPRESENTATIVE
        ws.merge_range(row, 0, row, 2, "7. CUSTOMER CONFIRMATION", f_sec)
        ws.merge_range(row, 3, row, 4, "8. LEDL REPRESENTATIVE", f_sec)
        row += 1
        ws.write(row, 1, "Name:", f_bold); ws.write(row, 2, profile.signatory_customer_name or "", f_cell)
        ws.write(row, 3, "Name:", f_bold); ws.write(row, 4, profile.rep_name or "", f_cell)
        row += 1
        ws.write(row, 1, "Designation:", f_bold); ws.write(row, 2, profile.signatory_designation or "", f_cell)
        ws.write(row, 3, "Designation:", f_bold); ws.write(row, 4, profile.rep_designation or "", f_cell)
        row += 1
        ws.write(row, 1, "Signature:", f_bold); ws.write(row, 2, "", f_cell)
        ws.write(row, 3, "Signature:", f_bold); ws.write(row, 4, "", f_cell)
        row += 1
        ws.write(row, 1, "Date:", f_bold); ws.write(row, 2, "", f_cell)
        ws.write(row, 3, "Date:", f_bold); ws.write(row, 4, "", f_cell)
        row += 1
    def _write_sheet2_roi(self, ws, wb, roi, profile, scenarios, f_title, f_sec, f_hdr, f_cell, f_bold, f_num, f_pct):
        ws.set_column("A:A", 5)
        ws.set_column("B:B", 35)
        ws.set_column("C:C", 20)
        ws.set_column("D:D", 15)

        ws.merge_range("B1:D1", "ENERGY SAVING & RETURN ON INVESTMENT (ROI)", f_title)

        ws.write("B3", "Parameter", f_hdr)
        ws.write("C3", "Value", f_hdr)
        ws.write("D3", "Unit", f_hdr)

        ws.write("B4", "Before Motor Consumption (kWh/hr):", f_bold)
        before_value = roi.get("before_kwh_hr")
        ws.write("C4", before_value if before_value is not None else "", f_num if before_value is not None else f_cell)
        ws.write("D4", "kWh/hr", f_cell)

        ws.write("B5", "After Motor Consumption (kWh/hr):", f_bold)
        after_value = roi.get("after_kwh_hr")
        ws.write("C5", after_value if after_value is not None else "", f_num if after_value is not None else f_cell)
        ws.write("D5", "kWh/hr", f_cell)

        # Live Excel Formula: Energy Saving = Before - After
        ws.write("B6", "Energy Saving (per hour):", f_bold)
        ws.write_formula("C6", '=IF(OR(C4="",C5="",C4<=C5),"",C4-C5)', f_num)
        ws.write("D6", "kWh/hr", f_cell)

        ws.write("B7", "Annual Operating Hours:", f_bold)
        annual_hours = roi.get("annual_operating_hours")
        ws.write("C7", annual_hours if annual_hours is not None else "", f_num if annual_hours is not None else f_cell)
        ws.write("D7", "hrs/year", f_cell)

        # Live Formula: Annual Energy Saving = Saving * Hours
        ws.write("B8", "Annual Energy Saving:", f_bold)
        ws.write_formula("C8", '=IF(OR(C6="",C7=""),"",C6*C7)', f_num)
        ws.write("D8", "kWh/year", f_cell)

        ws.write("B9", "Electricity Tariff:", f_bold)
        tariff = roi.get("electricity_tariff")
        ws.write("C9", tariff if tariff is not None else "", f_num if tariff is not None else f_cell)
        ws.write("D9", "Rs/kWh", f_cell)

        # Live Formula: Annual Monetary Saving = Annual Energy Saving * Tariff
        ws.write("B10", "Annual Monetary Saving:", f_bold)
        ws.write_formula("C10", '=IF(OR(C8="",C9=""),"",C8*C9)', f_num)
        ws.write("D10", "Rs/year", f_cell)

        ws.write("B11", "Monthly Monetary Saving:", f_bold)
        ws.write_formula("C11", '=IF(C10="","",C10/12)', f_num)
        ws.write("D11", "Rs/month", f_cell)

        ws.write("B12", "Monthly Energy Saving:", f_bold)
        ws.write_formula("C12", '=IF(C8="","",C8/12)', f_num)
        ws.write("D12", "kWh/month", f_cell)

        # Investment & Payback
        ws.write("B14", "LEDL Motor Investment:", f_bold)
        motor_investment = roi.get("motor_investment")
        ws.write("C14", motor_investment if motor_investment is not None else "", f_num if motor_investment is not None else f_cell)
        ws.write("D14", "Rs", f_cell)

        ws.write("B15", "Installation / Modification Cost:", f_bold)
        installation_cost = roi.get("installation_cost")
        ws.write("C15", installation_cost if installation_cost is not None else "", f_num if installation_cost is not None else f_cell)
        ws.write("D15", "Rs", f_cell)

        # Live Formula: Total Investment
        ws.write("B16", "Total Investment:", f_bold)
        ws.write_formula("C16", '=IF(AND(C14="",C15=""),"",SUM(C14:C15))', f_num)
        ws.write("D16", "Rs", f_cell)

        # Live Formula: Payback Period = Total Investment / Annual Saving
        ws.write("B17", "ROI / Simple Payback Period:", f_bold)
        ws.write_formula("C17", '=IF(OR(C10="",C16=""),"",IF(C10>0,C16/C10,"No saving"))', f_num)
        ws.write("D17", "Years", f_cell)

        ws.write("B19", "Baseline note:", f_bold)
        ws.merge_range("C19:D19", "Blank savings indicate no usable pre-change baseline was recorded.", f_cell)

        # Replacement scenarios are included in the AI Insights sheet when selected.

        # Add native Excel Bar Chart for Before vs After
        chart = wb.add_chart({"type": "column"})
        if roi.get("before_kwh_hr") is not None and roi.get("after_kwh_hr") is not None:
            chart.add_series({
            "name": "Specific Consumption (kWh/hr)",
            "categories": "='Energy Saving & ROI'!$B$4:$B$5",
            "values": "='Energy Saving & ROI'!$C$4:$C$5",
            "fill": {"color": "#1F3A8A"},
            "data_labels": {"value": True, "num_format": "0.00"}
            })
        chart.set_title({"name": "Before vs. After Motor Consumption"})
        chart.set_y_axis({"name": "kWh/hr"})
        chart.set_legend({"position": "none"})
        chart.set_size({"width": 450, "height": 300})
        if roi.get("before_kwh_hr") is not None and roi.get("after_kwh_hr") is not None:
            ws.insert_chart("F4", chart)

    @staticmethod
    def _classify_observed_duty(summary):
        duration = summary.get("duration_hours") or 0.0
        running = summary.get("running_hours") or 0.0
        if duration <= 0 or not summary.get("samples_count"):
            return "Not classifiable: no valid telemetry in the selected period."
        if running <= 0:
            return "No running interval detected; IEC duty class cannot be determined from this period."
        running_fraction = min(1.0, running / duration)
        idle_fraction = max(0.0, 1.0 - running_fraction)
        return (
            f"Observed running {running:.2f} h of {duration:.2f} h ({running_fraction * 100:.1f}%), "
            f"idle {idle_fraction * 100:.1f}%. Nameplate duty: {summary.get('nameplate_duty', 'not recorded')}. "
            "An IEC S1–S10 class requires load and rest-cycle/thermal evidence; telemetry runtime alone is not sufficient."
        )

    @staticmethod
    def _calculate_replacement_scenarios(summary, profile, roi):
        """Estimate savings using measured load and explicit efficiency assumptions."""
        rated_kw = profile.motor_rating_kw
        tariff = roi.get("electricity_tariff")
        annual_hours = roi.get("annual_operating_hours")
        running_hours = summary.get("running_hours")
        avg_kw = summary.get("avg_kw")
        duration_hours = summary.get("duration_hours") or 0.0
        if not all(isinstance(v, (int, float)) and v > 0 for v in (rated_kw, running_hours, avg_kw, duration_hours)):
            return []

        loading_pct = min(100.0, max(0.0, avg_kw / rated_kw * 100.0))
        annual_loaded_hours = roi.get("annual_operating_hours")
        annual_loaded_hours = (annual_loaded_hours * min(1.0, running_hours / duration_hours)) if annual_loaded_hours else None
        current_eff = profile.rated_efficiency_pct
        candidate_eff = profile.replacement_motor_efficiency_pct
        candidate_kw = profile.replacement_motor_rating_kw or rated_kw
        if not current_eff or not candidate_eff or not candidate_kw or not annual_loaded_hours or tariff is None:
            return [{
                "label": f"Measured loading {loading_pct:.1f}%",
                "loading_pct": round(loading_pct, 1),
                "annual_loaded_hours": round(annual_loaded_hours, 1) if annual_loaded_hours is not None else None,
                "annual_kwh_saving": None,
                "annual_cost_saving": None,
                "status": "Provide current nameplate efficiency, candidate rating and efficiency, annual operating hours, and tariff to calculate replacement savings.",
            }]

        candidate_load_kw = avg_kw * (current_eff / candidate_eff)
        if candidate_kw < rated_kw:
            candidate_load_kw = min(candidate_load_kw, candidate_kw * loading_pct / 100.0)
        saving_kw = avg_kw - candidate_load_kw
        # If the replacement increases consumption, preserve the negative result as a penalty.
        annual_saving_kwh = saving_kw * annual_loaded_hours if annual_loaded_hours is not None else None
        annual_saving_cost = annual_saving_kwh * tariff if annual_saving_kwh is not None and tariff is not None else None
        return [{
            "label": f"Measured baseline (observed loading {loading_pct:.1f}%)",
            "loading_pct": round(loading_pct, 1),
            "annual_loaded_hours": round(annual_loaded_hours, 1) if annual_loaded_hours is not None else None,
            "annual_kwh_saving": round(annual_saving_kwh, 2) if annual_saving_kwh is not None else None,
            "annual_cost_saving": round(annual_saving_cost, 2) if annual_saving_cost is not None else None,
            "status": f"Current efficiency {current_eff:.2f}%; replacement efficiency {candidate_eff:.2f}%.",
            "current_efficiency_pct": current_eff,
            "candidate_efficiency_pct": candidate_eff,
            "candidate_rating_kw": candidate_kw,
        }]

    def _generate_ai_report_summary(self, device, profile, summary, observations, scenarios, start_time, end_time, db):
        """Ask the configured OpenAI RAG service to summarize compact report facts."""
        payload = {
            "study_period_ist": {"start": _to_ist_str(start_time), "end": _to_ist_str(end_time)},
            "device": {"name": device.alias, "configured": bool(device.configured)},
            "motor_nameplate": {
                "make": profile.motor_make, "rating_kw": profile.motor_rating_kw,
                "rated_current_amps": profile.rated_current_amps, "rated_speed_rpm": profile.rated_speed_rpm,
                "duty": profile.motor_duty, "motor_type": profile.motor_type,
                "rated_efficiency_pct": profile.rated_efficiency_pct,
            },
            "replacement_motor": {
                "rating_kw": profile.replacement_motor_rating_kw,
                "efficiency_pct": profile.replacement_motor_efficiency_pct,
            },
            "measured_summary": summary,
            "automatic_observations": observations,
            "replacement_efficiency_scenarios": scenarios,
            "replacement_scenario_basis": "Replacement input power is estimated from measured kW and the ratio of nameplate efficiencies at equal shaft load. Annual savings use observed running fraction projected to configured annual hours. Verify candidate sizing and efficiency at the actual load point.",
            "commercial_assumptions": {
                "annual_operating_hours": profile.annual_operating_hours,
                "electricity_tariff_rs_per_kwh": profile.electricity_tariff,
            },
            "limitations": [
                "Replacement savings are estimates using configured nameplate efficiencies; confirm candidate efficiency at the measured load point.",
                "Validate candidate sizing and torque-speed characteristics before treating savings as a quote.",
                "Use measured running time and loading; disclose any missing or weak telemetry.",
            ],
        }
        prompt = (
            "Write a brief management-level summary for a motor energy report, focused only on energy consumption, "
            "electricity cost, and potential energy/cost savings from replacing the motor. Use the supplied measured "
            "study-period energy, tariff, operating hours, load, and replacement savings calculations. Mention the "
            "current and candidate efficiencies when available, and explain the estimate basis in one short sentence. "
            "Do not repeat telemetry readings, power quality metrics, or detailed real-time data. Never invent missing "
            "values; clearly say when a cost or saving cannot be calculated. Use concise headings and plain text.\n\n"
            "COMPACT REPORT DATA (JSON):\n" + json.dumps(payload, default=str, separators=(",", ":"))
        )
        try:
            return asyncio.run(rag_service.generate_report_insights(prompt, device.device_id, db))
        except Exception as exc:
            logger.exception("AI report summary failed")
            return f"AI insights unavailable: {exc}"

    @staticmethod
    def _write_ai_summary(ws, wb, ai_summary, scenarios, study, roi, f_title, f_section, f_header, f_cell, f_bold, f_num):
        # The detailed telemetry already lives on the Analysis and Data sheets.
        # Keep this optional AI page focused on the commercial energy decision.
        f_summary_title = wb.add_format({
            "bold": True, "font_size": 16, "font_color": "white",
            "bg_color": "#1F3A8A", "align": "center", "valign": "vcenter"
        })
        f_summary_section = wb.add_format({
            "bold": True, "font_size": 11, "font_color": "white",
            "bg_color": "#334155", "border": 1, "border_color": "#CBD5E1",
            "valign": "vcenter"
        })
        f_summary_label = wb.add_format({
            "bold": True, "font_size": 10, "bg_color": "#E2E8F0",
            "border": 1, "border_color": "#CBD5E1", "valign": "vcenter", "text_wrap": True
        })
        f_summary_value = wb.add_format({
            "font_size": 10, "border": 1, "border_color": "#CBD5E1",
            "valign": "vcenter", "text_wrap": True, "num_format": "#,##0.00"
        })
        f_summary_text = wb.add_format({
            "font_size": 10, "border": 1, "border_color": "#CBD5E1",
            "valign": "top", "text_wrap": True
        })

        ws.hide_gridlines(2)
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 1)
        ws.set_margins(0.35, 0.35, 0.5, 0.5)
        ws.set_column("A:A", 3)
        ws.set_column("B:B", 38)
        ws.set_column("C:C", 22)
        ws.set_column("D:D", 22)
        ws.merge_range("B2:D2", "ENERGY, COST & REPLACEMENT SAVINGS SUMMARY", f_summary_title)
        ws.set_row(1, 32)
        ws.merge_range("B4:D4", "AI POWER STUDY SUMMARY", f_summary_section)
        ws.merge_range("B5:D9", ai_summary or "AI insights unavailable.", f_summary_text)
        for row in range(4, 9):
            ws.set_row(row, 26)

        ws.merge_range("B11:D11", "ENERGY AND COST OUTLOOK", f_summary_section)
        scenario = scenarios[0] if scenarios else None
        measured_energy = study.get("energy_kwh") if study.get("samples_count") else None
        tariff = roi.get("electricity_tariff")
        measured_cost = measured_energy * tariff if measured_energy is not None and tariff is not None else None
        values = [
            ("Measured energy consumption for study period", measured_energy, "kWh"),
            ("Current motor energy cost for study period", measured_cost, "Rs"),
            ("Potential annual energy saving after replacement", scenario.get("annual_kwh_saving") if scenario else None, "kWh/year"),
            ("Potential annual cost saving after replacement", scenario.get("annual_cost_saving") if scenario else None, "Rs/year"),
            ("Potential monthly cost saving", (scenario.get("annual_cost_saving") / 12.0) if scenario and scenario.get("annual_cost_saving") is not None else None, "Rs/month"),
        ]
        for row, (label, value, unit) in enumerate(values, start=11):
            ws.write(row, 1, label, f_summary_label)
            if isinstance(value, (int, float)):
                ws.write_number(row, 2, value, f_summary_value)
            else:
                ws.write(row, 2, value if value is not None else "Not calculable", f_summary_text)
            ws.write(row, 3, unit, f_summary_text)
            ws.set_row(row, 30)

        ws.merge_range("B19:D19", "REPLACEMENT SCENARIO AND BASIS", f_summary_section)
        if scenario:
            details = (
                f"{scenario.get('label', 'Replacement motor')}\n"
                f"{scenario.get('status', '')}\n"
                f"Annual loaded hours used: {scenario.get('annual_loaded_hours') if scenario.get('annual_loaded_hours') is not None else 'not configured'}"
            )
        else:
            details = "Replacement savings could not be calculated. Configure the existing and replacement motor efficiencies, motor rating, annual operating hours, and electricity tariff."
        ws.merge_range("B20:D22", details, f_summary_text)
        ws.merge_range(
            "B24:D26",
            "Savings are estimates based on measured average load, configured motor efficiencies, observed running fraction, annual operating hours, and electricity tariff. Confirm replacement motor sizing and efficiency at the actual operating point before using these values for investment decisions.",
            f_summary_text,
        )
        ws.set_row(19, 30)
        ws.set_row(20, 30)
        ws.set_row(21, 30)
        ws.set_row(23, 30)
        ws.set_row(24, 30)
        ws.set_row(25, 30)
        ws.freeze_panes(4, 1)

    def _write_sheet3_analysis(
        self, ws, summary, points, alerts, auto_obs, profile,
        f_title, f_sec, f_hdr, f_cell, f_bold, f_num, f_pct
    ):
        ws.set_column("A:A", 5)
        ws.set_column("B:B", 35)
        ws.set_column("C:C", 20)
        ws.set_column("D:D", 15)

        ws.merge_range("B1:D1", "MOTOR ENERGY AUDIT - DETAILED ANALYSIS", f_title)

        row = 3
        sections = [
            ("ENERGY CONSUMPTION & COST", [
                ("Total Energy Consumed (Integrated)", summary.get("energy_kwh") if summary.get("samples_count", 0) else None, "kWh"),
                ("Hardware Counter Delta (kwh_imp)", summary.get("counter_kwh_delta", 0), "kWh"),
                ("Counter vs Integrated Discrepancy", summary.get("discrepancy_pct", 0.0) / 100.0, "%"),
                ("Electricity Tariff", profile.electricity_tariff, "Rs/kWh"),
            ("Total Electricity Cost", summary.get("energy_kwh", 0.0) * profile.electricity_tariff if profile.electricity_tariff is not None else None, "Rs")
            ]),
            ("POWER & DEMAND", [
                ("Average Active Power", summary.get("avg_kw"), "kW"),
                ("Maximum Active Power", summary.get("max_kw"), "kW"),
                ("Minimum Active Power", summary.get("min_kw"), "kW"),
                ("Load Factor (Avg kW / Max kW)", summary.get("load_factor"), ""),
                ("Max Demand (MD kW)", summary.get("max_demand_kw") if summary.get("samples_count", 0) else None, "kW")
            ]),
            ("OPERATIONAL DUTY CYCLE", [
                ("Nameplate Duty Declaration", profile.motor_duty or "Not recorded", "IEC duty class"),
                ("Total Duration", summary.get("duration_hours"), "Hours"),
                ("Running Time", summary.get("running_hours", 0.0), "Hours"),
                ("Idle Time", summary.get("idle_hours", 0.0), "Hours"),
                ("Idle Percentage", summary.get("idle_pct") / 100.0 if summary.get("idle_pct") is not None else None, "%")
            ]),
            ("POWER QUALITY & UNBALANCE", [
                ("Energy-Weighted Power Factor", summary.get("weighted_pf"), ""),
                ("Arithmetic Average PF", summary.get("avg_pf"), ""),
                ("Average Voltage (Line-Line)", summary.get("avg_voltage"), "V"),
                ("Voltage Unbalance", summary.get("voltage_unbalance_pct") / 100.0 if summary.get("voltage_unbalance_pct") is not None and summary.get("samples_count", 0) else None, "%"),
                ("Current Unbalance", summary.get("current_unbalance_pct") / 100.0 if summary.get("current_unbalance_pct") is not None and summary.get("samples_count", 0) else None, "%"),
                ("Data Completeness", summary.get("data_completeness_pct") / 100.0 if summary.get("data_completeness_pct") is not None else None, "%")
            ])
        ]

        for sec_name, items in sections:
            ws.merge_range(row, 1, row, 3, sec_name, f_sec)
            row += 1
            for lbl, val, unit in items:
                ws.write(row, 1, lbl, f_bold)
                if unit == "%":
                    ws.write(row, 2, val, f_pct)
                elif isinstance(val, (int, float)):
                    ws.write(row, 2, val, f_num)
                elif val is None:
                    ws.write(row, 2, "Not available", f_cell)
                else:
                    ws.write(row, 2, str(val), f_cell)
                ws.write(row, 3, unit, f_cell)
                row += 1
            row += 1

    def _write_sheet4_data(self, ws, points, f_hdr, f_cell, f_num, f_dt):
        headers = [
            "Timestamp (IST)", "Interval kWh", "Cumulative kWh", "Power (kW)",
            "kW L1", "kW L2", "kW L3", "Voltage L-L Avg (V)", "V12", "V23", "V31",
            "Current Avg (A)", "I L1", "I L2", "I L3", "PF Avg", "PF L1", "PF L2", "PF L3", "Frequency (Hz)"
        ]
        for col, h in enumerate(headers):
            ws.write(0, col, h, f_hdr)
            ws.set_column(col, col, 14)

        for row, pt in enumerate(points, start=1):
            ws.write(row, 0, _to_ist_str(pt.get("ts", "")), f_cell)
            ws.write(row, 1, pt["kwh"] if pt["kwh"] is not None else "", f_num)
            ws.write(row, 2, pt["cum_kwh"] if pt["cum_kwh"] is not None else "", f_num)
            ws.write(row, 3, pt["kw"] if pt["kw"] is not None else "", f_num)
            ws.write(row, 4, pt["kw1"] if pt["kw1"] is not None else "", f_num)
            ws.write(row, 5, pt["kw2"] if pt["kw2"] is not None else "", f_num)
            ws.write(row, 6, pt["kw3"] if pt["kw3"] is not None else "", f_num)
            vll = pt.get("vll_avg") if pt.get("vll_avg") is not None else pt.get("v_avg")
            ws.write(row, 7, vll if vll is not None else "", f_num)
            v12 = pt.get("v12") if pt.get("v12") is not None else (round(pt["v1n"] * 1.732, 1) if pt.get("v1n") is not None else "")
            v23 = pt.get("v23") if pt.get("v23") is not None else (round(pt["v2n"] * 1.732, 1) if pt.get("v2n") is not None else "")
            v31 = pt.get("v31") if pt.get("v31") is not None else (round(pt["v3n"] * 1.732, 1) if pt.get("v3n") is not None else "")
            ws.write(row, 8, v12, f_num if isinstance(v12, (int, float)) else f_cell)
            ws.write(row, 9, v23, f_num if isinstance(v23, (int, float)) else f_cell)
            ws.write(row, 10, v31, f_num if isinstance(v31, (int, float)) else f_cell)
            ws.write(row, 11, pt["i_avg"] if pt["i_avg"] is not None else "", f_num)
            ws.write(row, 12, pt["i1"] if pt["i1"] is not None else "", f_num)
            ws.write(row, 13, pt["i2"] if pt["i2"] is not None else "", f_num)
            ws.write(row, 14, pt["i3"] if pt["i3"] is not None else "", f_num)
            ws.write(row, 15, pt["pf_avg"] if pt["pf_avg"] is not None else "", f_num)
            ws.write(row, 16, pt["pf1"] if pt["pf1"] is not None else "", f_num)
            ws.write(row, 17, pt["pf2"] if pt["pf2"] is not None else "", f_num)
            ws.write(row, 18, pt["pf3"] if pt["pf3"] is not None else "", f_num)
            ws.write(row, 19, pt["freq"] if pt["freq"] is not None else "", f_num)

    def _write_sheet5_charts(self, ws, wb, points, num_pts):
        if num_pts < 2:
            return

        # Chart 1: Active Power (kW) Trend
        chart_kw = wb.add_chart({"type": "line"})
        chart_kw.add_series({
            "name": "Total Power (kW)",
            "categories": f"=Data!$A$2:$A${num_pts+1}",
            "values": f"=Data!$D$2:$D${num_pts+1}",
            "line": {"color": "#1F3A8A", "width": 2}
        })
        chart_kw.set_title({"name": "Active Power (kW) Trend"})
        chart_kw.set_x_axis({"name": "Time"})
        chart_kw.set_y_axis({"name": "kW"})
        chart_kw.set_size({"width": 600, "height": 320})
        ws.insert_chart("B2", chart_kw)

        # Chart 2: Current (3 Phases) Trend
        chart_i = wb.add_chart({"type": "line"})
        for name, col_letter, color in [("I L1", "M", "#EF4444"), ("I L2", "N", "#F59E0B"), ("I L3", "O", "#3B82F6")]:
            chart_i.add_series({
                "name": name,
                "categories": f"=Data!$A$2:$A${num_pts+1}",
                "values": f"=Data!${col_letter}$2:${col_letter}${num_pts+1}",
                "line": {"color": color, "width": 1.5}
            })
        chart_i.set_title({"name": "Phase Currents (A)"})
        chart_i.set_size({"width": 600, "height": 320})
        ws.insert_chart("B19", chart_i)

        # Chart 3: Line-to-Line Voltage Trend
        chart_v = wb.add_chart({"type": "line"})
        for name, col_letter, color in [("V12", "I", "#EF4444"), ("V23", "J", "#F59E0B"), ("V31", "K", "#3B82F6")]:
            chart_v.add_series({
                "name": name,
                "categories": f"=Data!$A$2:$A${num_pts+1}",
                "values": f"=Data!${col_letter}$2:${col_letter}${num_pts+1}",
                "line": {"color": color, "width": 1.5}
            })
        chart_v.set_title({"name": "Line-to-Line Voltages (V)"})
        chart_v.set_size({"width": 600, "height": 320})
        ws.insert_chart("L2", chart_v)

        # Chart 4: Power Factor Trend
        chart_pf = wb.add_chart({"type": "line"})
        chart_pf.add_series({
            "name": "Power Factor",
            "categories": f"=Data!$A$2:$A${num_pts+1}",
            "values": f"=Data!$P$2:$P${num_pts+1}",
            "line": {"color": "#10B981", "width": 2}
        })
        chart_pf.set_title({"name": "Power Factor Trend"})
        chart_pf.set_y_axis({"min": 0, "max": 1.0})
        chart_pf.set_size({"width": 600, "height": 320})
        ws.insert_chart("L19", chart_pf)

    def _compute_roi_data(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        study_summary: Dict[str, Any],
        profile: DeviceProfile,
        roi_params: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Compute Before and After kWh/hr figures from DB or manual override."""
        # After is typically current study window
        after_kwh = study_summary.get("energy_kwh", 0.0)
        after_running_hrs = study_summary.get("running_hours", 0.0)
        after_kwh_hr = (after_kwh / after_running_hrs) if after_running_hrs > 0 and after_kwh > 0 else None

        # Check manual override
        if roi_params.get("after_kwh_hr_manual") is not None:
            after_kwh_hr = float(roi_params["after_kwh_hr_manual"])

        # Before window: query DB for before period if specified, or manual
        before_kwh_hr = None
        if roi_params.get("before_kwh_hr_manual") is not None:
            before_kwh_hr = float(roi_params["before_kwh_hr_manual"])
        elif roi_params.get("before_start") and roi_params.get("before_end"):
            try:
                b_start = datetime.fromisoformat(roi_params["before_start"])
                b_end = datetime.fromisoformat(roi_params["before_end"])
                b_dev = roi_params.get("before_device_id", device_id)
                b_summary = query_service.get_period_summary(b_dev, b_start, b_end, db)
                b_kwh = b_summary.get("energy_kwh", 0.0)
                b_run_hrs = b_summary.get("running_hours", 0.0)
                if b_run_hrs > 0 and b_kwh > 0:
                    before_kwh_hr = b_kwh / b_run_hrs
                elif b_summary.get("duration_hours", 0) > 0 and b_kwh > 0:
                    before_kwh_hr = b_kwh / b_summary["duration_hours"]
            except Exception:
                before_kwh_hr = None

        # Do not treat a baseline window without usable telemetry as a measured zero.
        if before_kwh_hr is not None and before_kwh_hr <= 0:
            before_kwh_hr = None

        configured_annual_hours = roi_params.get("annual_operating_hours", profile.annual_operating_hours)
        configured_tariff = roi_params.get("electricity_tariff", profile.electricity_tariff)
        configured_motor_cost = roi_params.get("motor_investment", profile.motor_investment)
        configured_install_cost = roi_params.get("installation_cost", profile.installation_cost)
        return {
            "before_kwh_hr": round(before_kwh_hr, 2) if before_kwh_hr is not None else None,
            "after_kwh_hr": round(after_kwh_hr, 2) if after_kwh_hr is not None and after_kwh_hr > 0 else None,
            "annual_operating_hours": float(configured_annual_hours) if configured_annual_hours is not None else None,
            "electricity_tariff": float(configured_tariff) if configured_tariff is not None else None,
            "motor_investment": float(configured_motor_cost) if configured_motor_cost is not None else None,
            "installation_cost": float(configured_install_cost) if configured_install_cost is not None else None
        }


excel_report_service = ExcelReportService()
