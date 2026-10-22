"""
Chatbot API endpoint with Server-Sent Events (SSE) streaming.
"""
from typing import List, Dict, Literal
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.rag_service import rag_service
from app.db.models import User
from app.api.auth import get_current_user, require_device_access

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=10000)


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=40)
    device_id: str = Field(..., min_length=1, max_length=64)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)


@router.post("")
async def chat_stream(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Stream AI chatbot response using SSE."""
    require_device_access(user, req.device_id, db)
    msg_dicts = [{"role": m.role, "content": m.content} for m in req.messages]
    stream_gen = rag_service.stream_chat(
        messages=msg_dicts,
        device_id=req.device_id,
        user_timezone=req.timezone,
        db=db
    )
    return StreamingResponse(
        stream_gen,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
