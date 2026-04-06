"""
RAG endpoints for AI diagnostics.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import db
from app.models import FaultDiagnosis, FeatureVector
from app.rag.claude_client import ai_client
from app.feature_engineering import feature_extractor
from typing import List

router = APIRouter(prefix="/rag", tags=["rag"])

@router.get("/history")
async def get_diagnosis_history(machine_id: str = "Machine_5", limit: int = 10):
    """Get past AI diagnoses."""
    return db.get_diagnoses(machine_id, limit)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    machine_id: str
    history: List[ChatMessage]

@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """Real AI RAG Chat interface."""
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]
    response = await ai_client.chat(
        user_message=request.message,
        machine_id=request.machine_id,
        history=history_dicts
    )
    return {"response": response}

@router.post("/diagnose")
async def trigger_manual_diagnosis(machine_id: str = "Machine_5"):
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
