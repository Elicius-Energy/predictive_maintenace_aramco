"""
Report generation and download endpoints.
Supports live preview, official Excel generation, history retrieval, and raw data export.
"""
import io
import csv
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc, cast, String
from app.db.session import get_db
from app.db.base import SessionLocal
from app.db.models import Report, Reading, Device, User
from app.api.auth import get_current_user, require_roles, require_device_access
from app.services.excel_report_service import excel_report_service
from app.services.query_service import query_service

router = APIRouter(prefix="/api/reports", tags=["reports"])
logger = logging.getLogger(__name__)


class ReportPreviewRequest(BaseModel):
    device_id: str
    start_time: str
    end_time: str
    interval: str = "1-minute"


class GenerateReportRequest(BaseModel):
    device_id: str
    start_time: str
    end_time: str
    interval: str = "1-minute"
    title: Optional[str] = ""
    remarks: Optional[str] = ""
    include_roi: bool = True
    include_ai_summary: bool = False
    roi_params: Optional[Dict[str, Any]] = None


@router.post("/preview")
def preview_report(req: ReportPreviewRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Compute live preview card metrics before downloading the report."""
    require_device_access(user, req.device_id, db)
    try:
        t_start = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(req.end_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    summary = query_service.get_period_summary(req.device_id, t_start, t_end, db)
    return {
        "energy_kwh": summary.get("energy_kwh", 0.0),
        "avg_kw": summary.get("avg_kw", 0.0),
        "avg_pf": summary.get("weighted_pf", summary.get("avg_pf", 1.0)),
        "idle_time_str": summary.get("idle_time_str", "0 h 0 min"),
        "data_completeness_pct": summary.get("data_completeness_pct", 100.0),
        "duration_str": summary.get("duration_str", "")
    }


@router.post("/generate")
def generate_report(
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "analyst"))
):
    """Generate Excel report workbook and return as downloadable file."""
    require_device_access(user, req.device_id, db)
    try:
        t_start = datetime.fromisoformat(req.start_time.replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(req.end_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    if t_end <= t_start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    try:
        report_record, file_path = excel_report_service.generate_report(
            device_id=req.device_id,
            start_time=t_start,
            end_time=t_end,
            interval=req.interval,
            user_remarks=req.remarks or "",
            include_roi=req.include_roi,
            include_ai_summary=req.include_ai_summary,
            roi_params=req.roi_params,
            created_by=user.username,
            db=db
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Report generation failed for device %s", req.device_id)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc

    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/history/{device_id}")
def list_report_history(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Retrieve list of previously generated reports for the device."""
    require_device_access(user, device_id, db)
    reports = (
        db.query(Report)
        .filter(Report.device_id == device_id)
        .order_by(desc(Report.created_at))
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "report_no": r.report_no,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "start_time": r.params.get("start_time"),
            "end_time": r.params.get("end_time"),
            "interval": r.params.get("interval"),
            "energy_kwh": r.summary.get("energy_kwh", 0.0),
            "created_by": r.created_by,
            "filename": os.path.basename(r.file_path)
        }
        for r in reports
    ]


@router.get("/download/{report_id}")
def download_existing_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Re-download an existing generated report file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report file not found")
    require_device_access(user, report.device_id, db)
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")

    filename = os.path.basename(report.file_path)
    return FileResponse(
        path=report.file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete a generated report file from server disk storage and remove its database record."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    require_device_access(user, report.device_id, db)

    file_path = report.file_path
    report_no = report.report_no
    db.delete(report)
    db.commit()

    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as exc:
            logger.warning("Failed to remove report file %s: %s", file_path, exc)

    return {"success": True, "deleted_id": report_id, "report_no": report_no}


@router.delete("/history/{device_id}")
def delete_all_device_reports(device_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete all archived reports for a device from server disk storage and database."""
    require_device_access(user, device_id, db)
    reports = db.query(Report).filter(Report.device_id == device_id).all()
    deleted_count = 0
    for rep in reports:
        f_path = rep.file_path
        db.delete(rep)
        deleted_count += 1
        if f_path and os.path.exists(f_path):
            try:
                os.remove(f_path)
            except OSError as exc:
                logger.warning("Failed to remove report file %s: %s", f_path, exc)
    db.commit()
    return {"success": True, "deleted_count": deleted_count}


@router.get("/raw-data")
def download_raw_data(
    device_id: str = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    format: str = Query("csv"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Stream raw time-series readings in CSV format using lightweight column tuples
    and 5,000-row chunked streaming so multi-month exports (250k+ rows) start
    immediately with minimal memory usage.
    """
    require_device_access(user, device_id, db)
    try:
        t_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    IST = timezone(timedelta(hours=5, minutes=30))
    MONTH_NAMES = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    def _fmt_ist_date_time(dt: Optional[datetime]):
        if not dt:
            return "", ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ist_dt = dt.astimezone(IST)
        return f"{ist_dt.day:02d}-{MONTH_NAMES[ist_dt.month]}-{ist_dt.year}", f"{ist_dt.hour:02d}:{ist_dt.minute:02d}:{ist_dt.second:02d}"

    # Pre-fetch only rows that actually contain machine_screen OCR data (typically 0 to a few rows)
    screen_rows = (
        db.query(Reading.ts, Reading.raw)
        .filter(
            Reading.device_id == device_id,
            Reading.ts >= t_start,
            Reading.ts <= t_end,
            Reading.raw.isnot(None),
            cast(Reading.raw, String).like('%"machine_screen"%')
        )
        .all()
    )
    screen_by_ts: Dict[int, Dict[str, Any]] = {
        (int(r_ts.timestamp()) if r_ts.tzinfo else int(r_ts.replace(tzinfo=timezone.utc).timestamp())): r_raw.get("machine_screen")
        for r_ts, r_raw in screen_rows
        if isinstance(r_raw, dict) and isinstance(r_raw.get("machine_screen"), dict)
    }

    def generate_csv_chunks():
        buf = io.StringIO()
        writer = csv.writer(buf)

        # 1. Immediately yield header row so HTTP 200 headers flush right away
        writer.writerow([
            "Date (IST)", "Time (IST)", "Device_ID", "v1n", "v2n", "v3n", "vln_avg",
            "v12", "v23", "v31", "vll_avg", "i1", "i2", "i3", "i_avg",
            "kw1", "kw2", "kw3", "t_kw", "kvar1", "kvar2", "kvar3", "t_kvar",
            "kva1", "kva2", "kva3", "t_kva", "pf1", "pf2", "pf3", "pf_avg",
            "freq", "kwh_imp", "kvarh_imp", "t_kvah", "md_kw", "md_kva",
            "temperature_c", "rpm",
            "count_ne", "spindle_rpm", "tpi", "doff_time_min",
            "front_roller_rpm", "delivery_speed_m_min", "chase_mm", "length_m",
            "screen_efficiency_pct", "suction_pressure_mm_wc"
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        stream_db = SessionLocal()
        try:
            q = (
                stream_db.query(
                    Reading.ts, Reading.device_id,
                    Reading.v1n, Reading.v2n, Reading.v3n, Reading.vln_avg,
                    Reading.v12, Reading.v23, Reading.v31, Reading.vll_avg,
                    Reading.i1, Reading.i2, Reading.i3, Reading.i_avg,
                    Reading.kw1, Reading.kw2, Reading.kw3, Reading.t_kw,
                    Reading.kvar1, Reading.kvar2, Reading.kvar3, Reading.t_kvar,
                    Reading.kva1, Reading.kva2, Reading.kva3, Reading.t_kva,
                    Reading.pf1, Reading.pf2, Reading.pf3, Reading.pf_avg,
                    Reading.freq, Reading.kwh_imp, Reading.kvarh_imp, Reading.t_kvah,
                    Reading.md_kw, Reading.md_kva, Reading.temperature, Reading.rpm
                )
                .filter(
                    Reading.device_id == device_id,
                    Reading.ts >= t_start,
                    Reading.ts <= t_end
                )
                .order_by(Reading.ts.asc())
                .yield_per(5000)
            )

            row_count = 0
            for r in q:
                date_str, time_str = _fmt_ist_date_time(r.ts)
                ms = None
                if screen_by_ts:
                    r_epoch = int(r.ts.timestamp()) if r.ts.tzinfo else int(r.ts.replace(tzinfo=timezone.utc).timestamp())
                    ms = screen_by_ts.get(r_epoch)

                if ms:
                    writer.writerow([
                        date_str, time_str, r.device_id, r.v1n, r.v2n, r.v3n, r.vln_avg,
                        r.v12, r.v23, r.v31, r.vll_avg, r.i1, r.i2, r.i3, r.i_avg,
                        r.kw1, r.kw2, r.kw3, r.t_kw, r.kvar1, r.kvar2, r.kvar3, r.t_kvar,
                        r.kva1, r.kva2, r.kva3, r.t_kva, r.pf1, r.pf2, r.pf3, r.pf_avg,
                        r.freq, r.kwh_imp, r.kvarh_imp, r.t_kvah, r.md_kw, r.md_kva,
                        r.temperature if r.temperature is not None else "",
                        int(r.rpm) if r.rpm is not None else "",
                        ms.get("count_ne") if ms.get("count_ne") is not None else "",
                        int(ms["spindle_rpm"]) if ms.get("spindle_rpm") is not None else "",
                        ms.get("tpi") if ms.get("tpi") is not None else "",
                        ms.get("doff_time_min") if ms.get("doff_time_min") is not None else "",
                        ms.get("front_roller_rpm") if ms.get("front_roller_rpm") is not None else "",
                        ms.get("delivery_speed_m_min") if ms.get("delivery_speed_m_min") is not None else "",
                        ms.get("chase_mm") if ms.get("chase_mm") is not None else "",
                        ms.get("length_m") if ms.get("length_m") is not None else "",
                        ms.get("efficiency_pct") if ms.get("efficiency_pct") is not None else "",
                        ms.get("suction_pressure_mm_wc") if ms.get("suction_pressure_mm_wc") is not None else ""
                    ])
                else:
                    writer.writerow([
                        date_str, time_str, r.device_id, r.v1n, r.v2n, r.v3n, r.vln_avg,
                        r.v12, r.v23, r.v31, r.vll_avg, r.i1, r.i2, r.i3, r.i_avg,
                        r.kw1, r.kw2, r.kw3, r.t_kw, r.kvar1, r.kvar2, r.kvar3, r.t_kvar,
                        r.kva1, r.kva2, r.kva3, r.t_kva, r.pf1, r.pf2, r.pf3, r.pf_avg,
                        r.freq, r.kwh_imp, r.kvarh_imp, r.t_kvah, r.md_kw, r.md_kva,
                        r.temperature if r.temperature is not None else "",
                        int(r.rpm) if r.rpm is not None else "",
                        "", "", "", "", "", "", "", "", "", ""
                    ])

                row_count += 1
                if row_count % 5000 == 0:
                    yield buf.getvalue()
                    buf.seek(0)
                    buf.truncate(0)

            rem = buf.getvalue()
            if rem:
                yield rem
        finally:
            stream_db.close()

    filename = f"Raw_Energy_Data_{device_id[-6:]}_{t_start.strftime('%Y%m%d')}_{t_end.strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        generate_csv_chunks(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Accel-Buffering": "no"
        }
    )
