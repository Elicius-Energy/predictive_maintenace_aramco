"""
Device Telemetry Ingestion endpoint.
Authenticated via X-Device-Key header.
Accepts single JSON reading object or array of readings (up to 1000).
"""
from typing import Union, List, Dict, Any
from fastapi import APIRouter, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.config import settings
from app.db.session import get_db
from app.services.ingest_service import ingest_service

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("")
def ingest_readings(
    payload: Union[Dict[str, Any], List[Dict[str, Any]]],
    x_device_key: str = Header(None, alias="X-Device-Key"),
    db: Session = Depends(get_db)
):
    """
    Ingest IoT energy meter readings.
    Supports single reading object or batch array up to 1000 items.
    """
    if not x_device_key or x_device_key != settings.DEVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Device-Key authentication header"
        )

    # Process payload idempotently
    result = ingest_service.process_payload(payload, db)
    return result
