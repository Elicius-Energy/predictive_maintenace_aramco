"""
WebSocket endpoints for real-time streaming.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket_manager import ws_manager

router = APIRouter(tags=["ws"])

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time data."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open. We can also receive commands here.
            data = await websocket.receive_text()
            # Handle client-to-server messages if needed
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
