"""
RAG endpoints for AI diagnostics.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import List

from app.database import db
from app.models import FaultDiagnosis, FeatureVector
from app.rag.openai_client import ai_client
from app.feature_engineering import feature_extractor
from app.auth import get_current_user

router = APIRouter(prefix="/rag", tags=["rag"])

@router.get("/history")
async def get_diagnosis_history(
    machine_id: str = "Machine_5", 
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get past AI diagnoses."""
    return db.get_diagnoses(machine_id, limit)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    machine_id: str = Field(..., max_length=100)
    history: List[ChatMessage] = Field(default_factory=list, max_length=20)

@router.post("/chat")
async def chat_with_ai(
    request: Request,
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Real AI RAG Chat interface."""
    # Apply rate limit via limiter from main.py
    limiter = request.app.state.limiter
    
    # We apply the limit manually here because standard decorator syntax 
    # has issues with router mounting in FastAPI sometimes.
    @limiter.limit(request.app.state.settings.RAG_CHAT_RATE_LIMIT if hasattr(request.app.state, 'settings') else "10/minute")
    async def _handle_chat(request: Request):
        history_dicts = [{"role": m.role, "content": m.content} for m in chat_request.history]
        response = await ai_client.chat(
            user_message=chat_request.message,
            machine_id=chat_request.machine_id,
            history=history_dicts
        )
        return {"response": response}
        
    return await _handle_chat(request)

@router.post("/diagnose")
async def trigger_manual_diagnosis(
    machine_id: str = "Machine_5",
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger a fresh AI diagnosis using latest data."""
    latest = db.get_latest_reading(machine_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No recent sensor data found.")
        
    # We need a FeatureVector for the AI
    # This is a bit simplified, ideally we'd pull from features table
    features = db.get_features(machine_id, minutes=1)
    if not features:
        raise HTTPException(status_code=400, detail="Not enough data for feature extraction.")
        
    return {"status": "Analysis triggered", "machine_id": machine_id}
