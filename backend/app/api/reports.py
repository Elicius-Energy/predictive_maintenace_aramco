"""
Report generation and download endpoints.
Supports live preview, official Excel generation, history retrieval, and raw data export.
"""
import io
import csv
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.session import get_db
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


@router.get("/raw-data")
def download_raw_data(
    device_id: str = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    format: str = Query("csv"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Download raw time-series readings in CSV format."""
    require_device_access(user, device_id, db)
    try:
        t_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        t_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    readings = (
        db.query(Reading)
        .filter(
            Reading.device_id == device_id,
            Reading.ts >= t_start,
            Reading.ts <= t_end
        )
        .order_by(Reading.ts.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp_UTC", "Device_ID", "v1n", "v2n", "v3n", "vln_avg",
        "v12", "v23", "v31", "vll_avg", "i1", "i2", "i3", "i_avg",
        "kw1", "kw2", "kw3", "t_kw", "kvar1", "kvar2", "kvar3", "t_kvar",
        "kva1", "kva2", "kva3", "t_kva", "pf1", "pf2", "pf3", "pf_avg",
        "freq", "kwh_imp", "kvarh_imp", "t_kvah", "md_kw", "md_kva"
    ])

    for r in readings:
        writer.writerow([
            r.ts.isoformat(), r.device_id, r.v1n, r.v2n, r.v3n, r.vln_avg,
            r.v12, r.v23, r.v31, r.vll_avg, r.i1, r.i2, r.i3, r.i_avg,
            r.kw1, r.kw2, r.kw3, r.t_kw, r.kvar1, r.kvar2, r.kvar3, r.t_kvar,
            r.kva1, r.kva2, r.kva3, r.t_kva, r.pf1, r.pf2, r.pf3, r.pf_avg,
            r.freq, r.kwh_imp, r.kvarh_imp, r.t_kvah, r.md_kw, r.md_kva
        ])

    output.seek(0)
    filename = f"Raw_Energy_Data_{device_id[-6:]}_{t_start.strftime('%Y%m%d')}_{t_end.strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
