"""
WebSocket endpoints for real-time streaming.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websocket_manager import ws_manager
from app.auth import verify_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """Main WebSocket endpoint for real-time data."""
    # 1. Authenticate via token before fully accepting
    if not token or token == "undefined" or token == "null":
        # In dev mode we might allow it without token, but check config
        from app.config import get_runtime_settings
        settings = get_runtime_settings()
        if settings.ADMIN_PASSWORD_HASH:
            # Prod mode: require token
            logger.warning("WebSocket connection rejected: No token provided")
            await websocket.close(code=1008, reason="Authentication required")
            return
    else:
        try:
            # Check token validity
            verify_token(token)
        except Exception as e:
            logger.warning(f"WebSocket connection rejected: Invalid token - {e}")
            await websocket.close(code=1008, reason="Invalid token")
            return

    # 2. Connect via manager (handles max connections check)
    connected = await ws_manager.connect(websocket)
    if not connected:
        return # Manager already closed it with 1008
        
    try:
        while True:
            # Keep connection open. We can also receive commands here.
            data = await websocket.receive_text()
            # Handle client-to-server messages if needed
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Unexpected WebSocket error: {e}")
        await ws_manager.disconnect(websocket)
