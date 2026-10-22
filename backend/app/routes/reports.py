from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict
from app.auth import get_current_user
from app.reports.generator import generate_pdf_report

router = APIRouter()

class ReportRequest(BaseModel):
    machine_id: str
    start_time: str
    end_time: str
    report_data: Dict[str, Any] = {}

@router.get("/generate_pdf")
async def generate_pdf(
    machine_id: str,
    start_time: str,
    end_time: str,
    current_user: str = Depends(get_current_user)
):
    try:
        buf = await generate_pdf_report(machine_id, start_time, end_time)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Report_{machine_id}.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate_pdf")
async def generate_custom_pdf(
    request: ReportRequest,
    current_user: str = Depends(get_current_user)
):
    try:
        buf = await generate_pdf_report(
            request.machine_id,
            request.start_time,
            request.end_time,
            report_data=request.report_data,
        )
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Motor_Energy_Report_{request.machine_id}.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
